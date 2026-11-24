"""Five real positive-mass saved worlds, with immutable original chunk identities."""
from fractions import Fraction
from pathlib import Path
import numpy as np
from basketball_common import read_json,sha256_file
from scripts.world_mass import WorldMass,branch_masses

VECTOR_STATS=('pts','oreb','dreb','ast','stl','blk','tov','fg3m','fga','fta')

def select(folder):
    folder=Path(folder)
    plan=read_json(folder/'work-plan.json');provenance=read_json(folder/'provenance.json')
    if sha256_file(folder/'inputs.pkl')!=plan['provenance']['replay_input_sha256']:raise ValueError('replay inputs changed')
    blocks=[];player_ids=None;side=None
    for batch in sorted(plan['batches'],key=lambda b:b['branch_id']):
        mass=Fraction(*map(int,batch['weight']))
        if mass<0:raise ValueError('negative branch mass')
        if not mass:continue
        # Snapshot-owned complete captures remain authoritative even when work-plan paths refer to the original run root.
        original=Path(batch['capture'])
        path=folder/'branches'/original.name if batch['branch_id']!='unconditional' else folder/'capture.npz'
        receipt=read_json(path.with_suffix('.json'))
        if sha256_file(path)!=receipt['capture_sha256']:raise ValueError('saved branch changed')
        with np.load(path,allow_pickle=False) as z:
            ids=z['player_ids'].tolist();s=z['side'];points=z['team_points'].sum(2)
            if player_ids is None:player_ids,side=ids,s.copy()
            elif ids!=player_ids or not np.array_equal(side,s):raise ValueError('branch roster order differs')
            stats={k:z['box_'+k].sum(2,dtype=np.int64) for k in VECTOR_STATS}
            fantasy=10*stats['pts']+12*(stats['oreb']+stats['dreb'])+15*stats['ast']+30*(stats['stl']+stats['blk'])-10*stats['tov']
            vectors=np.column_stack([stats[k][:,s==team].sum(1) for team in (0,1) for k in VECTOR_STATS]+[z['possessions'][:,i] for i in (0,1)]).astype(float)
            own_fantasy=np.column_stack([fantasy[:,s==team].max(1) for team in (0,1)])
            n=len(points)
        if n!=batch['worlds']:raise ValueError('branch size differs')
        blocks.append({'batch':batch,'path':path,'source_hash':sha256_file(path),'mass':mass,'points':points,'fantasy':own_fantasy,'vectors':vectors})
    if sum((b['mass'] for b in blocks),Fraction())!=1:raise ValueError('positive branch mass does not sum to1')
    weights=branch_masses([len(b['points']) for b in blocks],[b['mass'] for b in blocks])
    mass=WorldMass(len(weights),weights)
    vector=np.concatenate([b['vectors'] for b in blocks]);mean=mass.mean(vector)
    variance=mass.mean((vector-mean)**2);supported=variance>0
    distance=np.square((vector[:,supported]-mean[supported])/np.sqrt(variance[supported])).sum(1)
    points=np.concatenate([b['points'] for b in blocks]);fantasy=np.concatenate([b['fantasy'] for b in blocks])
    selectors=[('home_margin','Largest home margin',int(np.argmax(points[:,0]-points[:,1]))),
               ('away_margin','Largest away margin',int(np.argmax(points[:,1]-points[:,0]))),
               ('home_fantasy','Largest individual home fantasy score',int(np.argmax(fantasy[:,0]))),
               ('away_fantasy','Largest individual away fantasy score',int(np.argmax(fantasy[:,1]))),
               ('representative','Representative across team scoring, possessions and boxes',int(np.argmin(distance)))]
    examples=[]
    for key,label,global_index in selectors:
        offset=0
        for b in blocks:
            if global_index<offset+len(b['points']):break
            offset+=len(b['points'])
        index=global_index-offset;batch=b['batch'];start=index//batch['chunk_worlds']*batch['chunk_worlds'];stop=min(start+batch['chunk_worlds'],batch['worlds'])
        atom=b['mass']/len(b['points'])
        examples.append({'key':key,'label':label,'branch_id':batch['branch_id'],'choices':{str(pid):bool(plays) for team,pid,plays in batch['assignments']},
             'world_index':index,'global_index':global_index,'chunk_start':start,'chunk_stop':stop,'within_chunk':index-start,
             'branch_mass':[str(b['mass'].numerator),str(b['mass'].denominator)],'world_mass':[str(atom.numerator),str(atom.denominator)],
             'capture':str(b['path']),'capture_sha256':b['source_hash'],'batch':batch,
             'selection_definition':'Maximum own final margin; or maximum individual fantasy (PTS+1.2REB+1.5AST+3STL+3BLK−TOV); or minimum squared standardised distance to exact weighted mean of both teams’ ten box totals and possessions. Zero-variance dimensions excluded; ties use sorted branch ID, then original world index.'})
    return {'source_id':provenance['source_id'],'game_id':plan['batches'][0]['game'],'examples':examples,
            'player_ids':player_ids,'side':side.tolist(),'normalisation':{'statistics':[f'{side}_{stat}' for side in ['home','away'] for stat in VECTOR_STATS]+['home_possessions','away_possessions'],'mean':mean.tolist(),'variance':variance.tolist()},
            'work_plan_sha256':sha256_file(folder/'work-plan.json'),'input_sha256':sha256_file(folder/'inputs.pkl')}


