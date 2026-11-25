"""Prospective ledger uses its own clock and never overwrites original bytes."""
from copy import deepcopy
from datetime import datetime,timedelta,timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from analysis import c01_ledger as ledger
from analysis.c01_core import ContractError


def request(root,now):
    # Synthetic source artifacts are explicitly not real NBA forecast evidence.
    times={"fit":(now-timedelta(days=2)).isoformat(),"input":(now-timedelta(hours=3)).isoformat(),
           "published":(now-timedelta(hours=2)).isoformat(),"retrieved":(now-timedelta(hours=1)).isoformat(),"generated":(now-timedelta(minutes=30)).isoformat()}
    r={"game_id":"100","model_id":"synthetic-model","runtime_id":"synthetic-runtime","population":"original_pre_tip","provider":"ESPN",
       "tip_utc":(now+timedelta(hours=1)).isoformat()}
    for role in ("model","inputs","report"):
        p=root/f"{role}.json";p.write_text(json.dumps({"fixture":"synthetic", "role":role}))
        r[role]={"path":str(p),"sha256":ledger.fingerprint(p.read_bytes())}
    r['model']['fitted_at']=times['fit'];r['inputs'].update(as_of=times['input'],retrieved_at=times['input'])
    r['report'].update(published_at=times['published'],retrieved_at=times['retrieved'],publication_evidence="synthetic published field",retrieval_evidence="synthetic retained manifest")
    p=root/'forecast.json';p.write_text(json.dumps({"fixture":"synthetic","game_id":"100","tip_utc":r['tip_utc'],"model_id":r['model_id'],"runtime_id":r['runtime_id'],
         "generated_at":times['generated'],"inputs_sha256":r['inputs']['sha256'],"report_sha256":r['report']['sha256'],"forecast":{"points":[100,101]}}))
    r['forecast']={"path":str(p),"sha256":ledger.fingerprint(p.read_bytes()),"generated_at":times['generated']}
    return r


class ProspectiveLedgerTests(unittest.TestCase):
    def test_capture_audit_and_duplicate_entry_do_not_overwrite(self):
        now=datetime(2026,1,1,tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as directory,patch.object(ledger,'utc_now',return_value=now):
            root=Path(directory);r=request(root,now);dest=root/'ledger'
            entry=ledger.capture(dest,r,'original');original=(dest/'original/forecast.bin').read_bytes()
            self.assertEqual(entry['population'],'original_pre_tip');self.assertEqual(ledger.audit(dest)['entries'],1)
            with self.assertRaises(FileExistsError):ledger.capture(dest,r,'original')
            self.assertEqual((dest/'original/forecast.bin').read_bytes(),original)
            ledger.capture(dest,r,'later_capture')
            self.assertEqual(ledger.audit(dest)['entries'],2)

    def test_unknown_publication_late_report_and_late_capture_fail_closed(self):
        now=datetime(2026,1,1,tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as directory,patch.object(ledger,'utc_now',return_value=now):
            root=Path(directory);original=request(root,now)
            for mutate in ('publication','retrieval','evidence','capture','historical'):
                r=deepcopy(original)
                if mutate=='publication':r['report']['published_at']=None
                elif mutate=='retrieval':r['report']['retrieved_at']=(now+timedelta(hours=2)).isoformat()
                elif mutate=='evidence':r['report']['publication_evidence']=None
                elif mutate=='capture':r['tip_utc']=now.isoformat()
                else:r['population']='actual_participant'
                with self.assertRaises(ContractError):ledger.capture(root/'ledger',r)
            self.assertEqual(ledger.audit(root/'ledger')['entries'],0)

    def test_supplied_backdate_cannot_override_operation_clock(self):
        now=datetime(2026,1,1,tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);r=request(root,now);r['captured_at']=(now-timedelta(hours=3)).isoformat()
            with patch.object(ledger,'utc_now',return_value=now+timedelta(hours=2)):
                with self.assertRaises(ContractError):ledger.capture(root/'ledger',r)

    def test_source_tampering_and_forecast_identity_are_rejected(self):
        now=datetime(2026,1,1,tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as directory,patch.object(ledger,'utc_now',return_value=now):
            root=Path(directory);r=request(root,now)
            Path(r['model']['path']).write_text('changed')
            with self.assertRaisesRegex(ContractError,'model source'):ledger.capture(root/'ledger',r)
            r=request(root,now);payload=json.loads(Path(r['forecast']['path']).read_text());payload['game_id']='200'
            p=Path(r['forecast']['path']);p.write_text(json.dumps(payload));r['forecast']['sha256']=ledger.fingerprint(p.read_bytes())
            with self.assertRaisesRegex(ContractError,'game_id'):ledger.capture(root/'ledger',r)

    def test_crossing_tip_during_capture_and_changed_saved_bytes_are_detected(self):
        now=datetime(2026,1,1,tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);r=request(root,now)
            with patch.object(ledger,'utc_now',side_effect=[now,now+timedelta(hours=2)]):
                with self.assertRaises(ContractError):ledger.capture(root/'ledger',r)
            with patch.object(ledger,'utc_now',return_value=now):ledger.capture(root/'ledger',r,'original')
            p=root/'ledger/original/forecast.bin';p.chmod(0o644);p.write_bytes(b'corrupted')
            with self.assertRaisesRegex(ContractError,'artifact changed'):ledger.audit(root/'ledger')


if __name__=='__main__':unittest.main()
