import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import numpy as np

from scripts import a1_branch_persist, engine
from tests import test_a1_lineup_branches


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

    def test_rejects_future_or_missing_median_dates(self):
        with patch.object(a1_branch_persist.pd, 'read_parquet', return_value=pd.DataFrame({'date_et': ['2025-12-31']})):
            a1_branch_persist.check_median_cutoff(Path('unused'), '2026-01-01')
        for dates in (['2026-01-01'], ['2026-01-02'], [None], []):
            with self.subTest(dates=dates), patch.object(a1_branch_persist.pd, 'read_parquet',
                                                        return_value=pd.DataFrame({'date_et': dates})):
                with self.assertRaises(ValueError):
                    a1_branch_persist.check_median_cutoff(Path('unused'), '2026-01-01')


class QuarterAvailabilityTests(unittest.TestCase):
    def test_rounding_preserves_uncertain_endpoints_and_halfway_ties(self):
        for original, expected in ((0, 0), (0.01, 0.25), (0.15, 0.25), (0.375, 0.5),
                                   (0.6, 0.5), (0.7, 0.75), (0.9, 0.75), (1, 1)):
            with self.subTest(original=original):
                self.assertEqual(a1_branch_persist.quarter_availability(original), expected)
        for invalid in (-0.1, 1.1, np.nan, np.inf):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                a1_branch_persist.quarter_availability(invalid)

    def test_candidate_changes_all_draws_without_mutating_original(self):
        game, registry, latest, inputs = test_a1_lineup_branches.OnePlayerBranchesTests().selection_inputs()
        game.avail[0] = game.players['home'][0]['availability'] = inputs['100']['availability'] = 0.7
        game.avail[1] = game.players['home'][1]['availability'] = inputs['101']['availability'] = 0.9
        candidate, scaled = a1_branch_persist.quarter_candidate(game, inputs)
        self.assertEqual(candidate.avail[:2].tolist(), [0.75, 0.75])
        self.assertEqual(game.avail[:2].tolist(), [0.7, 0.9])
        self.assertEqual([scaled[x]['original_availability'] for x in ('100', '101')], [0.7, 0.9])
        self.assertEqual(inputs['100']['availability'], 0.7)
        selected, ranking = a1_branch_persist.a1_lineup_branches.select_uncertain(candidate, registry, latest, scaled)
        self.assertEqual(selected[0].probability, 0.75)
        self.assertEqual(next(row['original_availability'] for row in ranking if row['player_id'] == '100'), 0.7)
        self.assertEqual(candidate.players['home'][1]['availability'], 0.75)
        branches = a1_branch_persist.a1_lineup_branches.enumerate_branches(candidate, [('1', '100')])
        self.assertEqual([float(branch.weight) for branch in branches], [0.75, 0.25])
        self.assertEqual(a1_branch_persist.a1_lineup_branches.prepare_branch(
            candidate, branches[0].assignments).avail[1], 0.75)
        game.avail[0] = 0.5
        with self.assertRaisesRegex(ValueError, 'original roster'):
            a1_branch_persist.quarter_candidate(game, inputs)


if __name__ == '__main__':
    unittest.main()
