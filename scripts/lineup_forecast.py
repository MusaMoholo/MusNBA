"""Offline lineup worlds and exact precomputed selections; no serving-time simulation."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict
from fractions import Fraction
from itertools import product
import hashlib
from pathlib import Path

import numpy as np

from basketball_common import packed, sha256_file
from scripts import a1_lineup_branches as branches, forecast_output, player_worlds, projection
from scripts.foul_out import Rule3Policy
from scripts.world_mass import WorldMass, branch_masses


class LegalCapture(Rule3Policy):
    """Read-only opening capture and an independent five-player invariant around the accepted rule."""
    def __init__(self, delegate=None):
        super().__init__()
        self.delegate = delegate

    def begin(self, g, worlds, available, seed):
        if self.delegate is None:
            super().begin(g, worlds, available, seed)
        else:
            self.delegate.begin(g, worlds, available, seed)
            self.available = self.delegate.available
            self.counts = self.delegate.counts
        self.opening = np.full((worlds, 2, 5), -1, dtype=np.int16)
        self.checked = 0

    def check(self, g, st, active, lineups):
        if ((np.diff(np.sort(lineups, axis=2), axis=2) == 0).any()
                or (g.side[lineups] != np.arange(2)[None, :, None]).any()
                or not self.available[active[:, None, None], lineups].all()):
            raise ValueError('published lineup is not five distinct available teammates')
        for side in (0, 1):
            ordinary = ((st.ingame['pf_so_far'][active][:, g.side == side] < 6)
                        & self.available[active][:, g.side == side]).sum(1)
            disqualified = (st.ingame['pf_so_far'][active[:, None], lineups[:, side]] >= 6).sum(1)
            if not np.array_equal(disqualified, np.maximum(0, 5 - ordinary)):
                raise ValueError('published five violates the NBA exhaustion exception')
        self.checked += 2 * len(active)

    def before_segment(self, g, st, active, scheduled):
        lineups = (self.delegate.before_segment(g, st, active, scheduled) if self.delegate is not None
                   else super().before_segment(g, st, active, scheduled))
        self.check(g, st, active, lineups)
        opening = (st.period[active] == 1) & (st.clock[active] == 720) & (self.opening[active, 0, 0] < 0)
        self.opening[active[opening]] = lineups[opening]
        return lineups

    def after_fouls(self, g, st, active, offense, defense):
        changed = (self.delegate.after_fouls(g, st, active, offense, defense) if self.delegate is not None
                   else super().after_fouls(g, st, active, offense, defense))
        lineups = np.empty((len(active), 2, 5), int)
        off = st.off[active]
        lineups[np.arange(len(active)), off] = offense
        lineups[np.arange(len(active)), 1 - off] = defense
        self.check(g, st, active, lineups)
        return changed

    def finish(self, g, st):
        if self.delegate is None:
            super().finish(g, st)
        else:
            self.delegate.finish(g, st)
        if (self.opening < 0).any():
            raise ValueError('missing saved opening five')


def simulate(eng, g, worlds, seed):
    if eng.runtime.get('foul_policy') != 'nba-rule3-v1':
        raise ValueError('lineup publication requires the qualified Rule 3 runtime')
    previous = eng.rotation_policy
    policy = LegalCapture(previous)
    eng.rotation_policy = policy
    previous_detail = getattr(eng, 'world_observer', None)
    detail = previous_detail
    if detail is None and eng.runtime.get('world_details') == 'visible-worlds-v1':
        from scripts.world_detail import WorldDetail
        detail = WorldDetail()
    eng.world_observer = detail
    try:
        summary = eng.simulate(g, worlds, seed)
    finally:
        eng.rotation_policy = previous
        eng.world_observer = previous_detail
    st = eng.last
    raw = {'player_ids': np.asarray(g.ids), 'side': g.side.copy(), 'available': policy.available,
           'opening_lineups': policy.opening, 'minutes': st.minutes, 'team_points': st.pts,
           'final_period': st.period, 'possessions': st.poss,
           **{'box_' + key: value for key, value in st.box.items()}}
    if detail is not None:
        raw.update(zone_fga=detail.attempts, zone_fgm=detail.makes)
        if hasattr(detail,'rotation_presence'):
            raw['rotation_presence']=detail.rotation_presence
    for side in (0, 1):
        if not np.array_equal(raw['box_pts'][:, g.side == side].sum(1), raw['team_points'][:, side]):
            raise ValueError('saved player/team points differ')
        target = np.column_stack([np.full(worlds, 60.)] * 4 + [25. * (st.period - 4)])
        if not np.allclose(raw['minutes'][:, g.side == side].sum(1), target, rtol=0, atol=1e-8):
            raise ValueError('saved team-period minutes differ')
    return {'raw': raw, 'summary': summary, 'targets': g.expected.copy(), 'seed': str(seed),
            'counts': {**policy.counts, 'independently_checked_fives': policy.checked}}


def merge(records):
    first = records[0]['raw']
    if any(not np.array_equal(record['raw'][key], first[key]) for record in records for key in ('player_ids', 'side')):
        raise ValueError('lineup branch rosters differ')
    return {key: first[key] if key in ('player_ids', 'side') else np.concatenate([record['raw'][key] for record in records])
            for key in first}


def lead_fan(raw, weights):
    mass = WorldMass(len(weights), weights)
    lead = np.cumsum(raw['team_points'][:, 0] - raw['team_points'][:, 1], axis=1)
    return {'breaks': ['Q1', 'Half', 'Q3', 'Final'],
            'q': [mass.summary(lead[:, k], offset=True)['q'] for k in (0, 1, 2, 4)],
            'p_lead': [round(float(mass.mean(lead[:, k] > 0)), 3) for k in (0, 1, 2, 4)]}


def assemble(g, selected, records, runtime, provenance):
    chosen = [asdict(p) if not isinstance(p, dict) else p for p in selected]
    if not 1 <= len(chosen) <= 2 or len(records) != 2**len(chosen):
        raise ValueError('complete one/two-player branches required')
    expected = branches.enumerate_branches(g, [(p['team_id'], p['player_id']) for p in chosen])
    for p in chosen:
        if p['probability'] != float(g.avail[g.ids.index(p['player_id'])]):
            raise ValueError('selected availability differs from original inputs')
    if any(r['assignments'] != b.assignments or r['branch_id'] != b.branch_id or r['weight'] != b.weight
           for r, b in zip(records, expected)):
        raise ValueError('branches differ from exhaustive original-probability assignments')
    probabilities = [record['weight'] for record in records]
    counts = [len(record['raw']['minutes']) for record in records]
    units = branch_masses(counts, probabilities)
    boundaries = np.r_[0, np.cumsum(counts)]
    all_raw = merge(records)
    cases = {}
    for choices in product((None, True, False), repeat=len(chosen)):
        conditions = {p['player_id']: value for p, value in zip(chosen, choices) if value is not None}
        keep = [i for i, record in enumerate(records) if all(dict((p, value) for _, p, value in record['assignments']).get(pid) == value
                                                           for pid, value in conditions.items())]
        raw = merge([records[i] for i in keep])
        weights = np.concatenate([units[boundaries[i]:boundaries[i + 1]] for i in keep])
        mass = WorldMass(len(weights), weights)
        case_game = branches.prepare_branch(g, [(p['team_id'], p['player_id'], conditions[p['player_id']])
                                                for p in chosen if p['player_id'] in conditions]) if conditions else g
        players = deepcopy(case_game.players)
        expected_targets = sum(records[i]['targets'] * int(units[boundaries[i]:boundaries[i + 1]].sum()) for i in keep) / mass.total
        for j, player in enumerate(p for side in g.sides for p in players[side]):
            player['minutes']['target'] = float(expected_targets[j])
        teams = {side: {'tid': g.game[side + '_id'], 'players': players[side],
                        'minutes': raw['minutes'][:, g.side == i],
                        'box': {key: raw['box_' + key][:, g.side == i] for key in projection.BOX}}
                 for i, side in enumerate(g.sides)}
        points = {side: raw['team_points'][:, i] for i, side in enumerate(g.sides)}
        expectation = {'mu_home': float(mass.mean(points['home'].sum(1))), 'mu_away': float(mass.mean(points['away'].sum(1))),
                       'pace': float(mass.mean(raw['possessions'].mean(1)))}
        summary = forecast_output.game(g.game, teams, points, raw['final_period'] - 4, len(weights), expectation, runtime['id'], weights)
        from scripts.rotation_maps import summarise
        rotation=summarise(raw,weights)
        if rotation is not None:summary['rotation_map']=rotation
        for side in g.sides:
            for player in summary[side]['players']:
                j = g.ids.index(player['id'])
                player['opening_share'] = float(mass.mean((raw['opening_lineups'] == j).any((1, 2))))
                player['availability_simulated'] = float(mass.mean(raw['available'][:, j]))
        key = ''.join('x' if value is None else '1' if value else '0' for value in choices)
        cases[key] = {'choices': conditions, 'sim': summary, 'lead_fan': lead_fan(raw, weights)}
    descriptors = [{'branch_id': record['branch_id'], 'assignments': record['assignments'],
                    'weight': {'numerator': str(record['weight'].numerator), 'denominator': str(record['weight'].denominator)},
                    'seed': record['seed'], 'capture_sha256': record['capture_sha256'],
                    **({'execution':record['execution']} if 'execution' in record else {})} for record in records]
    identity = {'game': g.game['game_id'], 'origin': g.input_before, 'runtime': runtime, 'selected': chosen,
                'branches': descriptors, 'provenance': provenance}
    source_id = hashlib.sha256(packed(identity).encode()).hexdigest()
    for case in cases.values():
        if 'rotation_map' in case['sim']:case['sim']['rotation_map']['source_id']=source_id
    payload = {'schema': 1, 'game': g.game['game_id'], 'origin': g.input_before, 'engine': runtime['id'],
               'model': runtime['models'], 'source_id': source_id, 'selected_players': chosen,
               'weight_assumptions': 'Uncalibrated independent availability probabilities; other uncertain players still vary.',
               'cases': cases, 'branches': [{**d, 'worlds': player_worlds.pack_capture(r['raw'])} for d, r in zip(descriptors, records)]}
    return {'summary': cases['x' * len(chosen)]['sim'], 'raw': all_raw, 'weights': units, 'payload': payload,
            'season_pieces': [(record['raw']['team_points'], record['weight']) for record in records], 'source_id': source_id}


def project(eng, g, selected, worlds, directory, provenance):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    records = []
    for i, branch in enumerate(branches.enumerate_branches(g, [(p.team_id, p.player_id) for p in selected])):
        prepared = branches.prepare_branch(g, branch.assignments)
        seed = projection.seed_for('lineup-v1', eng.runtime['id'], g.input_before, g.day, g.game['game_id'], branch.branch_id)
        record = simulate(eng, prepared, worlds, seed)
        path = directory / f'branch-{i:03d}.npz'
        np.savez_compressed(path, **record['raw'])
        records.append({**record, 'assignments': branch.assignments, 'branch_id': branch.branch_id,
                        'weight': branch.weight, 'capture_sha256': sha256_file(path)})
    return assemble(g, selected, records, eng.runtime, provenance)
