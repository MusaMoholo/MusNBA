"""Forecast serialization with optional exact world masses; no fitting or provider access."""
from __future__ import annotations

import numpy as np

from scripts import projection
from scripts.world_mass import WorldMass

BOX, SLICES = projection.BOX, projection.SLICES
FG_DIST, PERIOD_DIST = projection.FG_DIST, projection.PERIOD_DIST


def shooting_summaries(values, mass=None):
    if mass is None:
        return projection.shooting_summaries(values)
    result = {}
    for key, (made, attempted) in projection.SHOOTING_PAIRS.items():
        if made not in values or attempted not in values:
            continue
        m, a = np.asarray(values[made]), np.asarray(values[attempted])
        if np.any(m < 0) or np.any(a < 0) or np.any(m > a):
            raise ValueError(f'Invalid shooting counts for {key}')
        mask = a > 0
        if mask.any():
            selected = mass.subset(mask)
            pct = np.floor(100 * m[mask] / a[mask] + 0.5).astype(np.int64)
            result[key] = {**selected.summary(pct), 'defined': selected.total, 'total': mass.total}
    return result


def game(game: dict, teams: dict, pts_by_period: dict, n_ot: np.ndarray, W: int, exp: dict, model_id: str, weights=None) -> dict:
    """Game output in the app contract from per-world arrays: pts_by_period[side] (W, 5 periods: Q1–Q4, OT),
    teams[side] with tid, players (player_inputs), box[stat] (W, players, 5) and minutes (W, players, 5).
    Shared by the placeholder and the possession engine (scripts/engine.py)."""
    mass = WorldMass(W, weights)
    mean = np.mean if weights is None else mass.mean
    summary = projection.summary if weights is None else mass.summary
    sides = ('home', 'away')
    out = {'game_id': game['game_id'], 'model': model_id, 'sims': W, 'shooting_distribution_schema': 1,
           'expectation': {k: round(v, 3) for k, v in exp.items()},
           'ot': round(float(mean(n_ot > 0)), 4), 'ot_periods': np.bincount(n_ot).astype(int).tolist() if weights is None else mass.counts(n_ot)[1].tolist(), 'periods': {}}
    policies = {p.get('availability_policy') for side in sides for p in teams[side]['players'] if p.get('availability_policy')}
    if len(policies) > 1:
        raise ValueError('mixed availability policies in one game')
    if policies:
        out['availability_policy'] = policies.pop()
    if weights is not None:
        out.update(weighted_worlds_schema=1, probability_mass=mass.total)
    for period, cols in SLICES.items():
        ph, pa = pts_by_period['home'][:, cols].sum(1), pts_by_period['away'][:, cols].sum(1)
        out['periods'][period] = {
            'total': summary(ph + pa, offset=True), 'margin': summary(ph - pa, offset=True),
            'home': {'pts': summary(ph, offset=True), 'win': round(float(mean(ph > pa)), 4), 'tie': round(float(mean(ph == pa)), 4)},
            'away': {'pts': summary(pa, offset=True), 'win': round(float(mean(pa > ph)), 4), 'tie': round(float(mean(ph == pa)), 4)},
        }
    for side, team in teams.items():
        box, minutes = team['box'], team['minutes']
        players = []
        fg = {k: box[k].sum(axis=2) for k in BOX}
        tens = np.stack([fg['pts'] + 0 >= 10, (fg['oreb'] + fg['dreb']) >= 10, fg['ast'] >= 10, fg['stl'] >= 10, fg['blk'] >= 10]).sum(axis=0)
        played_any = minutes.sum(axis=2) > 0
        for i, x in enumerate(team['players']):
            entry = {k: x[k] for k in ('id', 'name', 'pos', 'jersey', 'starter', 'status', 'injury')}
            if x.get('availability_basis'):
                entry['availability_basis'] = x['availability_basis']
            if x.get('availability_policy'):
                entry['availability_policy'] = x['availability_policy']
            if x.get('minutes'):  # D29: what the engine's minutes rest on (engine v1.2+)
                mm = x['minutes']
                entry['minutes_basis'] = {'healthy': round(mm['healthy'], 1), 'target': round(mm.get('target', 0.0), 1),
                                          'rotation': round(mm.get('rotation', 1.0), 3), 'missed': int(mm['missed']), 'k_back': int(mm['k_back']),
                                          'ramp': round(mm['ramp'], 3), 'start_share': round(mm['start_share'], 3)}
            entry.update({'availability': round(x['availability'], 3), 'base_min': round(x['base_min'], 2),
                          'played': round(float(mean(played_any[:, i])), 4),
                          'double_double': round(float(mean(tens[:, i] >= 2)), 4),
                          'triple_double': round(float(mean(tens[:, i] >= 3)), 4),
                          'quadruple_double': round(float(mean(tens[:, i] >= 4)), 5),
                          'quintuple_double': round(float(mean(tens[:, i] >= 5)), 5),
                          'five_by_five': round(float(mean((fg['pts'][:, i] >= 5) & ((fg['oreb'] + fg['dreb'])[:, i] >= 5) & (fg['ast'][:, i] >= 5)
                                                       & (fg['stl'][:, i] >= 5) & (fg['blk'][:, i] >= 5))), 5), 'periods': {}})
            for period, cols in SLICES.items():
                v = {k: box[k][:, i, cols].sum(axis=1) for k in BOX}
                v['reb'] = v['oreb'] + v['dreb']
                v['pra'], v['pr'], v['pa'], v['ra'] = v['pts'] + v['reb'] + v['ast'], v['pts'] + v['reb'], v['pts'] + v['ast'], v['reb'] + v['ast']
                v['stocks'] = v['stl'] + v['blk']
                mins_p = minutes[:, i, cols].sum(axis=1)
                v['min'] = np.rint(mins_p).astype(np.int64)
                dist = FG_DIST if period == 'fg' else PERIOD_DIST
                entry['periods'][period] = {
                    'sec': round(float(mean(mins_p) * 60), 1),
                    'mean': {k: round(float(mean(v[k])), 3) for k in BOX + ('reb',)},
                    'stats': {**{k: summary(v[k]) for k in dist}, **shooting_summaries(v, None if weights is None else mass)},
                }
            if not played_any[:, i].any():
                del entry['periods']  # ruled out in every world: identity and status only
                players.append(entry)
                continue
            if 0 < mean(played_any[:, i]) < 0.999:
                mask = played_any[:, i]
                if_mean = np.mean if weights is None else mass.subset(mask).mean
                entry['if_plays'] = {'min': round(float(if_mean(minutes[mask, i].sum(axis=1))), 3),
                                     **{k: round(float(if_mean(fg[k][mask, i])), 3) for k in ('pts', 'ast', 'fg3m')},
                                     'reb': round(float(if_mean((fg['oreb'] + fg['dreb'])[mask, i])), 3)}
            players.append(entry)
        team_means = {period: {k: round(float(mean(box[k][:, :, cols].sum(axis=(1, 2)))), 3) for k in BOX}
                      for period, cols in SLICES.items()}
        for period in team_means:
            team_means[period]['reb'] = round(team_means[period]['oreb'] + team_means[period]['dreb'], 3)
        out[side] = {'team_id': team['tid'], 'mu': round(float(exp['mu_home'] if side == 'home' else exp['mu_away']), 3),
                     'strength': round(float(np.mean(team.get('strength', 1.0))), 4), 'box': team_means, 'players': players}
    return out


