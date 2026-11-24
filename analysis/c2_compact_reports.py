#!/usr/bin/env python3
"""Keep rich arm records private; publish only aggregate evidence and hash links."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from basketball_common import read_json,write_json,sha256_file

FIELDS=('kind','manifest_sha256','game_ids','worlds','arms','reference_raw_parity','reference_reuse_enabled',
        'elapsed_seconds','fresh_arm_jobs','workers','production_changed')


def public_report(report,private_path,runner_copy):
    public={key:report[key] for key in FIELDS}
    public.update(schema='c2-engine-evidence-v2',private_report=str(private_path.relative_to(ROOT)),
                  private_report_sha256=sha256_file(private_path),prediction_runner=str(runner_copy.relative_to(ROOT)),
                  prediction_runner_sha256=sha256_file(runner_copy))
    games={gid:{} for gid in report['game_ids']}
    for item in report['receipts']:
        gid,arm=item['game'],item['arm'];reused=item.get('reused')
        selector='entry'
        if reused and reused.get('receipt'):
            path=ROOT/reused['receipt']
        elif reused and reused.get('reference_meta'):
            path=ROOT/reused['reference_meta'];selector='outputs/candidate'
        else:
            path=ROOT/f'data/derived/experiments/c2_engine_{"wiring" if len(report["game_ids"])==3 else "development"}_v1/{gid}/{arm}/receipt.json'
        if not path.exists():raise ValueError('missing private arm receipt')
        entry=read_json(path)
        for key in selector.split('/'):entry=entry[key]
        if entry!=item['entry']:raise ValueError('private arm receipt differs from original report')
        games[gid][arm]={'receipt':str(path.relative_to(ROOT)),'sha256':sha256_file(path),'entry_selector':selector}
    if any(set(arms)!={'reference','bridge','candidate'} for arms in games.values()):raise ValueError('incomplete public game metadata')
    public['captures']=[{'game':gid,'arms':games[gid]} for gid in report['game_ids']]
    phase='wiring' if len(report['game_ids'])==3 else 'development'
    derived=[]
    for arm in ['reference','bridge','candidate']:
        name=f'c2_engine_{phase}_v1_{arm}'
        derived += [ROOT/f'data/derived/experiments/{name}.parquet',ROOT/f'data/derived/experiments/{name}_players.parquet',ROOT/f'analysis/experiments/{name}.json']
    public['derived_outputs']={str(path.relative_to(ROOT)):sha256_file(path) for path in derived}
    return public


def main():
    # Never relocate active-run metadata: both completed outputs must already exist.
    inputs=[ROOT/f'analysis/experiments/20261124_c2_engine_{phase}_v1.json' for phase in ['wiring','development']]
    private_paths=[ROOT/f'data/derived/experiments/c2_engine_{phase}_v1/report.json' for phase in ['wiring','development']]
    if not all(a.exists() or b.exists() for a,b in zip(inputs,private_paths)):raise ValueError('wait for both completed phases and stopped workers')
    source=ROOT/'analysis/c2_engine_runner.py'
    folder=ROOT/'data/derived/experiments/c2_engine_format_v1_sources';folder.mkdir(parents=True,exist_ok=True)
    copy=folder/'c2_engine_runner.py'
    if not copy.exists():copy.write_bytes(source.read_bytes())
    manifest=read_json(ROOT/'analysis/experiments/20261124_c2_engine_runtime_v1.json')
    if sha256_file(copy)!=manifest['source_sha256']['analysis/c2_engine_runner.py']:raise ValueError('prediction controller changed')
    for phase,old in zip(['wiring','development'],inputs):
        private=ROOT/f'data/derived/experiments/c2_engine_{phase}_v1/report.json'
        output=ROOT/f'analysis/experiments/20261124_c2_engine_{phase}_v2.json'
        if output.exists():
            if not private.exists() or read_json(output)['private_report_sha256']!=sha256_file(private):raise ValueError('completed compact report differs')
            continue
        if not private.exists():old.rename(private)
        elif old.exists():raise ValueError('both legacy and private reports exist; inspect explicitly')
        report=read_json(private)
        public=public_report(report,private,copy);write_json(output,public,pretty=True)
    print('Rich immutable reports retained under ignored data; public v2 reports contain aggregate counts and receipt hashes only',flush=True)

if __name__=='__main__':main()
