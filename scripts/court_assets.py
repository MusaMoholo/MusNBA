"""Read saved, source-bound court/replay artifacts while building views; never used by serving."""
from pathlib import Path
import numpy as np
from basketball_common import ROOT,DERIVED,read_json,write_json,sha256_file
from scripts import shot_zones
CATALOGUE=DERIVED/'visible_worlds'

def source(snapshot,gid):
 folder=Path(snapshot)/'lineups'/str(gid);path=folder/'provenance.json'
 return (read_json(path)['source_id'],folder) if path.exists() else (None,folder)

def locate(snapshot,gid,suffix):
 identity,folder=source(snapshot,gid)
 if identity is None:return None,None
 direct=folder/('zones'+suffix if suffix in ('.npz','.json') else 'replay.json')
 canonical=CATALOGUE/(identity+('.court.json' if suffix=='.json' else '.zones.npz' if suffix=='.npz' else '.replay.json'))
 return identity,direct if direct.exists() else canonical if canonical.exists() else None

def enrich_players(snapshot,gid,players,stats):
 if 'zone_fga' in players:return players
 identity,path=locate(snapshot,gid,'.npz')
 if path is None:return players
 _,metadata=locate(snapshot,gid,'.json')
 if metadata is None or read_json(metadata).get('zone_worlds',{}).get('sha256')!=sha256_file(path):raise ValueError('stored zone artifact checksum differs')
 with np.load(path,allow_pickle=False) as z:
  if int(z['zone_schema'])!=1 or not np.array_equal(z['player_ids'],players['ids']) or not np.array_equal(z['side'],players['side']):raise ValueError('stored zone source roster differs')
  a,m=z['zone_fga'],z['zone_fgm'];weights=z['weights']
 if a.shape!=players['minutes'].shape+(5,) or m.shape!=a.shape or a.dtype!=np.uint16 or m.dtype!=np.uint16 or (m>a).any():raise ValueError('stored zone source dimensions differ')
 expected=players.get('weights',np.ones(len(a),np.int64))
 if not np.array_equal(weights,expected):raise ValueError('stored zone world masses differ')
 for stat,values in [('fga',a.sum((2,3))),('fgm',m.sum((2,3))),('fg3a',a[:,:,:,3:].sum((2,3))),('fg3m',m[:,:,:,3:].sum((2,3)))]:
  if stat not in stats or not np.array_equal(values,players['lines'][:,:,stats.index(stat)]):raise ValueError('stored zone world order/box differs')
 return {**players,'zone_schema':np.array(1,np.uint8),'zone_fga':a,'zone_fgm':m}

def enrich_branches(payload,players):
 if 'zone_fga' not in players:return
 offset=0
 for record in payload['branches']:
  raw=record['worlds'];end=offset+raw['worlds']
  raw.update(shot_zones.encode_arrays(players['zone_fga'][offset:end],players['zone_fgm'][offset:end]));offset=end
 if offset!=len(players['zone_fga']):raise ValueError('branch zone worlds do not cover source')

def build(snapshot,gid,api,game=None,players=None):
 descriptors={}
 for suffix,key,schema in [('.replay.json','replay','visible-worlds-v1'),('.json','court','shot-zones-v1')]:
  identity,path=locate(snapshot,gid,suffix)
  if path is None:continue
  payload=read_json(path)
  if payload.get('source_id')!=identity or str(payload.get('game_id'))!=str(gid) or payload.get('schema')!=schema:raise ValueError('stored exploration artifact source differs')
  payload={k:v for k,v in payload.items() if k!='zone_worlds'}
  if key=='court' and game is not None and players is not None:
   from scripts import court_observed
   payload['observed']=court_observed.build(game,players)
  write_json(Path(api)/'game'/str(gid)/(key+'.json'),payload)
  descriptors[key]={'schema':schema,'source_id':identity,'path':f'game/{gid}/{key}'}
 return descriptors

def register_capture(report):
 """Copy immutable verified enrichment into a source-ID catalogue; preserve existing artifacts."""
 CATALOGUE.mkdir(parents=True,exist_ok=True)
 for row in report['games']:
  court=read_json(ROOT/row['court']);identity=court['source_id']
  paths=[(ROOT/row['replay'],CATALOGUE/(identity+'.replay.json')),
         (ROOT/row['zone_worlds']['path'],CATALOGUE/(identity+'.zones.npz')),
         (ROOT/row['court'],CATALOGUE/(identity+'.court.json'))]
  for source_path,destination in paths:
   digest=sha256_file(source_path)
   declared=row.get('sha256') if destination.name.endswith('.replay.json') else row['zone_worlds'].get('sha256') if destination.name.endswith('.zones.npz') else None
   if declared is not None and digest!=declared:raise ValueError('capture report checksum differs')
   if destination.exists():
    if sha256_file(destination)!=digest:
     # The same verified arrays can be packaged from preview and final folders.
     # Preserve the original catalogue bytes; only that private locator may differ.
     if not destination.name.endswith('.court.json'):raise ValueError('immutable source enrichment already differs')
     prior=read_json(destination);current=read_json(source_path)
     for value in (prior,current):
      if 'zone_worlds' in value:value['zone_worlds'].pop('path',None)
     if prior!=current:raise ValueError('immutable source enrichment already differs')
   else:
    import shutil
    shutil.copyfile(source_path,destination)


def store_zones(folder,identity,raw,weights):
 """Write exact game/lineup summaries from the just-saved full zone arrays."""
 from scripts.world_mass import WorldMass
 folder=Path(folder)
 if not shot_zones.validate(raw):raise ValueError('zone-capable runtime omitted zone arrays')
 n=len(raw['minutes']);mass=WorldMass(n,weights)
 source=read_json(folder/'worlds.json') if (folder/'worlds.json').exists() else None
 conditions={key:case['choices'] for key,case in source['cases'].items()} if source else {'':{}}
 spans=[];offset=0
 if source:
  for branch in source['branches']:
   stop=offset+branch['worlds']['worlds'];spans.append(({str(pid):value for team,pid,value in branch['assignments']},offset,stop));offset=stop
  if offset!=n:raise ValueError('zone source branches differ')
 else:spans=[({},0,n)]
 cases={}
 for key,condition in conditions.items():
  mask=np.zeros(n,bool)
  for assignment,start,stop in spans:
   if all(assignment.get(pid)==value for pid,value in condition.items()):mask[start:stop]=True
  if not mask.any():raise ValueError('empty zone lineup case')
  cases[key]={'choices':condition,**shot_zones.summaries_arrays(raw['zone_fga'][mask],raw['zone_fgm'][mask],raw['player_ids'],raw['side'],None if weights is None else weights[mask])}
 expected=next(c for c in cases.values() if not c['choices'])
 game=read_json(folder/'game.json')
 payload={'schema':'shot-zones-v1','source_id':identity,'game_id':str(game['game_id']),'expected':expected,'cases':cases,
  'definition':'Exact saved-world zone counts; projected counts are weighted means, FG% uses weighted makes/attempts.',
  'spatial_precision':'Five pooled model regions, left/right pooled; generated zones, not exact coordinates.',
  'missingness':'Zero attempts leave FG% undefined. Legacy snapshots without full capture stay unavailable.',
  'zone_worlds':{'source':'players.npz','sha256':sha256_file(folder/'players.npz'),'worlds':n,'probability_mass':mass.total}}
 write_json(folder/'zones.json',payload,pretty=False)
