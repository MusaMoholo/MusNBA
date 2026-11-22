import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import a1_branch_persist, engine


class SnapshotGuardTests(unittest.TestCase):
    def setUp(self):
        self.fixture = {'game_id': '123', 'date_et': '2026-01-02', 'home_id': '1', 'away_id': '2'}
        self.registry = {'100': {'team': '1'}}
        self.report = {'home': [], 'away': []}
        self.meta = {
            'slate_date': '2026-01-02', 'origin': '2026-01-01', 'kind': 'prospective',
            'model': {'id': engine.ENGINE['id'], 'models': engine.ENGINE['models'], 'rotation': 'targets',
                      'pool': engine.ROTATION['pool']},
            'inputs': {**{k: 'digest' for k in ('master_sha256', 'player_games_sha256',
                                                'team_games_sha256', 'player_periods_sha256')},
                       'registry_run': 'run',
                       'engine_inputs_sha256': {k: 'digest' for k in ('latest', 'team_latest', 'stints',
                                                                      'on_court', 'models')}},
        }
        self.config = {'train_through': '2025-12-31'}
        self.saved = {'123': {'availability_report': self.report}}

    def read(self, path):
        return {'meta.json': self.meta, 'games.json': self.saved,
                'players.json': {'run': 'run', 'players': self.registry},
                'config.json': self.config}[path.name]

    def check(self):
        with (patch.object(a1_branch_persist, 'read_json', side_effect=self.read),
              patch.object(a1_branch_persist, 'sha256_file', return_value='digest'),
              patch.object(a1_branch_persist.master_fixtures, 'load', return_value=[self.fixture]),
              patch.object(a1_branch_persist.nightly, 'forecast_availability_report', return_value=self.report)):
            return a1_branch_persist.checked_snapshot('2026-01-02', '123')

    def test_accepts_matching_snapshot_and_rejects_changed_inputs(self):
        self.assertEqual(self.check(), (self.meta, self.fixture, self.registry))
        self.meta['inputs']['team_games_sha256'] = 'changed'
        with self.assertRaisesRegex(ValueError, 'box-score or master'):
            self.check()

    def test_rejects_changed_report_and_non_prior_model(self):
        self.saved['123']['availability_report'] = {'home': [{'id': '100'}], 'away': []}
        with self.assertRaisesRegex(ValueError, 'availability report'):
            self.check()
        self.saved['123']['availability_report'] = self.report
        self.config['train_through'] = self.meta['origin']
        with self.assertRaisesRegex(ValueError, 'before the forecast origin'):
            self.check()

    def test_rejects_invalid_identifiers_and_existing_outputs(self):
        with self.assertRaises(ValueError):
            a1_branch_persist.checked_snapshot('../2026-01-02', '123')
        with self.assertRaisesRegex(ValueError, 'ASCII digits'):
            a1_branch_persist.checked_snapshot('2026-01-02', '../123')
        with self.assertRaises(FileExistsError):
            a1_branch_persist.run('2026-01-02', '123', 32, Path(__file__), Path('unused'))


if __name__ == '__main__':
    unittest.main()