def season(T, master, day, teams, played, rng, engine_pts=None, params=None, weights=None):
    """Package already simulated season paths, preserving the legacy equal-mass representation."""
    from scripts import pathway
    W = int(played['home_win'].shape[0])
    mass = WorldMass(W, weights)
    mean = np.mean if weights is None else mass.mean
    summary = projection.summary if weights is None else mass.summary
    ids = sorted(teams, key=int)
    index = {t: i for i, t in enumerate(ids)}
    remaining = sorted((r for r in master if r['date_et'] >= day), key=lambda r: (r['date_et'], r['tip_utc'], r['game_id']))
    unresolved = [r for r in master if r['date_et'] < day and r['status'] != 'final']
    G = len(remaining)
    rows = []
    for g, r in enumerate(remaining):
        pts = played['points'][:, g]
        source = 'engine' if engine_pts and r['game_id'] in engine_pts else 'pathway'
        row = {'game_id': r['game_id'], 'p_home': round(float(mean(played['home_win'][:, g])), 4),
               'mu_home': round(float(mean(pts[:, 0])), 2), 'mu_away': round(float(mean(pts[:, 1])), 2),
               'source': source}
        if source == 'pathway':
            home, away = pts[:, 0], pts[:, 1]
            row['regulation'] = {name: summary(values, offset=True) for name, values in (
                ('home', home), ('away', away), ('total', home + away), ('margin', home - away))}
        rows.append(row)
    H = np.zeros((G, len(ids)), np.float32)
    A = np.zeros((G, len(ids)), np.float32)
    for g, r in enumerate(remaining):
        H[g, index[r['home_id']]] = 1
        A[g, index[r['away_id']]] = 1
    home_wins = played['home_win'].astype(np.float32)
    base_w = np.array([T[t]['w'] for t in ids], np.float32)
    base_l = np.array([T[t]['l'] for t in ids], np.float32)
    games_left = H.sum(0) + A.sum(0)
    wins = np.rint(base_w + home_wins @ H + (1 - home_wins) @ A).astype(np.int64)
    total_games = (base_w + base_l + games_left).astype(int)
    tiebreak = rng.random((W, len(ids)))
    seed = np.zeros((W, len(ids)), np.int64)
    for conf in ('East', 'West'):
        cols = np.array([index[t] for t in ids if teams[t]['conf'] == conf])
        order = np.argsort(-(wins[:, cols] + 0.5 * tiebreak[:, cols]), axis=1, kind='stable')
        ranks = np.empty_like(order)
        ranks[np.arange(W)[:, None], order] = np.arange(1, len(cols) + 1)[None, :]
        seed[:, cols] = ranks
    league_key = wins + 0.5 * tiebreak
    best, worst = np.argmax(league_key, axis=1), np.argmin(league_key, axis=1)
    bottom3 = np.argsort(league_key, axis=1, kind='stable')[:, :3]
    out = {}
    for t in ids:
        i = index[t]
        s = seed[:, i]
        if weights is None:
            seeds = np.bincount(s, minlength=16)[1:16] / W
        else:
            counts = np.zeros(16, np.int64)
            np.add.at(counts, s, mass.weights)
            seeds = counts[1:16] / mass.total
        out[t] = {'w': int(base_w[i]), 'l': int(base_l[i]), 'remaining': int(games_left[i]), 'scheduled': int(total_games[i]),
                  'mean_w': round(float(mean(wins[:, i])), 3), 'mean_l': round(float(total_games[i] - mean(wins[:, i])), 3),
                  'wins': summary(wins[:, i]), 'seed_mean': round(float(mean(s)), 3),
                  'seeds': [round(float(x), 4) for x in seeds],
                  'top6': round(float(mean(s <= 6)), 4), 'playin': round(float(mean((s >= 7) & (s <= 10))), 4),
                  'out': round(float(mean(s >= 11)), 4), 'first': round(float(mean(s == 1)), 4),
                  'bottom3': round(float(mean((bottom3 == i).any(axis=1))), 4),
                  'best_record': round(float(mean(best == i)), 4), 'worst_record': round(float(mean(worst == i)), 4)}
    params = {**pathway.PATHWAY, **(params or {})}
    result = {'model': pathway.PATHWAY['id'], 'pathway': params, 'as_of': day, 'sims': W, 'teams': out, 'games': rows,
            'regulation_distribution_schema': 1,
            'engine_games': sorted(engine_pts) if engine_pts else [],
            'unresolved_before': [r['game_id'] for r in unresolved],
            'notes': ['Team pathway (D25, D26): each universe carries its own offensive and defensive ratings, takes the '
                      "possession engine's worlds for its games and updates both teams after every simulated game; its "
                      'spread is calibrated walk-forward on 2022-26 (first cut, slightly wide in November).',
                      'Ties broken at random; NBA tiebreakers arrive with phase 4.',
                      'Only games the provider has scheduled are simulated; NBA Cup-determined games appear once scheduled.']}
    if weights is not None:
        result.update(weighted_paths_schema=1, probability_mass=mass.total)
        result['notes'].append("Season paths carry the same availability assumptions as today's Expected games; paths are weighted.")
    return result

