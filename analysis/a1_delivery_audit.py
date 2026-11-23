#!/usr/bin/env python3
"""Independent saved-world/Expected accounting, using stored branches and direct integer counts."""
import argparse
from fractions import Fraction
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from basketball_common import read_json, sha256_file, write_json

SLICES = {'q1': [0], 'q2': [1], 'q3': [2], 'q4': [3], 'h1': [0, 1], 'h2': [2, 3], 'fg': [0, 1, 2, 3, 4]}


def histogram(values, weights, saved):
    values = np.asarray(values, np.int64)
    counts = np.zeros(len(saved['hist']), np.int64)
    np.add.at(counts, values - saved['min'], weights)
    assert counts.tolist() == saved['hist'], 'histogram differs from direct integer counts'
    assert abs(float(np.dot(values, weights) / weights.sum()) - saved['mean']) <= .000500001


def audit(folder):
    folder = Path(folder)
    branched = (folder / 'worlds.json').exists()
    if branched:
        payload = read_json(folder / 'worlds.json')
    else:
        summary = read_json(folder / 'game.json')
        payload = {'game': summary['game_id'], 'selected_players': [],
                   'branches': [{'capture_sha256': sha256_file(folder / 'capture.npz'), 'assignments': [],
                                 'weight': {'numerator': '1', 'denominator': '1'}}],
                   'cases': {'': {'choices': {}, 'sim': summary}}}
    records = []
    for i, branch in enumerate(payload['branches']):
        path = folder / 'branches' / f'branch-{i:03d}.npz' if branched else folder / 'capture.npz'
        assert sha256_file(path) == branch['capture_sha256']
        with np.load(path, allow_pickle=False) as z:
            raw = {k: z[k] for k in z.files}
        p = Fraction(1)
        selected = {x['player_id']: x for x in payload['selected_players']}
        for team, pid, available in branch['assignments']:
            player = selected[pid]
            assert team == player['team_id']
            q = Fraction(str(player['probability']))
            p *= q if available else 1-q
            assert np.equal(raw['available'][:, list(raw['player_ids']).index(pid)], available).all()
        assert p == Fraction(int(branch['weight']['numerator']), int(branch['weight']['denominator']))
        for side in (0, 1):
            mask = raw['side'] == side
            assert np.array_equal(raw['box_pts'][:, mask].sum(1), raw['team_points'][:, side])
            expected = np.column_stack([np.full(len(raw['minutes']), 60.)]*4 + [25.*(raw['final_period']-4)])
            assert np.allclose(raw['minutes'][:, mask].sum(1), expected, atol=1e-8, rtol=0)
        assert not raw['minutes'][~raw['available']].any()
        records.append((branch, raw))
    with np.load(folder / 'players.npz', allow_pickle=False) as z:
        weights = z['weights'] if 'weights' in z else np.ones(len(z['lines']), np.int64)
    cuts = np.r_[0, np.cumsum([len(raw['minutes']) for _,raw in records])]
    checked = 0
    for case in payload['cases'].values():
        keep = [i for i,(branch,_) in enumerate(records) if all(dict((pid,val) for _,pid,val in branch['assignments']).get(pid)==value for pid,value in case['choices'].items())]
        selected_weights = np.concatenate([weights[cuts[i]:cuts[i+1]] for i in keep])
        points = np.concatenate([records[i][1]['team_points'] for i in keep])
        sim = case['sim']
        assert sim['sims'] == len(selected_weights) and sim.get('probability_mass', sim['sims']) == int(selected_weights.sum())
        for period, columns in SLICES.items():
            home,away = points[:,0,columns].sum(1),points[:,1,columns].sum(1)
            for key,values in [('total',home+away),('margin',home-away)]:
                histogram(values,selected_weights,sim['periods'][period][key]);checked+=1
            for side,name in enumerate(('home','away')):
                for player in sim[name]['players']:
                    if not player.get('periods'):continue
                    idx=list(records[0][1]['player_ids']).index(player['id'])
                    for stat in ('pts','ast','fg3m','oreb','dreb','stl','blk','tov','fgm','fga','fta','fg3a','ftm','min'):
                        saved=player['periods'][period]['stats'].get(stat)
                        if saved is None:continue
                        values=np.concatenate([records[i][1]['minutes' if stat=='min' else 'box_'+stat][:,idx,columns].sum(1) for i in keep])
                        if stat=='min':values=np.rint(values)
                        histogram(values,selected_weights,saved);checked+=1
    return {'game': payload['game'], 'branches': len(records), 'worlds': len(weights), 'cases': len(payload['cases']), 'independent_histograms': checked, 'status':'pass'}


