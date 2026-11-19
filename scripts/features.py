#!/usr/bin/env python3
"""Point-in-time player profiles (TRAINING_PLAN.md §2–§4; ENGINE_PLAN M4).

For every player before every game: decayed, shrunk rates built only from his earlier games.

  1. Per player-game counts from M2 segments (on-court exposures, actor events, assists, rebounds, blocks,
     steals, fouls, free throws, quarter usage) and M3 on-court minutes.
  2. Decayed pre-game sums per stat family: S <- S·0.5^(1/h) after each game, × carry at a new season.
  3. Shrinkage toward position-group priors from earlier seasons: (count + k·prior) / (exposure + k).

Outputs data/derived/features/pregame.parquet (one row per player-game, features as of tip-off),
latest.parquet (profiles after each player's last game, for live projections) and features_report.json.
Decay and prior settings are starting values for the validation folds (TRAINING_PLAN §5, §7).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import DERIVED, NBA_TEAM_IDS, write_json  # noqa: E402

OUT = DERIVED / 'features'
ZONES = ('rim', 'paint', 'mid', 'corner3', 'above3')
FAMILIES = {  # half-life in games, carry-over into a new season
    'role': (5, 0.3), 'usage': (15, 0.6), 'accuracy': (40, 0.8), 'ft': (60, 0.8),
}
PRIOR_K = {'usage': 200, 'shot_mix': 50, 'rim': 30, 'paint': 40, 'mid': 50, 'corner3': 80, 'above3': 150, 'ft': 40,
           'assisted': 40, 'ast': 100, 'oreb': 100, 'dreb': 150, 'stl': 300, 'blk': 200, 'pf': 300, 'quarter': 100,
           'tov': 100, 'foul_drawn': 100}


def group(pos) -> str:
    p = str(pos or '').upper()
    return 'C' if p.startswith('C') else 'G' if p.startswith('G') or p in ('PG', 'SG') else 'F'


def sources():
    """(segments, on_court) per season, history first, then the current season."""
    out = []
    for season_dir in sorted((DERIVED / 'history').glob('*/')):
        seg, on = season_dir / 'segments.parquet', season_dir / 'on_court.parquet'
        if seg.exists() and on.exists():
            out.append((seg, on))
    if (DERIVED / 'segments.parquet').exists() and (DERIVED / 'rotations' / 'on_court.parquet').exists():
        out.append((DERIVED / 'segments.parquet', DERIVED / 'rotations' / 'on_court.parquet'))
    return out


def counts_for(seg: pd.DataFrame, on: pd.DataFrame) -> pd.DataFrame:
    """Per player-game exposures and events (reconciled games only)."""
    seg = seg[seg['game_ok'] & seg['offense'].astype(str).isin(NBA_TEAM_IDS) & seg['defense'].astype(str).isin(NBA_TEAM_IDS)].copy()  # reconciled NBA games (no All-Star games)
    seg['seg_id'] = np.arange(len(seg))
    off = seg.melt(id_vars=['seg_id', 'game_id', 'period'], value_vars=[f'off_{i}' for i in range(1, 6)], value_name='player').dropna(subset=['player'])
    dfn = seg.melt(id_vars=['seg_id', 'game_id'], value_vars=[f'def_{i}' for i in range(1, 6)], value_name='player').dropna(subset=['player'])
    parts = []
    parts.append(off.groupby(['game_id', 'player']).size().rename('off_segs'))
    for q in (1, 2, 3, 4):
        parts.append(off[off['period'] == q].groupby(['game_id', 'player']).size().rename(f'off_segs_q{q}'))
    parts.append(dfn.groupby(['game_id', 'player']).size().rename('def_segs'))
    use = seg[seg['actor'].notna() & seg['end_type'].isin(['shot', 'fouled', 'turnover', 'foul'])]
    use = use[(use['end_type'] != 'foul') | (use['fta'] > 0)]
    use = use[~((use['end_type'] == 'shot') & use['heave'])]
    a = use.rename(columns={'actor': 'player'})
    parts.append(a.groupby(['game_id', 'player']).size().rename('uses'))
    for q in (1, 2, 3, 4):
        parts.append(a[a['period'] == q].groupby(['game_id', 'player']).size().rename(f'uses_q{q}'))
    shots = a[a['end_type'] == 'shot']
    parts.append(shots.groupby(['game_id', 'player']).size().rename('shots'))
    for z in ZONES:
        zs = shots[shots['zone'] == z]
        parts.append(zs.groupby(['game_id', 'player']).size().rename(f'att_{z}'))
        parts.append(zs[zs['made'] == True].groupby(['game_id', 'player']).size().rename(f'made_{z}'))
    made = shots[shots['made'] == True]
    parts.append(made.groupby(['game_id', 'player']).size().rename('made'))
    parts.append(made[made['assister'].notna()].groupby(['game_id', 'player']).size().rename('assisted'))
    parts.append(a[a['end_type'] == 'turnover'].groupby(['game_id', 'player']).size().rename('tov'))
    parts.append(a[(a['end_type'] == 'turnover') & (a['turnover'] == 'live')].groupby(['game_id', 'player']).size().rename('tov_live'))
    parts.append(a[a['end_type'].isin(['fouled', 'foul'])].groupby(['game_id', 'player']).size().rename('fouls_drawn'))
    ft = seg[seg['actor'].notna() & (seg['fta'] > 0)].rename(columns={'actor': 'player'})
    parts.append(ft.groupby(['game_id', 'player'])['fta'].sum().rename('fta'))
    parts.append(ft.groupby(['game_id', 'player'])['ftm'].sum().rename('ftm'))
    parts.append(seg[seg['assister'].notna()].groupby(['game_id', 'assister']).size().rename_axis(['game_id', 'player']).rename('ast'))
    made_seg = seg[(seg['end_type'] == 'shot') & (seg['made'] == True)][['seg_id', 'actor']]
    ast_opp = off.merge(made_seg, on='seg_id')
    ast_opp = ast_opp[ast_opp['player'] != ast_opp['actor']]
    parts.append(ast_opp.groupby(['game_id', 'player']).size().rename('ast_opp'))
    reb = seg[seg['rebound'].notna()][['seg_id', 'rebound', 'rebounder']]
    parts.append(off.merge(reb[['seg_id']], on='seg_id').groupby(['game_id', 'player']).size().rename('oreb_opp'))
    parts.append(dfn.merge(reb[['seg_id']], on='seg_id').groupby(['game_id', 'player']).size().rename('dreb_opp'))
    pr = seg[seg['rebound'].isin(['off', 'def']) & seg['rebounder'].notna()]
    parts.append(pr[pr['rebound'] == 'off'].groupby(['game_id', 'rebounder']).size().rename_axis(['game_id', 'player']).rename('oreb'))
    parts.append(pr[pr['rebound'] == 'def'].groupby(['game_id', 'rebounder']).size().rename_axis(['game_id', 'player']).rename('dreb'))
    parts.append(seg[seg['blocker'].notna()].groupby(['game_id', 'blocker']).size().rename_axis(['game_id', 'player']).rename('blk'))
    two = seg[(seg['end_type'] == 'shot') & (seg['value'] == 2)][['seg_id']]
    parts.append(dfn.merge(two, on='seg_id').groupby(['game_id', 'player']).size().rename('blk_opp'))
    parts.append(seg[seg['stealer'].notna()].groupby(['game_id', 'stealer']).size().rename_axis(['game_id', 'player']).rename('stl'))
    parts.append(seg[seg['fouler'].notna()].groupby(['game_id', 'fouler']).size().rename_axis(['game_id', 'player']).rename('pf'))
    counts = pd.concat(parts, axis=1).fillna(0)
    minutes = on.copy()
    for q in (1, 2, 3, 4):
        minutes[f'sec_q{q}'] = minutes[[f'm{m:02d}' for m in range((q - 1) * 12 + 1, q * 12 + 1)]].sum(axis=1) * 60
    keep = ['game_id', 'player', 'date_et', 'season', 'season_type', 'team', 'pos', 'starter', 'sec'] + [f'sec_q{q}' for q in (1, 2, 3, 4)]
    minutes = minutes[keep].set_index(['game_id', 'player'])
    df = minutes.join(counts, how='inner').reset_index()
    df['games'] = 1.0
    df['starts'] = df['starter'].astype(float)
    df['segs_on'] = df['off_segs'] + df['def_segs']
    return df


TEAM_STYLE = {'half_life': 15, 'carry': 0.5}  # games; style follows the coach and roster, so it resets faster than skills
TEAM_RATES = {  # feature: (numerator, denominator, prior strength) — style tendencies only, never strength (D18)
    't_pace': ('t_sum', 'n_timed', 100), 't_three': ('three', 'shots', 200), 't_rim': ('rim', 'shots', 200),
    't_tov': ('tov', 'uses', 200), 't_foul': ('fouled', 'uses', 200), 't_oreb': ('oreb', 'reb_opp', 200),
}


def team_counts(seg: pd.DataFrame) -> pd.DataFrame:
    """Per team-game style counts as the offence (off_*) and as the defence (def_*), reconciled games only."""
    seg = seg[seg['game_ok'] & seg['offense'].astype(str).isin(NBA_TEAM_IDS) & seg['defense'].astype(str).isin(NBA_TEAM_IDS)]
    timed = (seg['start_clock'] > 24) & ~seg['end_type'].isin(['end_period', 'unknown']) & (seg['start_type'] != 'oreb')
    use = seg['actor'].notna() & seg['end_type'].isin(['shot', 'fouled', 'turnover', 'foul']) & ~seg['heave'].fillna(False).astype(bool)
    use &= (seg['end_type'] != 'foul') | (seg['fta'] > 0)
    shots = use & (seg['end_type'] == 'shot') & seg['zone'].isin(ZONES)
    c = pd.DataFrame({'n_timed': timed.astype(float), 't_sum': np.where(timed, seg['shot_time'].clip(lower=0), 0.0),
                      'uses': use.astype(float), 'shots': shots.astype(float),
                      'three': (shots & seg['zone'].isin(['corner3', 'above3'])).astype(float), 'rim': (shots & (seg['zone'] == 'rim')).astype(float),
                      'tov': (use & (seg['end_type'] == 'turnover')).astype(float),
                      'fouled': (use & seg['end_type'].isin(['fouled', 'foul'])).astype(float),
                      'reb_opp': seg['rebound'].notna().astype(float), 'oreb': seg['rebound'].isin(['off', 'team_off']).astype(float)})
    c[['game_id', 'offense', 'defense', 'date_et', 'season']] = seg[['game_id', 'offense', 'defense', 'date_et', 'season']]
    cols = list(TEAM_COUNT_COLUMNS)
    off = c.groupby(['game_id', 'offense', 'date_et', 'season'])[cols].sum().add_prefix('off_')
    dfn = c.groupby(['game_id', 'defense', 'date_et', 'season'])[cols].sum().add_prefix('def_')
    off.index.names = dfn.index.names = ['game_id', 'team', 'date_et', 'season']
    return off.join(dfn, how='outer').fillna(0).reset_index()


TEAM_COUNT_COLUMNS = ('n_timed', 't_sum', 'uses', 'shots', 'three', 'rim', 'tov', 'fouled', 'reb_opp', 'oreb')


def team_profiles(tc: pd.DataFrame, half_life: float, carry: float) -> pd.DataFrame:
    """Pre-game team style (decayed, shrunk to the league rate of earlier seasons), rest days and day of season."""
    tc = tc.sort_values(['team', 'date_et', 'game_id'], kind='stable').reset_index(drop=True)
    cols = [f'{side}_{c}' for side in ('off', 'def') for c in TEAM_COUNT_COLUMNS]
    sums, _ = decayed_pregame(tc.rename(columns={'team': 'player'}), cols, half_life, carry)
    S = pd.DataFrame(sums, columns=cols)
    out = tc[['game_id', 'team', 'date_et', 'season']].copy()
    for side in ('off', 'def'):
        for feat, (num, den, k) in TEAM_RATES.items():
            league = {}
            for season in sorted(tc['season'].unique()):
                base = tc[tc['season'] < season]
                base = base if len(base) else tc[tc['season'] == season]
                league[season] = base[f'{side}_{num}'].sum() / max(base[f'{side}_{den}'].sum(), 1e-9)
            prior = tc['season'].map(league).to_numpy()
            out[f'{side}{feat[1:]}'] = (S[f'{side}_{num}'] + k * prior) / (S[f'{side}_{den}'] + k)
    return out


def schedule(seg: pd.DataFrame) -> pd.DataFrame:
    """Rest days (capped at 7; first game in the data = 7) and day of the season, per team-game, over every NBA game."""
    seg = seg[seg['offense'].astype(str).isin(NBA_TEAM_IDS) & seg['defense'].astype(str).isin(NBA_TEAM_IDS)]
    g = pd.concat([seg[['game_id', 'offense', 'date_et', 'season']].rename(columns={'offense': 'team'}),
                   seg[['game_id', 'defense', 'date_et', 'season']].rename(columns={'defense': 'team'})]).drop_duplicates(['game_id', 'team'])
    g = g.sort_values(['team', 'date_et', 'game_id']).reset_index(drop=True)
    d = pd.to_datetime(g['date_et'])
    g['rest_days'] = (d - d.groupby(g['team']).shift()).dt.days.clip(upper=7).fillna(7)
    g['season_day'] = (d - d.groupby(g['season']).transform('min')).dt.days
    return g[['game_id', 'team', 'rest_days', 'season_day']]


FAMILY_COLUMNS = {
    'role': ['games', 'starts', 'sec', 'sec_q1', 'sec_q2', 'sec_q3', 'sec_q4'],
    'usage': ['off_segs', 'def_segs', 'segs_on', 'uses', 'shots', 'tov', 'tov_live', 'fouls_drawn', 'ast', 'ast_opp', 'oreb',
              'oreb_opp', 'dreb', 'dreb_opp', 'stl', 'blk', 'blk_opp', 'pf', 'made', 'assisted']
             + [f'att_{z}' for z in ZONES] + [f'uses_q{q}' for q in (1, 2, 3, 4)] + [f'off_segs_q{q}' for q in (1, 2, 3, 4)],
    'accuracy': [f'att_{z}' for z in ZONES] + [f'made_{z}' for z in ZONES],
    'ft': ['fta', 'ftm'],
}


def decayed_pregame(df: pd.DataFrame, columns, half_life: float, carry: float):
    """Decayed sums of each column over the player's earlier games (pre-game), plus the post-last-game state."""
    vals = df[columns].to_numpy(float)
    players, seasons = df['player'].to_numpy(), df['season'].to_numpy()
    d = 0.5 ** (1.0 / half_life)
    out = np.zeros_like(vals)
    latest = {}
    S = np.zeros(len(columns))
    last_p, last_s = None, None
    for i in range(len(df)):
        if players[i] != last_p:
            if last_p is not None:
                latest[last_p] = S.copy()
            S = np.zeros(len(columns))
            last_p, last_s = players[i], seasons[i]
        elif seasons[i] != last_s:
            S *= carry
            last_s = seasons[i]
        out[i] = S
        S = S * d + vals[i]
    if last_p is not None:
        latest[last_p] = S.copy()
    return out, latest


