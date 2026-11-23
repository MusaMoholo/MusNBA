import base64
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from analysis.a1_slate_minutes_audit import audit
from scripts.projection import SLICES


class SlateMinutesAuditTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.snapshot, self.api = root / 'snapshot', root / 'api'
        self.snapshot.mkdir()
        game_dir = self.api / 'game' / 'g'
        game_dir.mkdir(parents=True)
        meta = {'origin': '2026-01-02', 'slate_date': '2026-01-02', 'cutoff': '2026-01-01',
                'sims': 2, 'season_sims': 2, 'games': ['g'], 'model': {'id': 'test'}}
        (self.snapshot / 'meta.json').write_text(json.dumps(meta))
        ids = np.array([str(i) for i in range(10)])
        side = np.array([0] * 5 + [1] * 5, dtype=np.int8)
        minutes = np.zeros((2, 10, 5), dtype=np.float64)
        minutes[:, :, :4] = 12
        lines = np.zeros((2, 10, 2), dtype=np.uint8)
        lines[:, :, 0] = 48
        lines[:, 0, 1] = 1
        points = np.zeros((2, 2, 5), dtype=np.int16)
        points[:, 0, 0] = 1
        np.savez(self.snapshot / 'engine_players.npz', g__ids=ids, g__side=side, g__lines=lines,
                 g__minutes=minutes, g__minutes_schema=np.array(1))
        np.savez(self.snapshot / 'engine_worlds.npz', g=points)
        pack = lambda array: base64.b64encode(array.tobytes()).decode()
        world = {'worlds': 2, 'minutes_schema': 1, 'players': ids.tolist(), 'side': side.tolist(),
                 'period_minutes_f64_le': pack(minutes), 'lines': pack(lines),
                 'team_periods': pack(points.astype(np.uint8))}
        phone = np.stack([np.sort(minutes[:, :, cols].sum(axis=2), axis=0)
                          for cols in SLICES.values()], axis=2)
        marginal = {'schema': 1, 'worlds': 2, 'players': ids.tolist(), 'periods': list(SLICES),
                    'minutes_f64_le': pack(phone)}
        (game_dir / 'worlds.json').write_text(json.dumps(world))
        self.marginal_path = game_dir / 'minute-marginals.json'
        self.marginal_path.write_text(json.dumps(marginal))

    def test_exact_worlds_and_marginals_reconcile(self):
        result = audit(self.snapshot, self.api, 2)
        self.assertEqual(result['world_minute_values_checked'], 100)
        self.assertEqual(result['phone_marginal_values_checked'], 140)
        self.assertEqual(result['team_scores_checked'], 4)

    def test_mismatched_phone_minutes_fail(self):
        marginal = json.loads(self.marginal_path.read_text())
        data = np.frombuffer(base64.b64decode(marginal['minutes_f64_le']), dtype='<f8').copy()
        data[0] += 0.1
        marginal['minutes_f64_le'] = base64.b64encode(data.tobytes()).decode()
        self.marginal_path.write_text(json.dumps(marginal))
        with self.assertRaisesRegex(ValueError, 'phone minute distribution differs'):
            audit(self.snapshot, self.api, 2)

    def test_incomplete_team_minutes_fail_even_if_views_match(self):
        path = self.snapshot / 'engine_players.npz'
        with np.load(path, allow_pickle=False) as archive:
            data = {key: archive[key] for key in archive.files}
        minutes = data['g__minutes']
        minutes[:, 0, 0] -= 0.1
        np.savez(path, **data)
        world_path = self.api / 'game' / 'g' / 'worlds.json'
        world = json.loads(world_path.read_text())
        world['period_minutes_f64_le'] = base64.b64encode(minutes.tobytes()).decode()
        world_path.write_text(json.dumps(world))
        marginal = json.loads(self.marginal_path.read_text())
        phone = np.stack([np.sort(minutes[:, :, cols].sum(axis=2), axis=0)
                          for cols in SLICES.values()], axis=2)
        marginal['minutes_f64_le'] = base64.b64encode(phone.tobytes()).decode()
        self.marginal_path.write_text(json.dumps(marginal))
        with self.assertRaisesRegex(ValueError, 'regulation team minutes'):
            audit(self.snapshot, self.api, 2)


if __name__ == '__main__':
    unittest.main()
