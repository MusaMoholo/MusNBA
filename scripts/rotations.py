#!/usr/bin/env python3
"""Rotations (ENGINE_PLAN.md M3): stints, dead-ball windows, substitutions, on-court minute shares,
and the replay-rotation baseline (v0) with its minutes backtest.

  .venv/bin/python scripts/rotations.py             current season (retained summaries)
  .venv/bin/python scripts/rotations.py --history   every downloaded historical season
  .venv/bin/python scripts/rotations.py --backtest  replay baseline v. actual minutes (2025-26 tail)

Game time t is elapsed seconds: 0–2880 in regulation, then 300 per overtime.
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import DERIVED, RAW, read_json, write_json  # noqa: E402
from scripts import pbp, plays  # noqa: E402

WINDOW_PRIORITY = ('timeout', 'foul', 'free_throw', 'dead_turnover', 'violation', 'jump_ball', 'review', 'other')


def period_base(period: int) -> int:
    return (period - 1) * 720 if period <= 4 else 2880 + (period - 5) * 300


def game_time(period: int, clock: float) -> float:
    return period_base(period) + pbp.period_length(period) - clock


def window_kind(e) -> str | None:
    k = e['type_text'].lower()
    if 'timeout' in k:
        return 'timeout'
    if e['shooting'] and e['points_attempted'] == 1:
        return 'free_throw'
    if 'foul' in k:
        return 'foul'
    if pbp.is_turnover(e) or any(w in k for w in pbp.TEAM_TURNOVERS):
        return None if 'steal' in e['text'].lower() else 'dead_turnover'
    if any(w in k for w in ('violation', 'kicked ball', 'delay', 'goaltending', '3-seconds')):
        return 'violation'
    if e['type_id'] == '615' or 'jump' in k:
        return 'jump_ball'
    if 'review' in k or 'challenge' in k or 'replay' in k:
        return 'review'
    return None


def walk(game: dict):
    """One game → stints, windows, substitutions, minute shares, issues, checks."""
    team_of, starters, box, teams, by_minutes = pbp.game_context(game)
    pos_of = {pl['id']: pl['pos'] for pl in game['players']}
    issues, checks = Counter(), Counter()
    stints, windows, subs = [], [], []
    if len(teams) != 2:
        issues['not_two_teams'] += 1
        return stints, windows, subs, {}, issues, checks
    home = game['home']
    closing = {t: list(starters[t]) for t in teams}
    fouls = Counter()
    score = {'home': 0, 'away': 0}
    for period in sorted({p['period'] for p in game['plays']}):
        events = [p for p in game['plays'] if p['period'] == period]
        events.sort(key=lambda p: -pbp.clock_seconds(p['clock']))
        length = pbp.period_length(period)
        lineup = pbp.period_starters(events, period, teams, team_of, starters, closing, by_minutes, issues)
        prev_on = {pid for t in teams for pid in closing.get(t, [])} if period > 1 else set()
        opened = {pid: float(length) for t in teams for pid in lineup[t]}
        stint_start = {pid: (game_time(period, length) if pid not in prev_on else None) for pid in opened}
        on_since = dict(stint_start)
        group_clock, group_kinds, group_subs = None, [], []

        def flush():
            if group_clock is None or (not group_kinds and not group_subs):
                return
            kind = next((k for k in WINDOW_PRIORITY if k in group_kinds), 'other')
            if kind == 'other' and group_clock == length:
                kind = 'period_start'  # changes logged at 12:00 (5:00 in overtime) before play
            margin = score['home'] - score['away']
            n_home = sum(1 for s in group_subs if s['team'] == home)
            windows.append({'game_id': game['id'], 'date_et': game['date_et'], 'season': game['season'], 'season_type': game['season_type'], 'period': period,
                            'clock': group_clock, 't': round(game_time(period, group_clock), 1), 'kind': kind,
                            'margin_home': margin, 'subs_home': n_home, 'subs_away': len(group_subs) - n_home})
            for s in group_subs:
                s.update({'kind': kind, 'margin': margin if s['team'] == home else -margin})
                subs.append(s)

        for e in events:
            clock = pbp.clock_seconds(e['clock'])
            if clock != group_clock:
                flush()
                group_clock, group_kinds, group_subs = clock, [], []
            parts = e['participants']
            if e['type_id'] == pbp.SUB and len(parts) >= 2:
                enter, leave = parts[0], parts[1]
                t = team_of.get(enter) or team_of.get(leave)
                if t not in teams:
                    continue
                for pid in (enter, leave):
                    if pid not in team_of:
                        team_of[pid] = t  # in the play-by-play but missing from the box score
                        issues['player_missing_from_box'] += 1
                t_now = game_time(period, clock)
                if leave in opened:
                    start = opened.pop(leave)
                    stints.append({'game_id': game['id'], 'date_et': game['date_et'], 'season': game['season'], 'season_type': game['season_type'], 'team': t,
                                   'player': leave, 'pos': pos_of.get(leave, ''), 'period': period, 'start_clock': start,
                                   'end_clock': clock, 'start_t': round(game_time(period, start), 1), 'end_t': round(t_now, 1),
                                   'continues': start == length and leave in prev_on})
                    group_subs.append({'game_id': game['id'], 'date_et': game['date_et'], 'season': game['season'], 'season_type': game['season_type'], 'team': t,
                                       'period': period, 'clock': clock, 't': round(t_now, 1), 'player_in': enter,
                                       'player_out': leave, 'out_fouls': fouls[leave],
                                       'out_stint_sec': round(t_now - (on_since.get(leave) if on_since.get(leave) is not None else game_time(period, length)), 1)})
                else:
                    issues['sub_out_not_on_court'] += 1
                if enter in opened:
                    issues['sub_in_already_on'] += 1
                else:
                    opened[enter] = clock
                    on_since[enter] = t_now
                continue
            kind = window_kind(e)
            if kind:
                group_kinds.append(kind)
            k = e['type_text'].lower()
            if parts and parts[0] in team_of and (pbp.is_personal_foul(e) or k in ('offensive foul turnover',)):
                fouls[parts[0]] += 1
            if e['scoring'] and e['team'] in teams:
                score['home' if e['team'] == home else 'away'] += e['score_value']
        flush()
        for pid, start in opened.items():
            stints.append({'game_id': game['id'], 'date_et': game['date_et'], 'season': game['season'], 'season_type': game['season_type'], 'team': team_of[pid],
                           'player': pid, 'pos': pos_of.get(pid, ''), 'period': period, 'start_clock': start, 'end_clock': 0.0,
                           'start_t': round(game_time(period, start), 1), 'end_t': round(game_time(period, 0.0), 1),
                           'continues': start == length and pid in prev_on})
        closing = {t: [pid for pid in opened if team_of[pid] == t] for t in teams}
        for t in teams:
            on = sum(s['start_clock'] - s['end_clock'] for s in stints if s['period'] == period and s['team'] == t)
            checks['team_periods'] += 1
            if abs(on - 5 * length) > 1:
                checks['team_period_seconds_off'] += 1
    seconds = defaultdict(float)
    shares = defaultdict(lambda: np.zeros(48))
    for s in stints:
        seconds[s['player']] += s['start_clock'] - s['end_clock']
        a, b = s['start_t'], min(s['end_t'], 2880.0)
        for m in range(int(a // 60), int(np.ceil(b / 60)) if b > a else int(a // 60)):
            if m < 48:
                shares[s['player']][m] += max(0.0, min(b, (m + 1) * 60) - max(a, m * 60)) / 60
    for pid, line in box.items():
        checks['player_games'] += 1
        if line.get('min') is not None and abs(seconds.get(pid, 0) / 60 - line['min']) > 1.01:
            checks['minutes_off'] += 1
    minute_rows = {pid: {'game_id': game['id'], 'date_et': game['date_et'], 'season': game['season'], 'season_type': game['season_type'], 'team': team_of[pid],
                         'player': pid, 'pos': pos_of.get(pid, ''), 'starter': pid in starters.get(team_of[pid], []),
                         'sec': round(seconds[pid], 1), **{f'm{m + 1:02d}': round(float(v), 3) for m, v in enumerate(shares[pid])}}
                   for pid in seconds}
    return stints, windows, subs, minute_rows, issues, checks


def build(games, out_dir: Path) -> dict:
    import pandas as pd
    all_stints, all_windows, all_subs, all_minutes = [], [], [], []
    issues, checks = Counter(), Counter()
    for game in games:
        st, wi, su, mi, i, c = walk(game)
        all_stints += st
        all_windows += wi
        all_subs += su
        all_minutes += list(mi.values())
        issues.update(i)
        checks.update(c)
    out_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(all_stints).to_parquet(out_dir / 'stints.parquet', index=False)
    pd.DataFrame(all_windows).to_parquet(out_dir / 'windows.parquet', index=False)
    pd.DataFrame(all_subs).to_parquet(out_dir / 'subs.parquet', index=False)
    pd.DataFrame(all_minutes).to_parquet(out_dir / 'on_court.parquet', index=False)
    windows = pd.DataFrame(all_windows)
    report = {'games': len({w['game_id'] for w in all_windows}), 'stints': len(all_stints), 'windows': len(all_windows),
              'subs': len(all_subs),
              'minutes_off_player_games': round(checks['minutes_off'] / max(1, checks['player_games']), 4),
              'team_period_seconds_off': round(checks['team_period_seconds_off'] / max(1, checks['team_periods']), 4),
              'subs_per_team_game': round(len(all_subs) / max(1, 2 * len({w['game_id'] for w in all_windows})), 2),
              'windows_with_subs': round(float(((windows['subs_home'] + windows['subs_away']) > 0).mean()), 4) if len(windows) else None,
              'sub_window_kinds': (pd.DataFrame(all_subs)['kind'].value_counts(normalize=True).round(4).to_dict() if all_subs else {}),
              'issues': dict(issues)}
    write_json(out_dir / 'rotations_report.json', report, pretty=True)
    return report


# ---------------------------------------------------------------- replay-rotation baseline (v0)

def templates_for(stints, team: str, before: str, n: int = 10):
    """The team's last n games before a date: each a list of slots (player, pos, minutes, stints)."""
    prior = stints[(stints['team'] == team) & (stints['date_et'] < before)]
    games = sorted(prior['game_id'].unique(), key=lambda g: prior.loc[prior['game_id'] == g, 'date_et'].iloc[0])[-n:]
    out = []
    for g in games:
        rows = prior[(prior['game_id'] == g) & (prior['start_t'] < 2880)]
        slots = []
        for pid, part in rows.groupby('player'):
            spans = [(float(a), float(min(b, 2880.0))) for a, b in zip(part['start_t'], part['end_t'])]
            slots.append({'player': pid, 'pos': part['pos'].iloc[0], 'sec': sum(b - a for a, b in spans), 'spans': spans})
        slots.sort(key=lambda s: -s['sec'])
        out.append({'game_id': g, 'slots': slots})
    return out