def priors_by_season(df: pd.DataFrame) -> dict:
    """Position-group pooled rates from seasons before each season (the first season uses itself)."""
    df = df.assign(group=df['pos'].map(group))
    out = {}
    for season in sorted(df['season'].unique()):
        base = df[df['season'] < season]
        if base.empty:
            base = df[df['season'] == season]
        g = base.groupby('group').sum(numeric_only=True)
        out[season] = g
    return out


def profiles(df: pd.DataFrame, sums: dict, priors: dict) -> pd.DataFrame:
    """Shrunk rates from decayed sums. `sums[family]` aligned with df rows."""
    f = pd.DataFrame(index=df.index)
    grp = df['pos'].map(group)
    def prior(num, den):
        return np.array([(priors[s].loc[g, num] / max(1e-9, priors[s].loc[g, den])) if g in priors[s].index else np.nan
                         for s, g in zip(df['season'], grp)])
    def shrunk(fam_num, num, fam_den, den, k):
        n, e = sums[fam_num][num], sums[fam_den][den]
        p = prior(num, den)
        return (n + k * p) / (e + k)
    role, use, acc, ft = sums['role'], sums['usage'], sums['accuracy'], sums['ft']
    f['games_eff'] = role['games']
    f['min_avg'] = np.where(role['games'] > 0, role['sec'] / 60 / np.maximum(role['games'], 1e-9), np.nan)
    f['start_share'] = np.where(role['games'] > 0, role['starts'] / np.maximum(role['games'], 1e-9), np.nan)
    for q in (1, 2, 3, 4):
        f[f'min_share_q{q}'] = np.where(role['sec'] > 0, role[f'sec_q{q}'] / np.maximum(role['sec'], 1e-9), np.nan)
    f['off_segs_eff'] = use['off_segs']
    f['usage'] = shrunk('usage', 'uses', 'usage', 'off_segs', PRIOR_K['usage'])
    f['shot_share'] = shrunk('usage', 'shots', 'usage', 'uses', PRIOR_K['tov'])
    f['tov_share'] = shrunk('usage', 'tov', 'usage', 'uses', PRIOR_K['tov'])
    f['foul_drawn_share'] = shrunk('usage', 'fouls_drawn', 'usage', 'uses', PRIOR_K['foul_drawn'])
    f['live_tov_share'] = shrunk('usage', 'tov_live', 'usage', 'tov', 20)
    for z in ZONES:
        f[f'mix_{z}'] = shrunk('usage', f'att_{z}', 'usage', 'shots', PRIOR_K['shot_mix'])
        f[f'fg_{z}'] = shrunk('accuracy', f'made_{z}', 'accuracy', f'att_{z}', PRIOR_K[z])
    f['assisted_share'] = shrunk('usage', 'assisted', 'usage', 'made', PRIOR_K['assisted'])
    f['ft_pct'] = shrunk('ft', 'ftm', 'ft', 'fta', PRIOR_K['ft'])
    f['fta_per_use'] = np.where(use['uses'] > 0, ft['fta'] / np.maximum(use['uses'], 1e-9), np.nan)
    f['ast_rate'] = shrunk('usage', 'ast', 'usage', 'ast_opp', PRIOR_K['ast'])
    f['oreb_pct'] = shrunk('usage', 'oreb', 'usage', 'oreb_opp', PRIOR_K['oreb'])
    f['dreb_pct'] = shrunk('usage', 'dreb', 'usage', 'dreb_opp', PRIOR_K['dreb'])
    f['stl_rate'] = shrunk('usage', 'stl', 'usage', 'def_segs', PRIOR_K['stl'])
    f['blk_rate'] = shrunk('usage', 'blk', 'usage', 'blk_opp', PRIOR_K['blk'])
    f['pf_rate'] = shrunk('usage', 'pf', 'usage', 'segs_on', PRIOR_K['pf'])
    overall = use['uses'] / np.maximum(use['off_segs'], 1e-9)
    for q in (1, 2, 3, 4):
        rate_q = use[f'uses_q{q}'] / np.maximum(use[f'off_segs_q{q}'], 1e-9)
        w = use[f'off_segs_q{q}'] / (use[f'off_segs_q{q}'] + PRIOR_K['quarter'])
        f[f'usage_mult_q{q}'] = np.where(overall > 0, 1 + w * (rate_q / np.maximum(overall, 1e-9) - 1), 1.0)
    f['shots_eff'] = acc[[f'att_{z}' for z in ZONES]].sum(axis=1)
    f['fta_eff'] = ft['fta']
    return f


