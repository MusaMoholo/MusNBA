#!/usr/bin/env python3
"""Immutable historical regular-calendar audit; no candidate fits or scores."""
from pathlib import Path
from datetime import datetime,timezone
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
import pyarrow as pa
from basketball_common import read_json,write_json,sha256_file
from scripts import season_backtest

POLICIES={
    2023:{'cup_final':None,'group_dates':[]},
    2024:{'cup_final':'401607495','group_dates':['11-03','11-10','11-14','11-17','11-21','11-24','11-28'],
          'window':['12-04','12-09'],'qf':['12-04','12-05'],'sf':'12-07','filler':['12-06','12-08'],
          'group_source':'https://www.nba.com/news/2023-nba-in-season-tournament-schedule',
          'format_source':'https://www.nba.com/news/2023-in-season-tournament-debut-official-release',
          'publication_before':'2023-08-18','sf_neutral':True,'cup_tiebreak_points':'full_game'},
    2025:{'cup_final':'401734908','group_dates':['11-12','11-15','11-19','11-22','11-26','11-29','12-03'],
          'window':['12-10','12-17'],'qf':['12-10','12-11'],'sf':'12-14','filler':['12-12','12-15'],
          'group_source':'https://www.nba.com/news/emirates-nba-cup-2024-group-play-schedule',
          'format_source':'https://www.nba.com/grizzlies/emiratesnbacup',
          'publication_before':'2024-09-05','sf_neutral':True,'cup_tiebreak_points':'regulation'},
    2026:{'cup_final':'401809839','group_dates':['10-31','11-07','11-14','11-21','11-25','11-26','11-28'],
          'window':['12-09','12-16'],'qf':['12-09','12-10'],'sf':'12-13','filler':['12-11','12-14'],
          'group_source':'https://www.nba.com/raptors/news/raptors-announce-2025-emirates-nba-cup-schedule',
          'format_source':'https://www.nba.com/news/2025-nba-cup-group-draw-results',
          'publication_before':'2025-11-06','sf_neutral':True,'cup_tiebreak_points':'regulation'}
}
WORK=ROOT/'data/derived/experiments/d42_b2_calendar_audit_v1'
REPORT=ROOT/'analysis/experiments/20261124_b2_calendar_audit_v1.json'


def connected_groups(games):
    edges={t:set(part.opp) for t,part in games.groupby('team')}
    left=set(edges);groups=[]
    while left:
        todo=[min(left,key=int)];found=set()
        while todo:
            team=todo.pop()
            if team in found:continue
            found.add(team);todo+=sorted(edges[team]-found,key=int)
        left-=found;groups.append(sorted(found,key=int))
    if len(groups)!=6 or any(len(g)!=5 for g in groups):
        raise ValueError('group fixtures do not form six published round robins')
    for group in groups:
        for team in group:
            part=games[games.team.eq(team)]
            if len(part)!=4 or set(part.opp)!=set(group)-{team} or int(part.home.sum())!=2:
                raise ValueError('group pair/home-away accounting failed')
    return groups


def load(season):
    if season not in POLICIES:raise ValueError('explicit historical season version required')
    policy=POLICIES[season];raw=season_backtest.team_games(season)
    regular=raw[~raw.game_id.astype(str).eq(policy['cup_final'])].copy()
    if (regular.groupby('team').size()!=82).any() or regular.game_id.nunique()!=1230:
        raise ValueError('historical regular calendar must be82/team and1230 games')
    if regular.duplicated(['game_id','team']).any() or not regular.groupby('game_id').size().eq(2).all():
        raise ValueError('duplicate/missing team-game')
    if not policy['cup_final']:
        return regular,{'season':season,'version':'pre-cup-2022-23','groups':[],'base_games':1230,'raw_games':1230,
                        'removed_final':None,'unknown_window_games':0,'regular_games':1230,'regular_team_games':82}
    start,end=[f'{season-1}-{md}' for md in policy['window']]
    base=regular[~regular.date.between(start,end)]
    if len(base)!=2400 or not base.groupby('team').size().eq(80).all():
        raise ValueError('historical Cup base calendar must be80/team')
    group=regular[regular.date.isin([f'{season-1}-{md}' for md in policy['group_dates']])]
    if group.game_id.nunique()!=60:raise ValueError('exactly60 historical Group Play games required')
    groups=connected_groups(group)
    # This is an outcome-blind structural join: source dates and fixture IDs only.
    return regular,{'season':season,'version':f'cup-{season-1}-regular-v1','groups':groups,
        'group_game_ids':sorted(group.game_id.astype(str).unique()),'base_game_ids':sorted(base.game_id.astype(str).unique()),
        'base_games':1200,'raw_games':raw.game_id.nunique(),'removed_final':policy['cup_final'],
        'unknown_window_games':30,'regular_games':1230,'regular_team_games':82,'policy':policy,
        'group_inference':'Connected components of published Cup-night fixtures; every component checked as a five-team complete graph, four games and2home/2away per team. No scores used.'}


