import os
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from types import SimpleNamespace
from threading import Event
from unittest.mock import patch

import numpy as np

from basketball_common import read_json, sha256_file, write_json
from scripts import live_forecast as live


@dataclass
class Selection:
    team_id: str = 'h'
    player_id: str = 'p'
    missing: tuple = ()


class ResumeTests(unittest.TestCase):
    def test_queue_continues_while_completed_game_consumer_is_paused(self):
        completed_second = Event()
        runtime = {'id': 'test', 'rotation_fit': 'independent-v1'}
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1'), \
                patch.object(live, 'ProcessPoolExecutor', ThreadPoolExecutor), patch.object(live, 'initialise'), \
                patch.object(live, '_chunk', side_effect=self.chunk), patch.object(live, '_merge', return_value={}):
            root = Path(tmp).resolve()
            tasks = [(SimpleNamespace(day='2026-11-23', input_before='2026-11-23', game={'game_id': name}),
                      [], 2, str(root / name), {}) for name in ('first', 'second')]

            def finish(job):
                result = self.finish(job)
                if Path(result).name == 'second':
                    completed_second.set()
                return result

            with patch.object(live, '_finish_game', side_effect=finish):
                stream = live.run(tasks, runtime, {}, workers=1, chunk_worlds=2)
                try:
                    self.assertEqual(next(stream), str(root / 'first'))
                    self.assertTrue(completed_second.wait(2), 'publication must not stall the shared queue')
                    self.assertEqual(list(stream), [str(root / 'second')])
                finally:
                    stream.close()

    def test_duplicate_games_fail_before_creating_a_namespace(self):
        game = SimpleNamespace(game={'game_id': 'same'})
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tasks = [(game, [], 4, str(root / name), {}) for name in ('first', 'second')]
            with patch.object(live, 'ProcessPoolExecutor', side_effect=AssertionError('must not launch')):
                with self.assertRaisesRegex(ValueError, 'duplicate'):
                    list(live.run(tasks, {'rotation_fit': 'independent-v1'}, {}))
            self.assertFalse(list(root.iterdir()))

    def queue(self, folder, *, resume=False, median=None, selected=()):
        game = SimpleNamespace(day='2026-11-23', input_before='2026-11-23', game={'game_id': 'g'})
        task = (game, list(selected), 4, str(folder), {'origin': '2026-11-23', 'sources': {'model': 'fixed'}})
        return live.run([task], {'id': 'test', 'rotation_fit': 'independent-v1'}, median or {},
                        workers=1, chunk_worlds=2, resume=resume)

    @staticmethod
    def chunk(job):
        p = job['plan']
        path = Path(p['chunks']) / f"{job['start']:05d}-{job['stop']:05d}.npz"
        np.savez(path, minutes=np.arange(job['start'], job['stop']))
        entry = {'start': job['start'], 'stop': job['stop'], 'sha256': sha256_file(path),
                 'seed': str(live.projection.seed_for('world-chunk-v1', int(p['seed']), job['start'], job['stop']))}
        write_json(path.with_suffix('.json'), entry)
        return entry

    @staticmethod
    def finish(job):
        folder = Path(job['folder'])
        for name in ('game.json', 'players.npz', 'points.npz'):
            (folder / name).write_bytes(b'complete')
        selected = bool(read_json(folder / 'work-plan.json')['selected'])
        write_json(folder / 'provenance.json', {'selected': selected})
        names = ['game.json', 'players.npz', 'points.npz', 'provenance.json', 'inputs.pkl']
        if selected:
            (folder / 'worlds.json').write_text('{}')
            names.append('worlds.json')
        write_json(folder / 'completion.json', {'schema': 1, 'files': {n: sha256_file(folder / n) for n in names}})
        return str(folder)

    def test_interrupt_reuses_exact_chunks_and_rejects_changed_inputs(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1'), \
                patch.object(live, 'ProcessPoolExecutor', ThreadPoolExecutor), patch.object(live, 'initialise'), \
                patch.object(live, '_merge', return_value={}), patch.object(live, '_finish_game', side_effect=self.finish):
            folder = Path(tmp) / 'g'
            calls = []

            def interrupted(job):
                calls.append(job['start'])
                if job['start'] == 2:
                    raise RuntimeError('interrupted')
                return self.chunk(job)

            with patch.object(live, '_chunk', side_effect=interrupted):
                with self.assertRaisesRegex(RuntimeError, 'interrupted'):
                    list(self.queue(folder))
            self.assertEqual(calls, [0, 2])
            saved = sha256_file(folder / 'chunks/0/00000-00002.npz')
            with patch.object(live, '_chunk', side_effect=self.chunk) as compute:
                with self.assertRaisesRegex(ValueError, 'changed inputs'):
                    list(self.queue(folder, resume=True, median={'future': 1}))
                compute.assert_not_called()
                self.assertEqual(list(self.queue(folder, resume=True)), [str(folder.resolve())])
                self.assertEqual(compute.call_count, 1)
                self.assertEqual(compute.call_args.args[0]['start'], 2)
            self.assertEqual(sha256_file(folder / 'chunks/0/00000-00002.npz'), saved)
            self.assertTrue(live.verified_completion(folder))
            with patch.object(live, 'ProcessPoolExecutor', side_effect=AssertionError('must not launch')):
                self.assertEqual(list(self.queue(folder, resume=True)), [str(folder.resolve())])
                relative = Path(os.path.relpath(folder))
                self.assertEqual(list(self.queue(relative, resume=True)), [str(folder.resolve())])
            (folder / 'points.npz').write_bytes(b'corrupted')
            with self.assertRaisesRegex(ValueError, 'changed complete-game'):
                list(self.queue(folder, resume=True))

    def test_committed_corrupt_chunk_is_rejected_before_workers_start(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1'), \
                patch.object(live, 'ProcessPoolExecutor', ThreadPoolExecutor), patch.object(live, 'initialise'), \
                patch.object(live, '_chunk', side_effect=self.chunk), patch.object(live, '_merge', side_effect=RuntimeError('merge stopped')):
            folder = Path(tmp) / 'g'
            with self.assertRaisesRegex(RuntimeError, 'merge stopped'):
                list(self.queue(folder))
            (folder / 'chunks/0/00000-00002.npz').write_bytes(b'corrupted')
            with patch.object(live, 'ProcessPoolExecutor', side_effect=AssertionError('must not launch')):
                with self.assertRaisesRegex(ValueError, 'changed saved world chunk'):
                    list(self.queue(folder, resume=True))

    def test_branch_selection_round_trips_its_tuple_metadata_on_resume(self):
        branch = SimpleNamespace(branch_id='lineup-test', assignments=(('h', 'p', True),), weight=Fraction(1))
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1'), \
                patch.object(live, 'ProcessPoolExecutor', ThreadPoolExecutor), patch.object(live, 'initialise'), \
                patch('scripts.a1_lineup_branches.enumerate_branches', return_value=[branch]), \
                patch.object(live, '_merge', return_value={}), patch.object(live, '_finish_game', side_effect=self.finish):
            folder = Path(tmp) / 'g'
            with patch.object(live, '_chunk', side_effect=RuntimeError('pause')):
                with self.assertRaisesRegex(RuntimeError, 'pause'):
                    list(self.queue(folder, selected=[Selection()]))
            with patch.object(live, '_chunk', side_effect=self.chunk):
                self.assertEqual(list(self.queue(folder, selected=[Selection()], resume=True)), [str(folder.resolve())])


if __name__ == '__main__':
    unittest.main()