def group(pos: str) -> str:
    p = (pos or '').upper()
    return 'C' if p.startswith('C') else 'G' if p.startswith('G') or p in ('PG', 'SG') else 'F'


def assign(template, players):
    """Map template slots (by minutes) to available players (by expected minutes), within position groups first."""
    slots = template['slots']
    free = sorted(players, key=lambda p: -p['expected'])
    mapping, used = {}, set()
    for i, slot in enumerate(slots):
        for p in free:
            if p['id'] not in used and group(p['pos']) == group(slot['pos']):
                mapping[i] = p['id']
                used.add(p['id'])
                break
    for i, slot in enumerate(slots):
        if i in mapping:
            continue
        for p in free:
            if p['id'] not in used:
                mapping[i] = p['id']
                used.add(p['id'])
                break
    return mapping


def replay_minutes(templates, players, rng, worlds: int = 200):
    """Per-world regulation minutes for each available player under replayed rotations."""
    totals = {p['id']: np.zeros(worlds) for p in players}
    if not templates:
        return totals
    recency = np.linspace(1.0, 2.0, len(templates))
    choice = rng.choice(len(templates), size=worlds, p=recency / recency.sum())
    for w, ti in enumerate(choice):
        mapping = assign(templates[ti], players)
        for i, pid in mapping.items():
            totals[pid][w] += templates[ti]['slots'][i]['sec'] / 60
    return totals


