import os
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

from basketball_common import read_json, sha256_file, write_json
from scripts import live_forecast, projection


class WorldQueueTests(unittest.TestCase):
    def test_one_game_uses_all_workers_and_finishes_only_after_all_chunks(self):
        lock, first_ten = threading.Lock(), threading.Barrier(10)
        seen, finished, merged = set(), [], []
        active, peak = 0, 0

        def chunk(job):
            nonlocal active, peak
            key = job['start'], job['stop']
            with lock:
                self.assertNotIn(key, seen)
                seen.add(key)
                active += 1
                peak = max(peak, active)
                early = len(seen) <= 10
            if early:
                first_ten.wait(timeout=5)
            with lock:
                active -= 1
                finished.append(key)

        def merge(job):
            self.assertEqual(len(finished), 13)
            merged.append(job['key'])

        def game(job):
            self.assertEqual(len(merged), 1)
            return job['folder']

        def executor(**kwargs):
            self.assertEqual(kwargs['max_workers'], 10)
            return ThreadPoolExecutor(max_workers=10)

        with tempfile.TemporaryDirectory() as tmp, \
                patch.dict(os.environ, OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1'), \
                patch.object(live_forecast, 'ProcessPoolExecutor', executor), \
                patch.object(live_forecast, '_chunk', chunk), \
                patch.object(live_forecast, '_merge', merge), \
                patch.object(live_forecast, '_finish_game', game):
            folder = str(Path(tmp) / 'game')
            g = SimpleNamespace(game={'game_id':'one'}, input_before='2026-11-23', day='2026-11-23')
            tasks = [(g, [], 13, folder, {})]
            result = list(live_forecast.run(tasks, {'rotation_fit':'independent-v1', 'id':'candidate'}, {},
                                            workers=10, chunk_worlds=1))
            self.assertEqual([str(Path(p).resolve()) for p in result], [str(Path(folder).resolve())])
            self.assertEqual(peak, 10)
            self.assertEqual(seen, {(i,i+1) for i in range(13)})
            self.assertEqual(read_json(Path(folder)/'work-plan.json')['worlds'], 13)

    def test_merge_retains_order_and_rejects_changed_ranges_seeds_and_lengths(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan = {'worlds':5, 'chunk_worlds':2, 'chunks':str(root), 'seed':'123',
                    'capture':str(root/'merged.npz')}
            paths = []
            for start, stop in ((0,2),(2,4),(4,5)):
                path = root/f'{start:05d}-{stop:05d}.npz'
                np.savez_compressed(path, player_ids=np.array(['a','b']), side=np.array([0,1]),
                                    minutes=np.full((stop-start,2,5),start))
                entry = {'start':start, 'stop':stop, 'sha256':sha256_file(path), 'counts':{'fives':stop-start},
                         'seed':str(projection.seed_for('world-chunk-v1',123,start,stop)), 'targets':[120,120]}
                write_json(path.with_suffix('.json'), entry)
                paths.append(path)
            result = live_forecast._merge({'plan':plan})
            self.assertEqual(result['counts']['fives'],5)
            with np.load(plan['capture']) as z:
                self.assertEqual(z['minutes'][:,0,0].tolist(),[0,0,2,2,4])
            path = paths[1]
            original = read_json(path.with_suffix('.json'))
            for change in ({'start':0},{'seed':'wrong'},{'sha256':'wrong'}):
                write_json(path.with_suffix('.json'),{**original,**change})
                with self.assertRaisesRegex(ValueError,'world chunk'):
                    live_forecast._merge({'plan':plan})
            np.savez_compressed(path, player_ids=np.array(['a','b']), side=np.array([0,1]),
                                minutes=np.zeros((1,2,5)))
            write_json(path.with_suffix('.json'),{**original,'sha256':sha256_file(path)})
            with self.assertRaisesRegex(ValueError,'number of complete worlds'):
                live_forecast._merge({'plan':plan})

    def test_coupled_recipe_cannot_enter_chunk_queue(self):
        with self.assertRaisesRegex(ValueError,'independent rotation'):
            list(live_forecast.run([], {'id':'legacy'}, {}))


if __name__ == '__main__':
    unittest.main()