def build(out: Path = OUT, families: dict | None = None, team_style: dict | None = None) -> dict:
    families = families or FAMILIES
    team_style = team_style or TEAM_STYLE
    frames, team_frames, schedules = [], [], []
    for seg_path, on_path in sources():
        seg = pd.read_parquet(seg_path)
        frames.append(counts_for(seg, pd.read_parquet(on_path)))
        team_frames.append(team_counts(seg))
        schedules.append(schedule(seg))
    df = pd.concat(frames, ignore_index=True)
    df = df.sort_values(['player', 'date_et', 'game_id'], kind='stable').reset_index(drop=True)
    sums, latest_sums = {}, {}
    for family, (half_life, carry) in families.items():
        cols = FAMILY_COLUMNS[family]
        arr, latest = decayed_pregame(df, cols, half_life, carry)
        sums[family] = pd.DataFrame(arr, columns=cols, index=df.index)
        latest_sums[family] = latest
    priors = priors_by_season(df)
    feats = profiles(df, sums, priors)
    base = df[['game_id', 'player', 'date_et', 'season', 'season_type', 'team', 'pos', 'starter']]
    pre = pd.concat([base, feats], axis=1)
    out.mkdir(parents=True, exist_ok=True)
    pre.to_parquet(out / 'pregame.parquet', index=False)
    teams = team_profiles(pd.concat(team_frames, ignore_index=True), team_style['half_life'], team_style['carry'])
    teams = teams.merge(pd.concat(schedules, ignore_index=True), on=['game_id', 'team'], how='left')
    teams.to_parquet(out / 'team_pregame.parquet', index=False)
    # Latest profile per player: the state after his last game (for projections from today).
    last = df.groupby('player').tail(1).reset_index(drop=True)
    lsums = {fam: pd.DataFrame([latest_sums[fam][p] for p in last['player']], columns=FAMILY_COLUMNS[fam]) for fam in families}
    latest = pd.concat([last[['player', 'date_et', 'season', 'team', 'pos']], profiles(last, lsums, priors)], axis=1)
    latest.to_parquet(out / 'latest.parquet', index=False)
    # Sanity: does the pre-game profile anticipate the game?
    game_usage = df['uses'] / df['off_segs'].where(df['off_segs'] > 0)
    big = (df['off_segs'] >= 25) & (feats['games_eff'] > 0)
    three = df['att_above3'] + df['att_corner3']
    report = {'player_games': len(df), 'players': int(df['player'].nunique()), 'seasons': sorted(int(s) for s in df['season'].unique()),
              'with_history': round(float((feats['games_eff'] > 0).mean()), 4),
              'usage_corr_pregame_v_game': round(float(np.corrcoef(feats.loc[big, 'usage'], game_usage[big])[0, 1]), 3),
              'minutes_corr_pregame_v_game': round(float(np.corrcoef(feats.loc[feats['games_eff'] > 0, 'min_avg'], df.loc[feats['games_eff'] > 0, 'sec'] / 60)[0, 1]), 3),
              'three_share_corr': round(float(np.corrcoef((feats['mix_above3'] + feats['mix_corner3'])[big & (df['shots'] >= 8)],
                                                          (three / df['shots'])[big & (df['shots'] >= 8)])[0, 1]), 3),
              'families': {k: {'half_life_games': v[0], 'season_carry': v[1]} for k, v in families.items()},
              'team_style': team_style, 'team_games': len(teams), 'team_columns': [c for c in teams.columns if c not in ('game_id', 'team', 'date_et', 'season')],
              'feature_columns': list(feats.columns)}
    write_json(out / 'features_report.json', report, pretty=True)
    return report


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--out', type=Path, default=OUT, help='output folder (variants for experiments: anywhere else)')
    ap.add_argument('--family', action='append', default=[], metavar='NAME=HALF_LIFE[,CARRY]',
                    help=f'override a stat family, e.g. usage=8 or role=3,0.3 (families: {", ".join(FAMILIES)})')
    ap.add_argument('--team', default=None, metavar='HALF_LIFE[,CARRY]', help='team style decay (default 15,0.5)')
    args = ap.parse_args()
    families = dict(FAMILIES)
    for spec in args.family:
        name, value = spec.split('=')
        hl, *rest = value.split(',')
        families[name] = (float(hl), float(rest[0]) if rest else FAMILIES[name][1])
    team = dict(TEAM_STYLE)
    if args.team:
        hl, *rest = args.team.split(',')
        team = {'half_life': float(hl), 'carry': float(rest[0]) if rest else TEAM_STYLE['carry']}
    import json
    r = build(args.out, families, team)
    print(json.dumps({k: v for k, v in r.items() if k != 'feature_columns'}, indent=1))


if __name__ == '__main__':
    main()