def backtest(season: int = 2026, start: str = '2026-03-01', worlds: int = 200) -> dict:
    """Replay v. actual regulation minutes, players who played (availability known), March onward."""
    import pandas as pd
    from scripts import history
    stints = pd.read_parquet(history.OUT_DIR / str(season) / 'stints.parquet')
    on = pd.read_parquet(history.OUT_DIR / str(season) / 'on_court.parquet')
    stints = stints[stints['season_type'] == 2]  # baseline measured on the regular season
    on = on[on['season_type'] == 2]
    reg = stints[stints['start_t'] < 2880].copy()
    reg['sec'] = reg[['end_t']].clip(upper=2880)['end_t'] - reg['start_t']
    actual = reg.groupby(['game_id', 'team', 'player'])['sec'].sum().div(60).rename('actual').reset_index()
    dates = on[['game_id', 'date_et']].drop_duplicates().set_index('game_id')['date_et']
    actual['date_et'] = actual['game_id'].map(dates)
    rng = np.random.default_rng(7)
    rows = []
    games = actual[actual['date_et'] >= start]
    for (gid, team), part in games.groupby(['game_id', 'team']):
        day = part['date_et'].iloc[0]
        temps = templates_for(stints, team, day)
        if len(temps) < 5:
            continue
        prior = actual[(actual['team'] == team) & (actual['date_et'] < day)]
        players = []
        for pid in part['player']:
            hist_min = prior.loc[prior['player'] == pid, 'actual'].tail(10)
            players.append({'id': pid, 'pos': on.loc[on['player'] == pid, 'pos'].iloc[0] if (on['player'] == pid).any() else '',
                            'expected': float(hist_min.ewm(halflife=4).mean().iloc[-1]) if len(hist_min) else 0.0})
        sims = replay_minutes(temps, players, rng, worlds)
        for _, r in part.iterrows():
            v = sims[r['player']]
            exp = next(p['expected'] for p in players if p['id'] == r['player'])
            rows.append({'actual': r['actual'], 'mean': v.mean(), 'p10': np.quantile(v, 0.1), 'p90': np.quantile(v, 0.9), 'ewma': exp})
    df = pd.DataFrame(rows)
    big = df[df['actual'] >= 20]
    report = {'player_games': len(df), 'mae_replay_mean': round(float((df['mean'] - df['actual']).abs().mean()), 2),
              'mae_ewma': round(float((df['ewma'] - df['actual']).abs().mean()), 2),
              'coverage_p10_p90': round(float(((df['actual'] >= df['p10']) & (df['actual'] <= df['p90'])).mean()), 3),
              'rotation_players_mae_replay': round(float((big['mean'] - big['actual']).abs().mean()), 2),
              'rotation_players_mae_ewma': round(float((big['ewma'] - big['actual']).abs().mean()), 2),
              'sd_sim_rotation_players': round(float(((big['p90'] - big['p10']) / 2.563).mean()), 2)}
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--history', action='store_true')
    parser.add_argument('--backtest', action='store_true')
    args = parser.parse_args()
    import json
    if args.backtest:
        from scripts import history
        report = backtest()
        write_json(history.OUT_DIR / '2026' / 'replay_backtest.json', report, pretty=True)
        print(json.dumps(report, indent=1))
        return
    if args.history:
        from scripts import history
        for season in history.SEASONS:
            if (history.RAW_DIR / f'play_by_play_{season}.parquet').exists():
                print(season, json.dumps(build(history.season_games(season), history.OUT_DIR / str(season))))
        return
    from scripts import possessions
    print(json.dumps(build(possessions.current_games(), DERIVED / 'rotations'), indent=1))


if __name__ == '__main__':
    main()
