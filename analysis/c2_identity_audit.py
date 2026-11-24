#!/usr/bin/env python3
"""Resolve saved C2 decisions to immutable raw-file hashes and original rows."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
import pyarrow as pa
from basketball_common import NBA_TEAM_IDS,read_json,write_json,sha256_file
from scripts import nodes,court_zones as cz
from analysis.c2_node_screen import source_rows,WORK,PLAN


def main():
    pa.set_cpu_count(1)
    output=ROOT/'analysis/experiments/20261124_c2_identity_audit_v1.json'
    mapping=WORK/'source_identity.parquet'
    if output.exists() or mapping.exists():raise FileExistsError('identity audit is immutable')
    parts=[];hashes={}
    for path in nodes.segment_files():
        raw=pd.read_parquet(path,columns=['game_id','game_ok','offense','defense'])
        digest=sha256_file(path);hashes[str(path.relative_to(ROOT))]=digest
        keep=raw.game_ok & raw.offense.astype(str).isin(NBA_TEAM_IDS) & raw.defense.astype(str).isin(NBA_TEAM_IDS)
        parts.append(pd.DataFrame({'game_id':raw.loc[keep,'game_id'].to_numpy(),
                                  'source_row':np.flatnonzero(keep),'source_sha256':digest}))
    identity=pd.concat(parts,ignore_index=True);identity.index.name='source_seg_id'
    assert not identity.duplicated(['source_sha256','source_row']).any()
    identity.reset_index().to_parquet(mapping,index=False)
    checks={}
    direct=['period','start_clock','sec_left_game','margin','fouls_def','fouls_off','off_home','season_type','season','start_code','shot_time','clutch','distance','lateral']
    for name in ['what','location','shot_result']:
        rows,old_y=source_rows(name)
        np.testing.assert_array_equal(identity.iloc[rows.seg_id].game_id,rows.game_id)
        for fold in ['F1','F2','F3']:
            pre=ROOT/f'data/derived/variants/a1_scheduled_{fold}_20261122_v3/features/pregame.parquet'
            data=next(nodes.datasets([name],pregame=pre));compared=[]
            for col in direct:
                if col in data['X']:
                    np.testing.assert_array_equal(data['X'][col].to_numpy(),rows[col].to_numpy(np.float32));compared.append(col)
            # Actor identity check through dated profile values, independently of cache row metadata.
            profiles=pd.read_parquet(pre).set_index(['game_id','player'])
            actor_idx=pd.MultiIndex.from_arrays([rows.game_id,rows.actor])
            actor=profiles.reindex(actor_idx)
            on=rows[[f'off_{i}' for i in range(1,6)]].eq(rows.actor,axis=0).any(axis=1).to_numpy()
            for col in ['usage','fg_rim','mix_above3','min_avg']:
                key='actor_'+col
                if key in data['X']:
                    expected=actor[col].to_numpy(np.float32);expected[~on]=np.nan
                    np.testing.assert_array_equal(data['X'][key].to_numpy(),expected);compared.append(key)
            for variant in ['control','zone','distance','defence']:
                folder=WORK/f'{fold}_{name}_{variant}_s7';receipt=read_json(folder/'receipt.json')
                if receipt['source_sha256']!=hashes:raise ValueError('source hashes differ')
                saved=np.load(folder/'validation.npz',allow_pickle=False)
                row_by_id=rows.set_index('seg_id').loc[saved['source_seg_id']]
                if name=='location' and variant!='control':
                    target=cz.encode(receipt['layout'],row_by_id.x,row_by_id.y,row_by_id.value)
                else:target=pd.Series(old_y,index=rows.seg_id).loc[saved['source_seg_id']].to_numpy()
                np.testing.assert_array_equal(saved['target'],target)
                key=f'{fold}_{name}_{variant}'
                checks[key]={'rows':len(target),'unique_source_decisions':len(np.unique(saved['source_seg_id'])),'independent_context_profile_columns':compared,'receipt_sha256':sha256_file(folder/'receipt.json')}
                assert checks[key]['unique_source_decisions']==len(target)
        print(name,'immutable source keys and cached context/profile values exact',flush=True)
    write_json(output,{'kind':'independent original-row/source-hash and context/actor-profile audit; no accuracy scoring',
                       'recipe_sha256':sha256_file(PLAN),'source_sha256':hashes,'mapping_sha256':sha256_file(mapping),
                       'mapping_rows':len(identity),'comparisons':checks},pretty=True)

if __name__=='__main__':main()