def audit_view_rates(folder, views_root):
    """Independent displayed-rate/count accounting against retained merged raw worlds."""
    folder, views_root = Path(folder), Path(views_root)
    gid = folder.name
    game = read_json(views_root / 'api' / 'game' / f'{gid}.json')
    source = read_json(views_root / 'api' / 'game' / gid / 'worlds.json')
    cases = list(source['cases'].values()) if 'cases' in source else []
    cases.append({'choices': {}, 'sim': game['projection']['sim']})
    with np.load(folder / 'players.npz', allow_pickle=False) as z:
        lines, ids, sides = z['lines'].astype(float), list(map(str, z['ids'])), z['side']
        weights = z['weights'] if 'weights' in z else np.ones(len(lines), np.int64)
    stats = ('min','pts','reb','ast','fg3m','stl','blk','tov','fgm','fga','fg3a','fta','oreb','dreb','ftm')
    branches = source.get('branches', [{'assignments': [], 'worlds': {'worlds': len(lines)}}])
    cuts = np.r_[0, np.cumsum([b['worlds']['worlds'] for b in branches])]
    assert cuts[-1] == len(lines)
    def rates(x, other=None):
        result = {'fgpct': (x['fgm'], x['fga'],100), 'fg3pct':(x['fg3m'],x['fg3a'],100),
                  'ftpct':(x['ftm'],x['fta'],100), 'efg':(x['fgm']+.5*x['fg3m'],x['fga'],100),
                  'ts':(x['pts'],2*(x['fga']+.44*x['fta']),100),
                  'two':(x['fgm']-x['fg3m'],x['fga']-x['fg3a'],100),
                  'threeShare':(x['fg3a'],x['fga'],100), 'ftRate':(x['fta'],x['fga'],100),
                  'astTov':(x['ast'],x['tov'],1)}
        if other is not None:
            own=x['fga']-x['oreb']+x['tov']+.44*x['fta']
            opp=other['fga']-other['oreb']+other['tov']+.44*other['fta']
            offense=np.divide(x['pts'],own,out=np.full(len(own),np.nan),where=own>0)
            defense=np.divide(other['pts'],opp,out=np.full(len(opp),np.nan),where=opp>0)
            result.update(poss=(own,np.ones(len(own)),1),ortg=(x['pts'],own,100),drtg=(other['pts'],opp,100),
                          net=(offense-defense,np.ones(len(own)),100),oreb=(x['oreb'],x['oreb']+other['dreb'],100),
                          dreb=(x['dreb'],x['dreb']+other['oreb'],100),assist=(x['ast'],x['fgm'],100),
                          turnover=(x['tov'],own,100),steals=(x['stl'],opp,100))
        return result
    checked=0
    for case in cases:
        mask=np.zeros(len(lines),bool)
        for i,b in enumerate(branches):
            assignment={str(pid):value for _,pid,value in b['assignments']}
            if all(assignment.get(pid)==value for pid,value in case['choices'].items()): mask[cuts[i]:cuts[i+1]]=True
        selected, w=lines[mask],weights[mask]
        sim=case['sim']; assert sim['sims']==len(w)
        assert sim['availability_policy']=='report-bands-v1'
        boxes=[{k:selected[:,sides==side,j].sum(1) for j,k in enumerate(stats)} for side in (0,1)]
        targets=[]
        for side,name in enumerate(('home','away')):
            targets.append((sim[name]['advanced'],rates(boxes[side],boxes[1-side])))
            for player in sim[name]['players']:
                if not player.get('periods'): continue
                index=ids.index(str(player['id']))
                targets.append((player['periods']['fg']['advanced'],rates({k:selected[:,index,j] for j,k in enumerate(stats)})))
                assert player['availability'] in (0,.25,.5,.75,1)
        for summaries, definitions in targets:
            for key,(numerator,denominator,scale) in definitions.items():
                d=summaries[key]; good=(denominator>0)&np.isfinite(numerator)
                assert (d['worlds'],d['defined_worlds'],d['total'],d['defined']) == (len(w),int(good.sum()),int(w.sum()),int(w[good].sum()))
                if good.any():
                    # Quantise the per-world ratio, then apply its display units. Reordering these
                    # operations moves exact half-bin cases by one ULP (e.g.23/40*100).
                    values=(numerator[good]/denominator[good])*scale; weighted=w[good]
                    assert abs(d['exact_mean']-float((values*weighted).sum()/weighted.sum()))<=.000500001
                    bins=np.floor(values*d['scale']+.5).astype(int)
                    direct=np.zeros(len(d['hist']),np.int64);np.add.at(direct,bins-d['min'],weighted)
                    assert direct.tolist()==d['hist'], (gid,case['choices'],key,np.flatnonzero(direct!=np.asarray(d['hist'])).tolist(), [(int(i+d['min']),int(direct[i]),d['hist'][i]) for i in np.flatnonzero(direct!=np.asarray(d['hist']))[:8]])
                    order=np.argsort(values); ordered=values[order]; cumulative=np.cumsum(weighted[order])
                    expected=[float(ordered[cumulative>=q*weighted.sum()][0]) for q in (.1,.25,.5,.75,.9)]
                    assert np.allclose(d['exact_q'],expected,atol=.000500001,rtol=0)
                checked+=1
    return {'game':gid,'cases_including_game_view':len(cases),'rate_distributions_checked':checked,'status':'pass'}


if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('folder',type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args()
    result=audit(a.folder);write_json(a.output,result,pretty=True);print(result,flush=True)
