#!/usr/bin/env python3
"""Independently compare fixed derived zones with the retained native joins."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
from basketball_common import write_json,sha256_file
from scripts import court_zones as z


def main():
    paths=sorted((ROOT/'data/derived/experiments/c2_source_audit_v1').glob('*.parquet'))
    if len(paths)!=3:raise ValueError('exact three-game source audit required')
    rows=pd.concat([pd.read_parquet(p) for p in paths],ignore_index=True)
    truth=z.native_codes(rows.SHOT_ZONE_BASIC,rows.SHOT_ZONE_AREA,rows.SHOT_ZONE_RANGE)
    value=np.where(rows.SHOT_TYPE.eq('3PT Field Goal'),3,2)
    native=z.derive(25+rows.LOC_X.to_numpy()/10,rows.LOC_Y.to_numpy()/10,value)
    rounded=z.derive(rows.espn_x,rows.espn_y,rows.espn_value)
    mismatch=rows.loc[native!=truth,['GAME_ID','GAME_EVENT_ID','SHOT_TYPE','SHOT_ZONE_BASIC','SHOT_ZONE_AREA','SHOT_ZONE_RANGE','LOC_X','LOC_Y']]
    output=ROOT/'analysis/experiments/20261124_c2_geometry_audit_v2.json'
    cases=ROOT/'data/derived/experiments/c2_geometry_cases_v2.json'
    if output.exists() or cases.exists():raise FileExistsError('fresh aggregate/case namespace required')
    write_json(cases,mismatch.to_dict('records'),pretty=True)
    write_json(output,{'kind':'native-vs-derived input audit; no candidate prediction scoring','pairs':len(rows),'native_coordinate_fine_agreement':int((native==truth).sum()),'rounded_coordinate_fine_agreement':int((rounded==truth).sum()),'native_cells_observed':np.unique(truth).tolist(),'unknown_rounded_pairs':int((rounded>=20).sum()),'native_disagreement_count':len(mismatch),'native_disagreement_cases':str(cases.relative_to(ROOT)),'native_disagreement_cases_sha256':sha256_file(cases),'source_sha256':{str(p.relative_to(ROOT)):sha256_file(p) for p in paths},'mapper_sha256':sha256_file(ROOT/'scripts/court_zones.py'),'limits':['Three early-season games; not a general accuracy estimate.','ESPN rounding can cross boundaries; retain derived provenance.','Native Mid-Range label conflicts with official3PT value in one joined event; no forced relabelling.','Long frontcourt40ft split is explicitly derived, without an independently observed native AboveTheBreak/BackCourt example.']},pretty=True)
    print(output.relative_to(ROOT))

if __name__=='__main__':main()