def replay_chunk(eng,folder,selection,branch_id,start,stop,output):
    """Replay the entire original chunk; save only selected records after every original array agrees."""
    import pickle,time
    from scripts import a1_lineup_branches,lineup_forecast,projection,shot_zones
    from scripts.world_detail import WorldDetail
    from basketball_common import write_json
    folder,output=Path(folder),Path(output)
    chosen=[e for e in selection['examples'] if (e['branch_id'],e['chunk_start'],e['chunk_stop'])==(branch_id,start,stop)]
    plan=read_json(folder/'work-plan.json')
    batch=next(b for b in plan['batches'] if b['branch_id']==branch_id)
    original=Path(batch['capture']);source=folder/'branches'/original.name if branch_id!='unconditional' else folder/'capture.npz'
    source_meta=read_json(source.with_suffix('.json'));source_hash=sha256_file(source)
    if source_hash!=source_meta['capture_sha256'] or sha256_file(folder/'inputs.pkl')!=selection['input_sha256']:raise ValueError('original replay source changed')
    if start<0 or stop>batch['worlds'] or stop<=start or start%batch['chunk_worlds'] or stop!=min(start+batch['chunk_worlds'],batch['worlds']):raise ValueError('not an original full canonical chunk')
    signature={'source_id':selection['source_id'],'capture_sha256':source_hash,'input_sha256':selection['input_sha256'],
               'branch_id':branch_id,'start':start,'stop':stop,'selected_worlds':sorted({e['within_chunk'] for e in chosen})}
    if output.exists():
        receipt=read_json(output.with_suffix('.receipt.json'))
        if (receipt['signature']!=signature or sha256_file(output)!=receipt['sha256']
            or sha256_file(Path(receipt['zone_output']))!=receipt['zone_sha256']):raise ValueError('completed replay changed')
        return receipt
    if output.with_suffix('.receipt.json').exists():raise ValueError('orphan replay receipt')
    began=time.monotonic()
    with (folder/'inputs.pkl').open('rb') as stream:saved=pickle.load(stream)
    effective=lambda r:{k:v for k,v in r.items() if k!='world_details'}
    if effective(eng.runtime)!=effective(saved['runtime']):raise ValueError('replay runtime differs from original recipe')
    # Data/models must be exactly the original fits; source code has only the separately audited read-only observer changes.
    root=Path(__file__).resolve().parents[1]
    sources=read_json(folder/'work-plan.json')['provenance']['sources']
    for name,digest in sources.items():
        if name.startswith('data/models/') and sha256_file(root/name)!=digest:raise ValueError('original fitted replay artifact changed')
    g=saved['game'];eng.m.median=saved['median']
    if batch['assignments']:g=a1_lineup_branches.prepare_branch(g,[tuple(a) for a in batch['assignments']])
    seed=projection.seed_for('world-chunk-v1',int(batch['seed']),start,stop)
    detail=WorldDetail(signature['selected_worlds']);previous=getattr(eng,'world_observer',None);eng.world_observer=detail
    try:record=lineup_forecast.simulate(eng,g,stop-start,seed)
    finally:eng.world_observer=previous
    raw=record['raw']
    with np.load(source,allow_pickle=False) as expected:
        if not set(expected.files).issubset(raw) or set(raw)-set(expected.files)-{'zone_fga','zone_fgm'}:raise ValueError('original replay raw fields differ')
        for key in expected.files:
            value=expected[key] if key in ('player_ids','side') else expected[key][start:stop]
            if not np.array_equal(raw[key],value):raise ValueError(f'original full-chunk raw parity differs:{key}')
    shot_zones.validate(raw)
    people=[{'id':str(p['id']),'name':p.get('name') or str(p['id']),'side':side}
            for side,s in enumerate(g.sides) for p in g.players[s]]
    lookup={pid:i for i,pid in enumerate(g.ids)}
    worlds={}
    for w in signature['selected_worlds']:
        for event in detail.events[w]:
            for five in event['lineups']+event['lineups_after']:
                if not all(raw['available'][w,lookup[pid]] for pid in five):raise ValueError('replay uses unavailable player')
        worlds[str(w)]={'events':detail.events[w],'audit':detail.audit[w],
                       'final_score':eng.last.score[w].astype(int).tolist(),
                       'final_box':{str(pid):{**{stat:int(values[w,i].sum()) for stat,values in eng.last.box.items()},
                                              'min':float(eng.last.minutes[w,i].sum())} for i,pid in enumerate(g.ids)}}
    zone_output=output.with_suffix('.zones.npz')
    if zone_output.exists():raise FileExistsError('orphan zone output')
    output.parent.mkdir(parents=True,exist_ok=True)
    np.savez_compressed(zone_output,zone_fga=raw['zone_fga'],zone_fgm=raw['zone_fgm'],player_ids=raw['player_ids'],side=raw['side'])
    result={'schema':'visible-worlds-v1','signature':signature,'game_id':selection['game_id'],'players':people,'worlds':worlds,
            'raw_arrays_exact':True,'zone_arrays_valid':True,'seed':str(seed),'seconds':time.monotonic()-began}
    output.parent.mkdir(parents=True,exist_ok=True);write_json(output,result,pretty=False)
    receipt={'signature':signature,'output':str(output),'sha256':sha256_file(output),'raw_arrays_exact':True,
             'worlds_replayed':stop-start,'worlds_recorded':len(worlds),'seconds':result['seconds'],
             'zone_output':str(zone_output),'zone_sha256':sha256_file(zone_output)}
    write_json(output.with_suffix('.receipt.json'),receipt,pretty=True)
    return receipt