def main():
    pa.set_cpu_count(1)
    if WORK.exists() or REPORT.exists():raise FileExistsError('fresh immutable B2 audit namespace required')
    origins=read_json(ROOT/'analysis/experiments/20261124_chunk_b_successor_v4.json')['historical_pathway_panel']['origins']
    sources={};rows={};panels=[];WORK.mkdir(parents=True)
    for year in POLICIES:
        frame,meta=load(year);rows[str(year)]=meta
        file=WORK/f'{year}.parquet';frame.to_parquet(file,index=False)
        sources[str(file.relative_to(ROOT))]=sha256_file(file)
        raw=ROOT/f'data/raw/hoopr/player_box_{year}.parquet';sources[str(raw.relative_to(ROOT))]=sha256_file(raw)
        dates=sorted(day for day in origins if int(day[:4])+(day[5:7]>='07')==year)
        for day in dates:
            past=frame[frame.date.lt(day)];future=frame[frame.date.ge(day)]
            if len(past)+len(future)!=2460 or len(past.groupby('team'))!=30:
                raise ValueError('origin partition/cold-start team support failed')
            unresolved=bool(meta['removed_final'] and day<f'{year-1}-{POLICIES[year]["window"][0]}')
            if unresolved and POLICIES[year]['publication_before']>=day:
                raise ValueError('future group metadata publication')
            panels.append({'season':year,'origin':day,'past_games':past.game_id.nunique(),
                 'remaining_games':future.game_id.nunique(),'latest_past_date':str(past.date.max()),
                 'min_prior_games_per_team':int(past.groupby('team').size().min()),
                 'world_local_slots_required':30 if unresolved else 0,
                 'future_actual_cup_pairings_permitted':not unresolved,
                 'previous_season_available':year>2023,
                 'cold_start_policy':'No prior2021-22 table retained; common league-centred prior, no future or whole-season estimate' if year==2023 else 'Only completed prior season and current games before origin'})
        print(f'{year}:1230 regular games/82team; Cup final removed={meta["removed_final"]};4 origins audited',flush=True)
    if len(panels)!=16 or {x['origin'] for x in panels}!=set(origins):raise ValueError('all16 frozen origins required')
    sources[str(Path(__file__).relative_to(ROOT))]=sha256_file(Path(__file__))
    write_json(REPORT,{'kind':'B2 historical calendar/source audit; no candidate fitting or scoring',
        'created_at':datetime.now(timezone.utc).isoformat(),'seasons':rows,'origins':panels,
        'diagnosis':{'legacy_extra_regular_finals':3,'legacy_83_game_teams':6,
            'legacy_future_cup_pairing_leak_origins':3,
            'production_2026_guard':'competitions.prepare explicitly rejects non2026-27 calendars; do not reuse its current groups, dates or prior-season records historically.'},
        'required_repair':'Before November Cup forecasts remove all30 unresolved regular slots and draw bracket/fillers within each world under its own historical policy; December25/February/March assignments are already known.',
        'limits':['As-played regular fixture dates lack original revision timestamps: conditional schedule evaluation, not certified as-published historical forecasts.',
                  'No historical postseason/title calibration claim. Neutral semifinals precede2026;2023 Cup ties include OT whereas2024/25 exclude OT.',
                  'Filler draw matching is an explicit sensitivity assumption where unpublished; never use later realised opponents in November.',
                  'Early2022 prior season unavailable; retain all four origins with a frozen common neutral prior.',
                  'Dated future absence support unestablished; retain no-hazard fallback.'],
        'source_sha256':sources,'candidate_outcomes_opened':False,'protected_scoring':False,'production_changed':False},pretty=True)


if __name__=='__main__':main()
