#!/usr/bin/env python3
"""Accounting and contract checks over retained data, snapshots and views.

  .venv/bin/python scripts/smoke.py            all checks
  .venv/bin/python scripts/smoke.py --fault    perturb one stored value in memory; must FAIL

Independent identities: box-score points reconcile with team and master scores; standings W/L
reconcile with finals; every histogram sums to the simulation count; win/margin/total summaries
agree; seed probabilities partition; a stored game re-simulates bit-for-bit from its seed.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import DATA, DERIVED, MASTER_CSV, NBA_TEAM_IDS, SNAPSHOTS, VIEWS, day_shift, read_json  # noqa: E402
from scripts import box_scores, master_fixtures, pbp, projection  # noqa: E402
from scripts.season_stats import period_profiles, player_table, team_table  # noqa: E402

results = []


def check(name, ok, detail=''):
    results.append(ok)
    print(f'{"PASS" if ok else "FAIL"}  {name}{"  " + str(detail) if detail and not ok else ""}')


def hist_total(d):
    return sum(d['hist'])


def training_loss_runs(directory: Path) -> list[Path]:
    return sorted(path for path in directory.glob('*.npz')
                  if re.fullmatch(r'\d{8}T\d{6}Z_.+\.npz', path.name))


def hist_mean(d):
    return sum((d['min'] + i) * c for i, c in enumerate(d['hist'])) / hist_total(d)


def player_hist_problems(stats: dict, worlds: int, shooting_schema: bool) -> list[str]:
    problems = []
    for key, dist in stats.items():
        if key not in projection.SHOOTING_PAIRS and hist_total(dist) != worlds:
            problems.append(f'{key} histogram count')
    if shooting_schema:
        for key, (_, attempts) in projection.SHOOTING_PAIRS.items():
            if attempts not in stats:
                problems.append(f'{attempts} missing')
                continue
            a = stats[attempts]
            zero = a['hist'][-a['min']] if a['min'] <= 0 < a['min'] + len(a['hist']) else 0
            defined = worlds - zero
            d = stats.get(key)
            if (not defined and d is not None) or (defined and (d is None or d.get('defined') != defined
                    or d.get('total') != worlds or hist_total(d) != defined
                    or any(count and not 0 <= d['min'] + i <= 100 for i, count in enumerate(d['hist'])))):
                problems.append(f'{key} conditional histogram count')
    return problems


def align_legacy_shooting_schema(stored: dict, replay: dict) -> None:
    if 'shooting_distribution_schema' in stored:
        return
    replay.pop('shooting_distribution_schema', None)
    for side in ('home', 'away'):
        for player in replay[side]['players']:
            for period, line in player.get('periods', {}).items():
                for key in projection.SHOOTING_PAIRS:
                    line['stats'].pop(key, None)
                if period != 'fg':
                    for key in ('fga', 'fg3a', 'fta'):
                        line['stats'].pop(key, None)


def lineup_accuracy_consistent(record: dict) -> bool:
    slates = list(record['slates'].values())
    overall = record.get('overall')
    if not slates:
        return overall is None
    if overall is None:
        return False
    n = sum(row['team_games'] for row in slates)
    if n <= 0 or overall['team_games'] != n or overall['slates'] != len(slates):
        return False
    for metric in ('slot_accuracy', 'all_five'):
        weighted = sum(row[metric] * row['team_games'] for row in slates) / n
        if not abs(weighted - overall[metric]) < 1e-3:
            return False
    return all(0 <= row['all_five'] <= row['slot_accuracy'] <= 1 for row in slates)


def m6a_player_outputs(folder: Path, reports: Path) -> list[Path]:
    outputs = []
    for path in folder.glob('*_m6a*.parquet'):
        report = reports / f'{path.stem}.json'
        if report.exists() and json.loads(report.read_text()).get('experiment') == 'm6a_aggregation':
            outputs.append(path)
    return sorted(outputs)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--fault', action='store_true')
    args = parser.parse_args()

    master = master_fixtures.load()
    ids = [r['game_id'] for r in master]
    check('master: unique game ids', len(ids) == len(set(ids)))
    per_team = Counter()
    for r in master:
        per_team[r['home_id']] += 1
        per_team[r['away_id']] += 1
    check('master: 30 teams, home != away', len(per_team) == 30 and all(r['home_id'] != r['away_id'] for r in master))
    check('master: equal scheduled games per team', len(set(per_team.values())) == 1, dict(Counter(per_team.values())))
    finals = [r for r in master if r['status'] == 'final']
    check('master: finals have scores and no ties', all(r['home_pts'] and r['away_pts'] and r['home_pts'] != r['away_pts'] for r in finals))

    team_rows, player_rows = box_scores.load_csv('team_games.csv'), box_scores.load_csv('player_games.csv')
    pts = defaultdict(int)
    for r in player_rows:
        if r['dnp'] == '0':
            pts[(r['game_id'], r['team_id'])] += int(r['pts'] or 0)
    team_pts = {(r['game_id'], r['team_id']): int(r['pts']) for r in team_rows}
    bad = [k for k, v in team_pts.items() if pts.get(k) != v]
    check('box: player points sum to team points in every final', not bad, bad[:3])
    by_id = {r['game_id']: r for r in master}
    mismatch = [r['game_id'] for r in team_rows
                if int(r['pts']) != int(by_id[r['game_id']]['home_pts' if r['home'] == '1' else 'away_pts'])]
    check('box: team points match master scores', not mismatch, mismatch[:3])
    quarters = [r['game_id'] for r in team_rows if r['q1'] and sum(int(r[q]) for q in ('q1', 'q2', 'q3', 'q4')) + int(r['ot'] or 0) != int(r['pts'])]
    check('box: quarter scores sum to final', not quarters, quarters[:3])

    report = read_json(DERIVED / 'pbp_report.json')
    rates = report['mismatch_rates']
    check('pbp: points reconcile with box scores (<0.5% of player-games)', rates.get('pts', 1) < 0.005, rates.get('pts'))
    check('pbp: minutes reconcile within a minute (<2%)', rates.get('min', 1) < 0.02, rates.get('min'))
    check('pbp: every counting stat reconciles (<1.5%)', all(v < 0.015 for v in rates.values()), {k: v for k, v in rates.items() if v >= 0.015})
    period_rows = pbp.load()
    team_q = defaultdict(int)
    for r in team_rows:
        for i, q in enumerate(('q1', 'q2', 'q3', 'q4'), 1):
            if r[q]:
                team_q[(r['game_id'], r['team_id'], i)] = int(r[q])
    pbp_q = defaultdict(int)
    for r in period_rows:
        if int(r['period']) <= 4:
            pbp_q[(r['game_id'], r['team_id'], int(r['period']))] += int(r['pts'])
    off = [k for k, v in team_q.items() if pbp_q.get(k, 0) != v]
    check('pbp: player quarter points sum to linescores (<1% of team-quarters)', len(off) < 0.01 * max(1, len(team_q)), len(off))

    for path in sorted((DERIVED / 'history').glob('*/pbp_report.json')):
        h = read_json(path)
        r = h['mismatch_rates']
        agreement = (h.get('points_attempted') or {}).get('agreement_where_known')
        check(f'history {path.parent.name}: {h["games"]} games reconcile (points <0.5%, minutes <2%, stats <1.5%)',
              r.get('pts', 1) < 0.005 and r.get('min', 1) < 0.02 and all(v < 0.015 for v in r.values()), r)
        if agreement is not None and (h['points_attempted']['checked'] or 0) > 1000:
            check(f'history {path.parent.name}: inferred shot values agree where known (>=99.9%)', agreement >= 0.999, agreement)

    from scripts.engine import ENGINE
    versions = [ROOT / 'models' / f"{ENGINE.get('models', ENGINE['version'])}.json"]  # the node models' version file
    if versions[0].exists():
        import numpy as np
        spec = read_json(versions[0])
        v = spec['version']
        vb = spec.get('validated_by')
        logs = [vb] if isinstance(vb, str) else list(vb or [])
        fold_log = next((ROOT / x for x in logs if (ROOT / x).exists() and 'results' in read_json(ROOT / x)), None)  # the node-level fold run
        if fold_log and fold_log.exists():
            res = read_json(fold_log)['results']
            worst = {n: min(r['gain_vs_best_baseline'] for r in folds.values()) for n, folds in res.items()}
            check(f'{v}: every node ({len(worst)}) at least level with its best baseline on every fold ({fold_log.name})',
                  all(x >= -0.001 for x in worst.values()), {k: x for k, x in worst.items() if x < -0.001})
            check(f'{v}: calibration error below 0.02 on every node and fold',
                  all(r['ece_model'] < 0.02 for folds in res.values() for r in folds.values()))
        cfg_path = DERIVED.parent / 'models' / v / 'config.json'
        if cfg_path.exists():
            import lightgbm as lgb
            cfg = read_json(cfg_path)
            problems = []
            for node, m in cfg['nodes'].items():
                booster = lgb.Booster(model_file=str(cfg_path.parent / m['file']))
                x = np.full((3, len(m['columns'])), np.nan)
                if args.fault and node == next(iter(cfg['nodes'])):
                    x = np.full((3, len(m['columns']) + 1), np.nan)
                try:
                    pred = booster.predict(x, raw_score=m['kind'] == 'candidate')
                except Exception as exc:  # wrong input width
                    problems.append(f'{node}: {exc.__class__.__name__}')
                    continue
                if booster.num_feature() != len(m['columns']):
                    problems.append(f'{node}: {booster.num_feature()} features v {len(m["columns"])} listed')
                if m['kind'] == 'multiclass' and not np.allclose(pred.sum(axis=1), 1):
                    problems.append(f'{node}: probabilities do not sum to 1')
            check(f'{v}: all {len(cfg["nodes"])} persisted node models load, take their listed inputs and predict', not problems, problems)
    latest_by_node = {}
    for path in sorted((ROOT / 'analysis' / 'experiments').glob('*_m5_lightgbm.json')) if not versions else []:
        for node, folds in read_json(path)['results'].items():
            latest_by_node[node] = (path.name, folds)  # later runs supersede earlier ones per node
    if latest_by_node:
        worst = {node: min(r['gain_vs_best_baseline'] for r in folds.values()) for node, (_, folds) in latest_by_node.items()}
        check(f'M5: every node ({len(worst)}) at least level with its best baseline on every fold', all(v >= -0.001 for v in worst.values()),
              {k: v for k, v in worst.items() if v < -0.001})
        check('M5: calibration error below 0.02 on every node and fold',
              all(r['ece_model'] < 0.02 for _, folds in latest_by_node.values() for r in folds.values()))
    team_path = DERIVED / 'features' / 'team_pregame.parquet'
    if team_path.exists():
        import pandas as pd
        teams = pd.read_parquet(team_path)
        ok_games = set()
        for seg_path in sorted((DERIVED / 'history').glob('*/segments.parquet')) + [DERIVED / 'segments.parquet']:
            if seg_path.exists():
                g = pd.read_parquet(seg_path, columns=['game_id', 'game_ok', 'offense', 'defense'])
                nba = g['offense'].astype(str).isin(NBA_TEAM_IDS) & g['defense'].astype(str).isin(NBA_TEAM_IDS)
                ok_games |= set(g.loc[g['game_ok'] & nba, 'game_id']) - set(g.loc[~nba, 'game_id'])
        style = [c for c in teams.columns if c.startswith(('off_', 'def_'))]
        check('team profiles: two rows per reconciled game, no missing style, rest 1-7 days',
              len(teams) == 2 * len(ok_games) and not teams[style].isna().any().any() and teams['rest_days'].between(1, 7).all(),
              {'rows': len(teams), 'games': len(ok_games)})
    loss_runs = training_loss_runs(DERIVED / 'experiments')
    if loss_runs:
        import numpy as np
        from scripts import compare
        run = compare.load(str(loss_runs[-1]))
        node, fold = next(iter(run))
        a = run[(node, fold)]
        b_loss = a['loss'].copy()
        if args.fault:
            b_loss[0] += 0.5
        mean, se, per_game = compare.paired(a['loss'], b_loss, a['game'])
        check(f'compare: a run against itself changes nothing ({loss_runs[-1].stem} {node} {fold})', mean == 0 and se == 0, mean)
        other = run[(node, fold)]
        d = other['loss'].astype(float)[::-1].copy()  # any second loss vector on the same rows
        mean, _, per_game = compare.paired(a['loss'], d, a['game'])
        check('compare: per-game sums add up to the node total', abs(per_game.sum() - (d - a['loss']).sum()) < 1e-6 * max(1, len(d)))
    m6a = m6a_player_outputs(DERIVED / 'experiments', ROOT / 'analysis' / 'experiments')
    if m6a:
        import numpy as np
        import pandas as pd
        r = pd.read_parquet(m6a[-1])
        if args.fault:
            r.loc[r.index[0], 'pts_sim'] += 0.5
        bad = {}
        for side in ('sim', 'actual'):
            pts = 2 * r[f'fgm_{side}'] + r[f'fg3m_{side}'] + r[f'ftm_{side}']
            bad[f'pts_{side}'] = float((r[f'pts_{side}'] - pts).abs().max())
            bad[f'reb_{side}'] = float((r[f'reb_{side}'] - r[f'oreb_{side}'] - r[f'dreb_{side}']).abs().max())
        pits = r[[c for c in r.columns if c.endswith('_pit')]].to_numpy()
        check(f'M6a {m6a[-1].stem}: points = 2·FGM + 3PM + FTM and rebounds = OREB + DREB (sim and actual); PIT in [0, 1]',
              max(bad.values()) < 1e-6 and np.nanmin(pits) >= 0 and np.nanmax(pits) <= 1, bad)
    backtests = sorted(p for p in (DERIVED / 'experiments').glob('*_backtest_*.parquet') if not p.stem.endswith('_players'))
    if backtests:  # M9: each game's simulated total and margin add up from the two teams; probabilities and PITs in [0, 1]
        import numpy as np
        import pandas as pd
        b = pd.read_parquet(backtests[-1])
        if args.fault:
            b.loc[b.index[0], 'total_sim'] += 0.5
        gap = max(float((b['total_sim'] - b['home_sim'] - b['away_sim']).abs().max()),
                  float((b['margin_sim'] - b['home_sim'] + b['away_sim']).abs().max()))
        pits = b[[c for c in b.columns if c.endswith('_pit')]].to_numpy()
        check(f'backtest {backtests[-1].stem}: total = home + away and margin = home − away (sim); p and PIT in [0, 1]',
              gap < 1e-6 and b['p_home'].between(0, 1).all() and np.nanmin(pits) >= 0 and np.nanmax(pits) <= 1, {'gap': gap})
    for path in [DERIVED / 'rotations' / 'rotations_report.json'] + sorted((DERIVED / 'history').glob('*/rotations_report.json')):
        if not path.exists():
            continue
        r = read_json(path)
        label = 'current' if path.parent.name == 'rotations' else path.parent.name
        check(f'rotations {label}: stints reconcile (minutes <1%, five on court >99%), 20-45 subs per team-game',
              r['minutes_off_player_games'] < 0.01 and r['team_period_seconds_off'] < 0.01 and 20 <= r['subs_per_team_game'] <= 45,
              {k: r[k] for k in ('minutes_off_player_games', 'team_period_seconds_off', 'subs_per_team_game')})
    for path in [DERIVED / 'segments_report.json'] + sorted((DERIVED / 'history').glob('*/segments_report.json')):
        if not path.exists():
            continue
        r = read_json(path)
        label = 'current' if path.parent == DERIVED else path.parent.name
        implicit = sum(v for key, v in r['issues'].items() if key.startswith('implicit')) / max(1, r['segments'])
        poss_gap = abs(r['possessions_per_team_game'] - r['box_estimate_per_team_game']) / r['box_estimate_per_team_game']
        check(f'segments {label}: {r["segments"]:,} segments — points, clock, alternation, lineups, possessions reconcile',
              r['points_off_team_games'] < 0.01 and r['clock_off_periods'] < 0.01 and r['not_alternating'] < 0.005
              and r['lineups_ok'] > 0.99 and poss_gap < 0.02 and implicit < 0.01,
              {k: r[k] for k in ('points_off_team_games', 'clock_off_periods', 'not_alternating', 'lineups_ok')} | {'poss_gap': round(poss_gap, 4), 'implicit': round(implicit, 4)})
    variant = DERIVED / 'variants' / 'rebound_feed'  # D23: canonical = the 2026-27 rebound convention; v1's feed clocks kept here
    if (variant / 'segments.parquet').exists():
        import pandas as pd
        # History seasons are fixed: their reports must match field for field. The variant's live season is frozen at v1's
        # data (games through 18 Nov) while the canonical one grows nightly (D26), so it is compared row by row below,
        # on the games both hold.
        pairs = [(p, variant / 'history' / p.parent.name / 'segments_report.json') for p in sorted((DERIVED / 'history').glob('*/segments_report.json'))]
        moved = {}
        for a_path, b_path in pairs:
            if b_path.exists():
                a, b = read_json(a_path), read_json(b_path)
                if args.fault and a_path == pairs[-1][0]:
                    b['games_flagged'] += 1
                moved[a_path.parent.name] = [k for k in a if k != 'rebound_clock' and a[k] != b[k]]
        check(f'rebound convention: identical games, segments and identities under both clocks ({len(moved)} seasons)',
              not any(moved.values()), {k: v for k, v in moved.items() if v})
        gaps, live_moved = {}, None
        for p in sorted((DERIVED / 'history').glob('*/segments.parquet')) + [DERIVED / 'segments.parquet']:
            s = pd.read_parquet(p, columns=['rebound', 'action_clock', 'end_clock'])
            r = s[s['rebound'].notna()]
            gaps[p.parent.name] = round(float((r['action_clock'] == r['end_clock']).mean()), 5)
        a = pd.read_parquet(DERIVED / 'segments.parquet', columns=['game_id', 'start_clock', 'end_clock'])
        b = pd.read_parquet(variant / 'segments.parquet', columns=['game_id', 'start_clock', 'end_clock'])
        a = a[a['game_id'].isin(set(b['game_id']))]
        live_moved = int((a[['start_clock', 'end_clock']].to_numpy() != b[['start_clock', 'end_clock']].to_numpy()).any(axis=1).sum()) if len(a) == len(b) else -1
        check("rebound convention: every rebound starts at its miss (>99.9% per season); a no-op on the live season (<0.1%)",
              min(gaps.values()) > 0.999 and 0 <= live_moved < 0.001 * len(a), {'gap_zero': gaps, 'live_moved': live_moved})
    if (DERIVED.parent / 'raw' / 'espn' / 'parity').exists():
        from scripts import parity
        same = parity.same_games()
        bad = {g: r for g, r in same.items() if any(r[f'segment_differences_{rc}'] for rc in ('feed', 'miss'))}
        check(f'parity: {len(same)} 2025-26 games give identical segments through the live and history adapters (both clocks)', not bad, bad)
    import numpy as np
    import pandas as pd
    from scripts import train
    toy = lambda X, dates, groups: {'name': 'toy', 'kind': 'candidate', 'classes': None, 'profile': None, 'X': pd.DataFrame({'a': X}),
                                    'y': np.ones(len(X), int), 'date': np.array(dates), 'group': np.array(groups), 'game': np.array(groups).astype(str)}
    old = toy([1.0, 2.0, 3.0], ['2024-01-01', '2024-06-01', '2025-02-01'], [0, 1, 2])
    new = toy([10.0, 20.0, 30.0], ['2024-01-01', '2025-01-15', '2025-03-01'], [0, 1, 2])
    h = train.hybrid(old, new, ('2024-12-31', '2025-01-01', '2025-04-30'))
    check('train.hybrid: training rows from one dataset, validation rows from the other in order, candidate groups distinct',
          h['X']['a'].tolist() == [1.0, 2.0, 20.0, 30.0] and len(set(h['group'])) == 4 and len(h['y']) == 4, h['X']['a'].tolist())

    import numpy as np
    # D29 minutes: every allocation is exactly 240 regulation minutes, within [0, 48]; the ramp only lowers or keeps
    from scripts import minutes as minutes_mod
    mb = minutes_mod.build('2026-01-01', include_current=False)
    sums = mb['rows'].groupby(['game_id', 'team'])['alloc'].agg(['sum', 'size'])
    sums = sums[sums['size'] >= 5]['sum']
    if args.fault:
        sums.iloc[0] += 1.0
    check(f'minutes: every allocation sums to 240 ({len(sums):,} team-games) and stays in [0, 48]',
          bool((sums - 240).abs().max() < 1e-6) and bool(mb['rows']['alloc'].between(-1e-6, 48 + 1e-4).all()), float((sums - 240).abs().max()))
    check('minutes: return-ramp ratios in (0.5, 1.1], absence-free player-games unramped',
          all(0.5 < v <= 1.1 for v in mb['ramp'].values()) and bool((mb['rows'].loc[mb['rows']['k_back'] == 0, 'ramp'] == 1.0).all()),
          {k: v for k, v in mb['ramp'].items() if not 0.5 < v <= 1.1})
    rng_t = np.random.default_rng(3)
    X = minutes_mod.redraw(np.array([34, 32, 30, 28, 26, 24, 20, 16, 12, 10, 8.0]), np.full(11, 40.0), np.full(11, 4.0), 200, rng_t)
    check('minutes: per-world draws re-solve to 240 in every world', bool(np.abs(X.sum(1) - 240).max() < 1e-6), float(np.abs(X.sum(1) - 240).max()))
    # D29 rotation tables: five distinct players of the side in every second; table minutes hit each table's targets
    from scripts import engine as engine_mod
    curves = np.clip(rng_t.random((3, 11, 288)), 0, 1)
    top = engine_mod.Game._fit_offsets(curves, minutes_mod.redraw(np.array([34, 32, 30, 28, 26, 24, 20, 16, 12, 10, 8.0]), np.full(11, 40.0),
                                                                         np.full(11, 3.0), 3, rng_t))
    on = np.zeros((3, 11, 288), bool)
    np.put_along_axis(on, top, True, axis=1)
    check('rotation tables: five distinct players in every 10-second bin; 240 minutes per table',
          bool((on.sum(1) == 5).all()) and bool(np.allclose(on.sum((1, 2)) * 10 / 60, 240)))
    # D30 matchups: the soft assignment is a distribution over the five on court
    from scripts import matchups as matchups_mod
    theta_path = sorted((ROOT / 'models').glob('matchup_*.json'))
    if theta_path:
        th = json.loads(theta_path[-1].read_text())
        A = {'height_in': rng_t.normal(78, 3, 50), 'weight_lb': rng_t.normal(215, 20, 50), 'grp_code': rng_t.integers(0, 3, 50).astype(float),
             'min_avg': rng_t.uniform(10, 36, 50)}
        D = {k: np.stack([v] * 5, 1) + rng_t.normal(0, 1, (50, 5)) for k, v in A.items()}
        D['grp_code'] = rng_t.integers(0, 3, (50, 5)).astype(float)
        a = matchups_mod.assignment(th, A, D)
        check(f'matchups: assignment rows sum to 1 over the five defenders ({theta_path[-1].name})',
              bool(np.allclose(a.sum(1), 1)) and bool((a > 0).all()))
    # Projected starters: an empty scored set has no overall; otherwise check the weighted scores.
    lin = DERIVED / 'lineups' / 'accuracy.json'
    if lin.exists():
        rec = json.loads(lin.read_text())
        sl = list(rec['slates'].values())
        n = sum(r['team_games'] for r in sl)
        check(f'lineups: scored starter accuracy is consistent ({len(sl)} slates, {n} team-games)',
              lineup_accuracy_consistent(rec))

    teams = read_json(DERIVED / 'teams.json')
    registry = read_json(DERIVED / 'players.json')['players']
    snaps = sorted(p for p in SNAPSHOTS.iterdir() if p.is_dir() and not p.name.startswith('.'))
    check('snapshots exist', bool(snaps))
    for snap in snaps:
        day = snap.name
        meta = read_json(snap / 'meta.json')
        games = read_json(snap / 'games.json')
        season = read_json(snap / 'season.json')
        stats = read_json(snap / 'stats.json')
        if args.fault and snap == snaps[-1]:
            first = next(iter(games.values()))
            first['periods']['fg']['home']['win'] = round(first['periods']['fg']['home']['win'] + 0.02, 4)
        W = meta['sims']
        origin = meta.get('origin', day)
        before = [r for r in finals if r['date_et'] < origin]
        T = stats['teams']
        check(f'{day}: W total = L total = finals before cutoff', sum(t['w'] for t in T.values()) == sum(t['l'] for t in T.values()) == len(before),
              (sum(t['w'] for t in T.values()), len(before)))
        if 'origin' in meta:
            check(f'{day}: snapshot and season share the forecast origin',
                  origin <= day and meta['cutoff'] == day_shift(origin, -1) and season['as_of'] == origin)
        problems = []
        for gid, g in games.items():
            if g.get('shooting_distribution_schema') not in (None, 1):
                problems.append(f'{gid} unknown shooting distribution schema')
            for period, x in g['periods'].items():
                total_p = x['home']['win'] + x['away']['win'] + (0 if period == 'fg' else x['home']['tie'])
                if abs(total_p - 1) > 1e-3:
                    problems.append(f'{gid} {period} win/tie probabilities sum {total_p}')
                for name, d in [('margin', x['margin']), ('total', x['total']), ('home', x['home']['pts']), ('away', x['away']['pts'])]:
                    if hist_total(d) != W:
                        problems.append(f'{gid} {period} {name} hist {hist_total(d)}')
                if abs(hist_mean(x['margin']) - (hist_mean(x['home']['pts']) - hist_mean(x['away']['pts']))) > 1e-6:
                    problems.append(f'{gid} {period} margin mean')
                for side in ('home', 'away'):
                    playing = [p for p in g[side]['players'] if 'periods' in p]
                    total = sum(p['periods'][period]['mean']['pts'] for p in playing)
                    if abs(total - x[side]['pts']['mean']) > 0.005 * len(playing) + 0.01:
                        problems.append(f'{gid} {side} {period} player points {total:.2f} vs team {x[side]["pts"]["mean"]:.2f}')
                    if period in ('q1', 'q2', 'q3', 'q4'):
                        seconds = sum(p['periods'][period]['sec'] for p in playing)
                        if abs(seconds - 3600) > 30:
                            problems.append(f'{gid} {side} {period} player-seconds {seconds:.0f} (expected 3600)')
                    for p in playing:
                        hist_errors = player_hist_problems(p['periods'][period]['stats'], W, g.get('shooting_distribution_schema') == 1)
                        if hist_errors:
                            problems.append(f'{gid} {p["id"]} {period} {hist_errors[0]}')
                            break
            fg = g['periods']['fg']
            p_home = sum(c for i, c in enumerate(fg['margin']['hist']) if fg['margin']['min'] + i > 0) / W
            if abs(p_home - fg['home']['win']) > 1e-4:
                problems.append(f'{gid} margin histogram win {p_home} vs {fg["home"]["win"]}')
            for side in ('home', 'away'):
                for p in g[side]['players']:
                    if 'periods' not in p:
                        continue
                    parts = sum(p['periods'][q]['mean']['pts'] for q in ('q1', 'q2', 'q3', 'q4'))
                    if parts > p['periods']['fg']['mean']['pts'] + 0.0025:  # four values rounded to 3 dp
                        problems.append(f'{gid} {p["id"]} quarters exceed full game')
        check(f'{day}: game simulations reconcile ({len(games)} games)', not problems, problems[:3])
        seed_problems = []
        for conf in ('East', 'West'):
            members = [t for t in teams if teams[t]['conf'] == conf]
            for k in range(15):
                total = sum(season['teams'][t]['seeds'][k] for t in members)
                if abs(total - 1) > 2e-3:
                    seed_problems.append(f'{conf} seed {k + 1} sums {total:.4f}')
        for t, f in season['teams'].items():
            if abs(sum(f['seeds']) - 1) > 2e-3:
                seed_problems.append(f'{t} seeds sum {sum(f["seeds"]):.4f}')
            if not f['w'] <= f['mean_w'] <= f['w'] + f['remaining']:
                seed_problems.append(f'{t} mean wins out of range')
            if hist_total(f['wins']) != season['sims']:
                seed_problems.append(f'{t} wins hist')
        check(f'{day}: season seeds partition and wins stay in range', not seed_problems, seed_problems[:3])
        if season.get('engine_games'):  # D25: universe k plays engine world k, so a game's season win % is the engine's
            rows = {r['game_id']: r for r in season['games']}
            off = [g for g in season['engine_games'] if g in games and abs(rows[g]['p_home'] - games[g]['periods']['fg']['home']['win']) > 5e-5]
            check(f'{day}: season plays the engine\'s worlds ({len(season["engine_games"])} games, win % identical)', not off, off[:3])

    latest = snaps[-1]
    day = latest.name
    meta = read_json(latest / 'meta.json')
    games = read_json(latest / 'games.json')
    if games and meta['inputs']['player_games_sha256'] == __import__('basketball_common').sha256_file(DERIVED / 'player_games.csv') and meta['kind'] == 'prospective' and meta['inputs'].get('registry_run') == read_json(DERIVED / 'players.json')['run']:
        origin = meta.get('origin', day)
        T, lg = team_table(team_rows, origin, teams)
        P = player_table(player_rows, origin)
        Q, priors = period_profiles(period_rows, player_rows, origin, team_rows, blowout=15)
        gid = sorted(games)[0]
        stored = games[gid]
        if args.fault:
            stored = json.loads(json.dumps(stored))
            stored['periods']['fg']['home']['pts']['mean'] += 0.1
        if meta['model'].get('kind') in ('engine', 'preview'):  # possession engine: also needs its own inputs unchanged
            from basketball_common import sha256_file
            from scripts import engine as engine_mod
            node_models = meta['model'].get('models', meta['model'].get('version', 'v1'))  # v1.2+: node models named separately
            hashed = meta['inputs']['engine_inputs_sha256']
            same = all(sha256_file(f) == hashed[k] for k, f in (
                ('latest', engine_mod.features_dir(node_models) / 'latest.parquet'), ('team_latest', engine_mod.features_dir(node_models) / 'team_latest.parquet'),
                ('stints', DERIVED / 'rotations' / 'stints.parquet'), ('on_court', DERIVED / 'rotations' / 'on_court.parquet'),
                ('models', DERIVED.parent / 'models' / node_models / 'config.json')) if k in hashed)
            if same:
                g = engine_mod.inputs_for(by_id[gid], day, T, lg, P, registry, Q, priors,
                                          rotation=meta['model'].get('rotation', 'replay'), models=node_models, origin=origin)
                again = engine_mod.Engine(node_models).simulate(g, meta['sims'], projection.seed_for(meta['model']['id'], day, gid))
                again = json.loads(json.dumps(again))
            else:
                again = None
                print(f'SKIP  engine re-simulation: engine inputs changed since the {day} snapshot')
        else:
            again = projection.simulate_game(by_id[gid], T, lg, P, registry, day, True, meta['sims'], Q, priors)
        if again is not None:
            if 'availability_report' in stored:
                from scripts.nightly import forecast_availability_report
                again['availability_report'] = forecast_availability_report(by_id[gid], registry)
            else:
                for side in ('home', 'away'):
                    for player in again[side]['players']:
                        player.pop('availability_basis', None)
                print(f'NOTE  legacy {day} replay checks reproducibility, not origin or report provenance')
            align_legacy_shooting_schema(stored, again)
            check(f'{day}: stored game {gid} re-simulates bit-for-bit ({meta["model"]["id"]})',
                  json.dumps(again, sort_keys=True) == json.dumps(stored, sort_keys=True))
    else:
        print(f'SKIP  re-simulation: inputs changed since the {day} snapshot (expected after new collections)')

    # Team pathway (D25): the season re-simulates bit-for-bit from the snapshot dated on its as-of day (its stats are the
    # pathway's start) and the stored engine worlds, while the fixture list is unchanged.
    pathway_snaps = [p for p in snaps if read_json(p / 'season.json').get('as_of') == p.name and (p / 'meta.json').exists()]
    if pathway_snaps:
        snap = pathway_snaps[-1]
        meta, season = read_json(snap / 'meta.json'), read_json(snap / 'season.json')
        if meta['inputs']['master_sha256'] == __import__('basketball_common').sha256_file(MASTER_CSV):
            import numpy as np
            st = read_json(snap / 'stats.json')
            worlds = {}
            for p in snaps:  # every snapshot written with this season carries its own slate's engine worlds
                if (p / 'engine_worlds.npz').exists() and read_json(p / 'season.json').get('as_of') == snap.name:
                    with np.load(p / 'engine_worlds.npz') as z:
                        worlds.update({k: z[k] for k in z.files})
            again = json.loads(json.dumps(projection.simulate_season(st['teams'], st['league'], master, snap.name, teams,
                                                                     worlds or None, season['sims'], season['pathway'])))
            for tid, t in season['teams'].items():
                if 'bottom3' not in t:
                    again['teams'][tid].pop('bottom3', None)
            if args.fault:
                season['games'][0]['p_home'] += 1e-4
            check(f'{snap.name}: season re-simulates bit-for-bit ({season["model"]}, {len(worlds)} engine games)',
                  json.dumps(again, sort_keys=True) == json.dumps(season, sort_keys=True))
        else:
            print(f'SKIP  season re-simulation: fixtures changed since the {snap.name} snapshot')

    api = VIEWS / 'api'
    view_meta = read_json(api / 'meta.json')
    missing = [d for d in {r['date_et'] for r in master} if not (api / 'slate' / f'{d}.json').exists()]
    check('views: every slate date has a view', not missing, missing[:3])
    check('views: every game has a view', all((api / 'game' / f'{g}.json').exists() for g in ids))
    from scripts.views import current_snapshot
    check('views: meta latest = newest snapshot dated today (ET) or earlier', view_meta['latest'] == current_snapshot([p.name for p in snaps]))
    g0 = sorted(games)[0] if games else None
    if g0:
        view = read_json(api / 'game' / f'{g0}.json')
        check('views: game view carries the snapshot projection',
              view['projection'] and view['projection']['sim']['periods']['fg']['home']['win'] == games[g0]['periods']['fg']['home']['win'])
    # Joint outcomes (app Scenarios, Given…, drivers): in every stored world each side's player points sum to its points,
    # and the worlds' means equal the snapshot's projected means
    import base64
    import numpy as np
    wfiles = sorted((VIEWS / 'api' / 'game').glob('*/worlds.json'))
    if wfiles:
        wf = wfiles[0]
        w = read_json(wf)
        W_, n_ = w['worlds'], len(w['players'])
        L = np.frombuffer(base64.b64decode(w['lines']), np.uint8).reshape(W_, n_, len(w['stats'])).astype(int)
        T = np.frombuffer(base64.b64decode(w['team_periods']), np.uint8).reshape(W_, 2, 5).astype(int)
        if args.fault:
            T = T.copy()
            T[0, 0, 0] += 1
        side = np.array(w['side'])
        pts = L[:, :, w['stats'].index('pts')]
        ok = all(np.array_equal(pts[:, side == s].sum(1), T[:, s].sum(1)) for s in (0, 1))
        gv = read_json(VIEWS / 'api' / 'game' / f'{wf.parent.name}.json')
        home_mean = gv['projection']['sim']['periods']['fg']['home']['pts']['mean']
        check(f'worlds: player points sum to team points in all {W_:,} worlds; mean equals the projection ({wf.parent.name}, {len(wfiles)} games)',
              ok and abs(T[:, 0].sum(1).mean() - home_mean) < 0.05, (ok, round(float(T[:, 0].sum(1).mean()), 2), home_mean))

    # D32 NBA Stats: raw retention, one-to-one crosswalk, matchups = raw, real weights sum to 1, pair history cutoff-safe
    nb_raw, nb = DATA / 'raw' / 'nbastats', DERIVED / 'nbastats'
    if (nb / 'games.parquet').exists():
        import gzip
        import hashlib
        import json as _json
        import pandas as pd
        bad = 0
        manifests = sorted(nb_raw.glob('*/*/manifest.json'))
        for mf in manifests:
            man = _json.loads(mf.read_text())
            for key in list(man)[-2:]:
                body = gzip.decompress((mf.parent / f'{key}.json.gz').read_bytes())
                sha = man[key]['sha256'] if not (args.fault and mf == manifests[-1]) else '0' * 64
                bad += hashlib.sha256(body).hexdigest() != sha or len(body) != man[key]['bytes']
        check(f'nbastats: raw files match their manifests (sha256, bytes; {len(manifests)} folders)', bad == 0, bad)
        g = pd.read_parquet(nb / 'games.parquet')
        pl = pd.read_parquet(nb / 'players.parquet')
        if args.fault:
            pl = pd.concat([pl, pl.iloc[:1]])
        check(f'nbastats: crosswalk one-to-one ({len(g):,} games, {len(pl):,} people)',
              not g['espn_game'].duplicated().any() and not g['nba_game'].duplicated().any()
              and not pl['person'].duplicated().any() and not pl['player'].duplicated().any())
        if (nb / 'matchups.parquet').exists():
            from scripts import nbastats, realmatch
            M = pd.read_parquet(nb / 'matchups.parquet')
            gid = M['nba_game'].iloc[-1]
            season = g.loc[g['nba_game'] == gid, 'season'].iloc[0]
            raw = pd.DataFrame(nbastats.matchup_rows(_json.loads(gzip.decompress((nb_raw / 'boxscorematchupsv3' / season / f'{gid}.json.gz').read_bytes()))))
            mine = M[M['nba_game'] == gid]
            tot = float(mine['pposs'].sum()) + (0.5 if args.fault else 0)
            check(f'nbastats: matchups = raw response (game {gid}: {len(mine)} pairs, Σ partial possessions {tot:.1f})',
                  len(raw) == len(mine) and abs(float(raw['pposs'].astype(float).sum()) - tot) < 1e-6)
            from scripts import features
            seg = pd.read_parquet(sorted((DERIVED / 'history').glob('*/segments.parquet'))[-1])
            gsel = seg[seg['game_id'].astype(str) == str(mine['espn_game'].iloc[0])] if mine['espn_game'].iloc[0] in set(seg['game_id'].astype(str)) else seg[seg['game_id'] == seg['game_id'].iloc[-1]]
            use = gsel[gsel['actor'].notna() & gsel['end_type'].isin(['shot', 'turnover', 'fouled'])]
            defs = use[[f'def_{i}' for i in range(1, 6)]].astype(str).to_numpy()
            Ms = M.assign(espn_game=M['espn_game'].astype(str), off_player=M['off_player'].astype(str), def_player=M['def_player'].astype(str))
            Wr = features.real_weights(use, defs, np.full(defs.shape, 0.2), (use['made'] == True).to_numpy(), (use['end_type'] == 'shot').to_numpy(),  # noqa: E712
                                       {'index': features.real_index(Ms[Ms['espn_game'].isin(set(use['game_id'].astype(str)))])})
            if args.fault:
                Wr[0, 0] += 0.1
            check(f'features: real matchup weights over the five sum to 1 ({len(use)} uses)', np.allclose(Wr.sum(1), 1.0))
            if (nb / 'pair_history.parquet').exists():
                H = realmatch.load_pair_history()
                Mr = realmatch.load()
                last = H[H['pair_met'] > 0].iloc[-1]
                day = str(H.loc[H['espn_game'] == last['espn_game'], 'date'].iloc[0])
                st = realmatch.pair_state(Mr, day)
                row = st[(st['off_player'] == last['off_player']) & (st['def_player'] == last['def_player'])]
                v = float(row['pair_hist'].iloc[0]) + (0.1 if args.fault else 0) if len(row) else np.nan
                check(f'realmatch: pair history uses only earlier games (game {last["espn_game"]}, pair state before {day})',
                      len(row) == 1 and abs(v - float(last['pair_hist'])) < 1e-9, (v, float(last['pair_hist'])))

    # D36 phone bundle: per-world files left out, the worlds flag off, no duel of the night (localhost views keep them)
    from scripts import export_musnba
    gfile = next(iter(sorted((VIEWS / 'api' / 'game').glob('*.json'))), None)
    if gfile is not None:
        gkey = '/api/game/' + gfile.stem
        body = json.loads(export_musnba.phone_record(gkey, gfile.read_text()))
        sfile = sorted((VIEWS / 'api' / 'slate').glob('*.json'))[-1]
        slate = json.loads(export_musnba.phone_record('/api/slate/' + sfile.stem, sfile.read_text()))
        dropped = export_musnba.phone_record(gkey + '/worlds', '{}') is None
        if args.fault:
            body['worlds'] = True
        check('phone bundle: per-world files dropped, worlds flag off, no duel of the night (D36)',
              dropped and body.get('worlds') is False and all('duel' not in (g.get('proj') or {}) for g in slate.get('games', [])))
    # Multi-doubles and 5×5 (views, from the stored worlds): nested chances; final-wins distributions sum to the seasons
    newest = sorted(d.name for d in SNAPSHOTS.iterdir() if d.is_dir())[-2:]  # today's and tomorrow's projected slates
    slate_games = [g['id'] for d in newest if (VIEWS / 'api' / 'slate' / f'{d}.json').exists()
                   for g in read_json(VIEWS / 'api' / 'slate' / f'{d}.json').get('games', [])]
    multis = [m for gid in slate_games if (VIEWS / 'api' / 'game' / f'{gid}.json').exists()
              for m in (read_json(VIEWS / 'api' / 'game' / f'{gid}.json').get('multi') or {}).values()]
    if multis:
        if args.fault:
            multis[0] = {**multis[0], 'triple': multis[0]['double'] + 0.01}
        ok = all(m['double'] >= m['triple'] >= m['quadruple'] >= m['quintuple'] >= 0 and m['five_by_five'] <= m['double'] + 1e-9 for m in multis)
        check(f'multi-doubles nested: double ≥ triple ≥ quadruple ≥ quintuple, 5×5 ≤ double ({len(multis)} players)', ok)
    st = read_json(sorted((VIEWS / 'api' / 'standings').glob('*.json'))[-1])
    sims = st.get('sims')
    tot = [sum(t['forecast']['wins']['hist']) for t in st['teams'] if t.get('forecast', {}).get('wins')]
    if tot:
        if args.fault:
            tot[0] += 1
        check(f'standings: every team\'s final-wins distribution sums to the {sims:,} simulated seasons (Wins tab)', all(x == sims for x in tot))

    # Dashboard U15/U18/U19: presentation outputs reconcile to their retained sources.
    role_views = [read_json(p) for p in (VIEWS / 'api' / 'team').glob('*.json')]
    projected_roles = [t for t in role_views if t.get('tonight')]
    if args.fault and projected_roles:
        projected_roles[0]['tonight']['sims'] += 1
    role_ok = True
    for t in projected_roles:
        nxt = t['tonight']
        game = read_json(VIEWS / 'api' / 'game' / (nxt['game_id'] + '.json'))['projection']['sim']
        side = 'home' if game['home']['team_id'] == t['team']['id'] else 'away'
        expected = {str(p['id']): p for p in game[side]['players']}
        role_ok &= set(nxt['players']) == set(expected) and nxt['sims'] == game['sims']
        for pid, role in nxt['players'].items():
            source = expected[pid]
            mean = source['periods']['fg']['stats']['min']['mean'] if source.get('periods') else None
            role_ok &= ((mean is None and role['min'] is None) or
                        (mean is not None and role['min'] is not None and abs(role['min'] - mean) <= .050001))
            role_ok &= role['starter'] == bool(source.get('starter'))
    check(f'roster roles: next-game minutes/starters and simulation counts equal stored games ({len(projected_roles)} teams)',
          bool(projected_roles) and role_ok)

    bottom = [t['forecast'].get('bottom3') for t in st['teams']]
    if all(v is not None for v in bottom):
        total = sum(bottom) + (.01 if args.fault else 0)
        check('season races: bottom-three probabilities sum to 3; worst-record chance is nested',
              abs(total - 3) < .002 and all(0 <= t['forecast']['worst_record'] <= t['forecast']['bottom3'] <= 1
                                           for t in st['teams']))
    movers = read_json(VIEWS / 'api' / 'season_movers.json')
    if movers.get('from'):
        keys = ('mean_w', 'top6', 'playin', 'first')
        if args.fault:
            movers['teams'][0]['delta']['mean_w'] += .1
        delta_ok = all(abs(t['now'][k] - t['before'][k] - t['delta'][k]) < .000051
                       for t in movers['teams'] for k in keys)
        source_results = {r['game_id'] for r in master if r['status'] == 'final' and movers['from'] <= r['date_et'] < movers['to']}
        listed_results = {r['id'] for r in movers['results']}
        check('season movers: 30 teams, deltas = now minus before; results exactly cover distinct-cutoff interval',
              len(movers['teams']) == len({t['id'] for t in movers['teams']}) == 30 and delta_ok
              and movers['from'] < movers['to'] and source_results == listed_results)

    failed = results.count(False)
    print(f'\n{len(results) - failed}/{len(results)} checks passed')
    return 1 if failed else 0


if __name__ == '__main__':
    raise SystemExit(main())
