import os,tempfile,unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from types import SimpleNamespace
from unittest.mock import patch
from basketball_common import read_json,write_json,sha256_file
from scripts import live_forecast as live
from tests import test_live_resume as fixtures

class ReplayQueueTests(unittest.TestCase):
 def test_replays_share_workers_and_game_is_emitted_only_after_all_finish(self):
  barrier=Barrier(2);completed=[]
  def finish(job):
   return {'folder':job['folder'],'replay_jobs':[{'kind':'replay','folder':job['folder'],'key':i} for i in range(2)]}
  def replay(job):
   barrier.wait(timeout=2);completed.append(job['key']);return {}
  def finish_replay(job):
   self.assertEqual(sorted(completed),[0,1]);return job['folder']
  with tempfile.TemporaryDirectory() as tmp,patch.dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1'),patch.object(live,'ProcessPoolExecutor',ThreadPoolExecutor),patch.object(live,'initialise'),patch.object(live,'_chunk',side_effect=fixtures.ResumeTests.chunk),patch.object(live,'_merge',return_value={}),patch.object(live,'_finish_game',side_effect=finish),patch.object(live,'_replay',side_effect=replay),patch.object(live,'_replay_finish',side_effect=finish_replay):
   folder=Path(tmp)/'game';g=SimpleNamespace(day='2026-11-23',input_before='2026-11-23',game={'game_id':'g'})
   result=list(live.run([(g,[],4,str(folder),{})],{'id':'test','rotation_fit':'independent-v1','world_details':'visible-worlds-v1'},{},workers=2,chunk_worlds=2))
   self.assertEqual(result,[str(folder.resolve())])

 def test_detailed_game_rejects_legacy_completion_without_replay_files(self):
  with tempfile.TemporaryDirectory() as tmp:
   folder=Path(tmp);names=['game.json','players.npz','points.npz','provenance.json','inputs.pkl']
   for name in names:(folder/name).write_bytes(b'complete')
   write_json(folder/'provenance.json',{'selected':False,'engine':{'world_details':'visible-worlds-v1'}})
   write_json(folder/'completion.json',{'schema':1,'files':{n:sha256_file(folder/n) for n in names}})
   with self.assertRaisesRegex(ValueError,'complete-game receipt'):live.verified_completion(folder)

if __name__=='__main__':unittest.main()