def finish_replays(selection,chunk_outputs,output,model,runtime):
    """Join reconciled stored segments; no simulation or source reconstruction."""
    import gzip
    from basketball_common import packed,write_json
    output=Path(output)
    if output.exists():raise FileExistsError(output)
    by_chunk={};people=None
    for path in chunk_outputs:
        path=Path(path);receipt=read_json(path.with_suffix('.receipt.json'))
        if sha256_file(path)!=receipt['sha256'] or not receipt['raw_arrays_exact']:raise ValueError('replay chunk metadata changed')
        data=read_json(path);sig=data['signature']
        if sig['source_id']!=selection['source_id']:raise ValueError('replay source identity differs')
        key=(sig['branch_id'],sig['start'],sig['stop'])
        if key in by_chunk:raise ValueError('duplicate replay chunk')
        if people is not None and people!=data['players']:raise ValueError('replay player identities differ')
        people=data['players'];by_chunk[key]=data
    examples=[]
    for selected in selection['examples']:
        key=(selected['branch_id'],selected['chunk_start'],selected['chunk_stop'])
        data=by_chunk[key];world=data['worlds'][str(selected['within_chunk'])]
        examples.append({k:v for k,v in selected.items() if k not in ('batch','capture','capture_sha256','global_index')})
        examples[-1].update(world)
    payload={'schema':'visible-worlds-v1','source_id':selection['source_id'],'game_id':selection['game_id'],'model':model,'runtime':runtime,
             'players':people,'examples':examples,'spatial_precision':'Generated events and five pooled model zones; no tracking coordinates, player positions, pass sequences or trajectories.',
             'source':{'work_plan_sha256':selection['work_plan_sha256'],'input_sha256':selection['input_sha256']}}
    size=len(gzip.compress(packed(payload).encode(),compresslevel=6))
    if size>2097152:raise ValueError('replay exceeds frozen2MiB gzip/game limit; inspect scope, no truncation')
    payload['gzip_bytes']=size;write_json(output,payload,pretty=False)
    return {'examples':len(examples),'unique_chunks':len(by_chunk),'gzip_bytes':size,'sha256':sha256_file(output)}


