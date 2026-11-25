"""Independently account stored rotation summaries against every retained raw world/case."""
import sys,math
from pathlib import Path
from fractions import Fraction
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
from basketball_common import read_json,write_json,sha256_file

def audit(folder):
 provenance=read_json(folder/'provenance.json');identity=provenance['source_id'];summary=read_json(folder/'game.json')
 payload=read_json(folder/'worlds.json') if provenance['selected'] else None
 cases=payload['cases'] if payload else {'':{'choices':{},'sim':summary}}
 records=payload['branches'] if payload else [{'assignments':[],'weight':{'numerator':'1','denominator':'1'}}]
 arrays=[];fractions=[];counts=[];sources={}
 for i,record in enumerate(records):
  path=folder/f'branches/branch-{i:03d}.npz' if payload else folder/'capture.npz'
  with np.load(path,allow_pickle=False) as raw:
   p=raw['rotation_presence'];ids=raw['player_ids'];side=raw['side'];available=raw['available']
   assert p.dtype==np.uint8 and p.shape==(len(available),len(ids),48) and np.isin(p,[0,1]).all()
   assert not p[~available].any()
   for s in (0,1):assert np.all(p[:,side==s].sum(1)==5)
   arrays.append(p.sum(0,dtype=np.int64));counts.append(len(p))
  fractions.append(Fraction(int(record['weight']['numerator']),int(record['weight']['denominator']))/counts[-1]);sources[str(path.relative_to(ROOT))]=sha256_file(path)
 denominator=math.lcm(*(f.denominator for f in fractions));units=[int(f*denominator) for f in fractions]
 def compare(mapping,selected):
  n=sum(counts[i] for i in selected);mass=sum(counts[i]*units[i] for i in selected)
  expected=sum(arrays[i]*units[i] for i in selected)
  assert mapping['schema']=='rotation-midpoints-v1' and mapping['source_id']==identity
  assert mapping['seconds']==list(range(30,2880,60)) and mapping['worlds']==n and mapping['probability_mass']==mass
  for j,pid in enumerate(ids):
   value=mapping['players'][str(pid)];assert value['side']==int(side[j]);assert value['on_court_mass']==expected[j].tolist();assert value['probability']==(expected[j]/mass).tolist()
  for s in (0,1):assert (expected[side==s].sum(0)==5*mass).all()
 for case in cases.values():
  selected=[i for i,r in enumerate(records) if all({str(pid):value for team,pid,value in r['assignments']}.get(pid)==value for pid,value in case['choices'].items())]
  compare(case['sim']['rotation_map'],selected)
 compare(summary['rotation_map'],list(range(len(records))))
 game=read_json(ROOT/f'data/views/api/game/{folder.name}.json');assert game['projection']['sim']['rotation_map']==summary['rotation_map']
 return {'game':folder.name,'worlds':sum(counts),'cases':len(cases),'sample_cells':sum(counts)*len(ids)*48,'source_id':identity,'raw_sha256':sources,'all_counts_probabilities_and_fives_exact':True}
if __name__=='__main__':
 out=ROOT/'analysis/experiments/20261125_b3_rotation_audit_v1.json';assert not out.exists()
 day=read_json(ROOT/'data/views/api/meta.json')['latest'];rows=[audit(p.parent) for p in sorted((ROOT/f'data/snapshots/{day}/lineups').glob('*/provenance.json'))]
 assert rows
 write_json(out,{'kind':'All retained binary rotation worlds, independently summed by branch rational weights and selected cases','day':day,'games':rows,'worlds':sum(r['worlds'] for r in rows),'result':'pass'},pretty=True);print('All-world rotation accounting passed',len(rows),flush=True)
