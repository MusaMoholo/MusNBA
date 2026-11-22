import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from basketball_common import verified_pre_tip, write_json
from scripts import evaluate, lineups, views


class LineupTimingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.snapshots = self.root / 'snapshots'
        self.day = '2026-11-22'
        self.snap = self.snapshots / self.day
        self.snap.mkdir(parents=True)
        home = [{'id': str(i), 'starter': True} for i in range(1, 6)]
        away = [{'id': str(i), 'starter': True} for i in range(6, 11)]
        self.games = {gid: {'home': {'players': home}, 'away': {'players': away}}
                      for gid in ('before', 'after', 'unknown')}
        self.box = pd.DataFrame([{'game_id': gid, 'player_id': str(i), 'starter': '1'}
                                 for gid in self.games for i in range(1, 11)])
        self.meta = {'kind': 'prospective', 'model': {'id': 'engine-v1.3'},
                     'completed_at': '2026-11-22T18:00:00Z',
                     'pre_tip': {'before': True, 'after': False}}
        write_json(self.snap / 'games.json', self.games)
        self.paths = patch.multiple(lineups, SNAPSHOTS=self.snapshots,
                                    DERIVED=self.root, OUT=self.root / 'accuracy.json')
        self.paths.start()
        self.addCleanup(self.paths.stop)

    def test_only_verified_pre_tip_prospective_games_are_scored(self):
        write_json(self.snap / 'meta.json', self.meta)
        result = lineups.score_day(self.day, self.box)
        assert result is not None
        self.assertEqual(result['team_games'], 2)
        self.assertEqual(result['slot_accuracy'], 1.0)
        self.assertEqual(result['completed_at'], self.meta['completed_at'])
        for change in ({'completed_at': None}, {'kind': 'retrospective'}, {'pre_tip': None}):
            with self.subTest(change=change):
                write_json(self.snap / 'meta.json', {**self.meta, **change})
                self.assertIsNone(lineups.score_day(self.day, self.box))

    def test_legacy_aggregate_is_retained_but_excluded_from_overall(self):
        legacy = {'2026-11-21': {'team_games': 132, 'slot_accuracy': 0.8273, 'all_five': 0.3106}}
        write_json(self.root / 'accuracy.json', {'slates': legacy, 'overall': {'team_games': 132}})
        write_json(self.snap / 'meta.json', self.meta)
        with patch.object(lineups.pd, 'read_csv', return_value=self.box):
            record = lineups.score([self.day])
            again = lineups.score([self.day])
        self.assertEqual(record['legacy_unverified_slates'], legacy)
        self.assertEqual(record['legacy_unverified_overall'], {'team_games': 132})
        self.assertEqual(record['overall']['team_games'], 2)
        self.assertEqual(again, record)
        self.assertEqual(json.loads((self.root / 'accuracy.json').read_text()), record)

    def test_missing_and_malformed_timing_remain_unverified(self):
        for metadata in ({}, {'completed_at': 'time'}, {'completed_at': 'time', 'pre_tip': None},
                         {'completed_at': '2026-11-22T18:00:00Z', 'pre_tip': {'x': 1}}):
            with self.subTest(metadata=metadata):
                self.assertIsNone(verified_pre_tip(metadata, 'x'))
        for stamp in ('time', '2026-11-22T18:00:00'):
            with self.subTest(stamp=stamp), self.assertRaises(ValueError):
                verified_pre_tip({'completed_at': stamp, 'pre_tip': {'x': True}}, 'x')

    def test_lab_view_never_presents_unmigrated_scores_as_verified(self):
        target = self.root / 'lineups' / 'accuracy.json'
        write_json(target, {'slates': {'old': {'team_games': 2}}, 'overall': {'team_games': 2}})
        with patch.object(views, 'DERIVED', self.root), patch.object(evaluate, 'EXPERIMENTS', self.root):
            payload = views.lab({})['lineups']
        self.assertIsNone(payload['overall'])
        self.assertEqual(payload['slates'], [])
        self.assertEqual(payload['legacy_unverified_slates'], 1)


if __name__ == '__main__':
    unittest.main()