def collect_zones(folder,selection,chunk_outputs,output):
    """Build full exact zone worlds/cases from all original chunks, preserving the original branch order."""
    from scripts import shot_zones
    from scripts.world_mass import branch_masses
    from basketball_common import write_json
    folder,output=Path(folder),Path(output)
    if output.exists():raise FileExistsError(output)
    by_chunk={}
    for path in chunk_outputs:
        path=Path(path);receipt=read_json(path.with_suffix('.receipt.json'));sig=receipt['signature']
        if sha256_file(Path(receipt['zone_output']))!=receipt['zone_sha256']:raise ValueError('zone chunk changed')
        key=(sig['branch_id'],sig['start'],sig['stop'])
        if key in by_chunk:raise ValueError('duplicate zone chunk')
        by_chunk[key]=receipt
    plan=read_json(folder/'work-plan.json');attempts=[];makes=[];spans=[];offset=0;ids=None;side=None
    for batch in plan['batches']:
        branch_a=[];branch_m=[]
        for start in range(0,batch['worlds'],batch['chunk_worlds']):
            stop=min(start+batch['chunk_worlds'],batch['worlds']);receipt=by_chunk.pop((batch['branch_id'],start,stop))
            with np.load(receipt['zone_output'],allow_pickle=False) as z:
                if ids is None:ids=z['player_ids'].copy();side=z['side'].copy()
                if not np.array_equal(ids,z['player_ids']) or not np.array_equal(side,z['side']):raise ValueError('zone chunk roster differs')
                branch_a.append(z['zone_fga']);branch_m.append(z['zone_fgm'])
        a=np.concatenate(branch_a);m=np.concatenate(branch_m)
        source=folder/'branches'/Path(batch['capture']).name if batch['branch_id']!='unconditional' else folder/'capture.npz'
        with np.load(source,allow_pickle=False) as z:
            shot_zones.validate({'zone_fga':a,'zone_fgm':m,'minutes':z['minutes'],
                                 **{k:z[k] for k in ('box_fga','box_fgm','box_fg3a','box_fg3m')}})
        attempts.append(a);makes.append(m);spans.append((batch,offset,offset+len(a)));offset+=len(a)
    if by_chunk:raise ValueError('unexpected zone chunks')
    a=np.concatenate(attempts);m=np.concatenate(makes)
    weights=branch_masses([len(x) for x in attempts],[Fraction(*map(int,b['weight'])) for b in plan['batches']])
    output.parent.mkdir(parents=True,exist_ok=True);np.savez_compressed(output,zone_schema=np.array(1,np.uint8),zone_fga=a,zone_fgm=m,player_ids=ids,side=side,weights=weights)
    choices={k:v['choices'] for k,v in read_json(folder/'worlds.json')['cases'].items()} if plan['selected'] else {'':{}}
    cases={}
    for key,condition in choices.items():
        mask=np.zeros(offset,bool)
        for batch,lo,hi in spans:
            assignments={str(pid):bool(plays) for team,pid,plays in batch['assignments']}
            if all(assignments.get(pid)==value for pid,value in condition.items()):mask[lo:hi]=True
        if not mask.any():raise ValueError('empty stored zone case')
        cases[key]={'choices':condition,**shot_zones.summaries_arrays(a[mask],m[mask],ids,side,weights[mask])}
    expected=next(c for c in cases.values() if not c['choices'])
    payload={'schema':'shot-zones-v1','source_id':selection['source_id'],'game_id':selection['game_id'],'expected':expected,'cases':cases,
             'definition':'Exact saved-world zone attempts and makes; projected counts are weighted means, FG% uses weighted makes/attempts.',
             'spatial_precision':'Five pooled r3 model regions; left/right pooled. These are generated zone counts, not exact shot coordinates.',
             'missingness':'Zero attempts leave FG% undefined. Legacy snapshots without full zone capture remain unavailable.',
             'zone_worlds':{'path':str(output),'sha256':sha256_file(output),'worlds':offset,'probability_mass':int(weights.sum())}}
    write_json(output.with_suffix('.json'),payload,pretty=False)
    return payload
