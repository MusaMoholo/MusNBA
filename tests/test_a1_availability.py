import unittest
from unittest.mock import patch

import pandas as pd

from scripts import a1_availability_cohort as cohort


class AvailabilityCohortTests(unittest.TestCase):
    def test_membership_uses_only_prior_unique_latest_team(self):
        history = pd.DataFrame([
            ('2026-01-01', 'a', 'old'), ('2026-01-02', 'a', 'new'),
            ('2026-01-02', 'b', 'old'), ('2026-01-02', 'b', 'new'),
            ('2026-01-03', 'c', 'old'), ('2026-01-03', 'a', 'same-day'),
        ], columns=['day', 'player', 'team'])
        members, ambiguous = cohort.prior_membership(history, '2026-01-03')
        self.assertEqual(members.to_dict(orient='records'), [{'prior_day': '2026-01-02', 'player': 'a', 'team': 'new'}])
        self.assertEqual(ambiguous, ['b'])

    def test_participation_keeps_zero_or_missing_minutes_unknown(self):
        box = pd.DataFrame({'did_not_play': [True, False, False, False, None],
                            'minutes': [None, 12, 0, None, 4]})
        labels = cohort.participation(box)
        self.assertEqual(labels.iloc[:2].tolist(), [0.0, 1.0])
        self.assertTrue(labels.iloc[2:].isna().all())
        box.loc[0, 'minutes'] = 1
        with self.assertRaisesRegex(ValueError, 'DNP with positive minutes'):
            cohort.participation(box)
        box.loc[0, 'minutes'] = -1
        with self.assertRaisesRegex(ValueError, 'negative minutes'):
            cohort.participation(box)

    def test_report_and_rows_cannot_overwrite_each_other(self):
        argv = ['a1_availability_cohort.py', 'run', '--output', '/tmp/a1-same-path',
                '--rows-output', '/tmp/a1-same-path']
        with patch('sys.argv', argv), patch.object(cohort, 'build') as build:
            with self.assertRaisesRegex(ValueError, 'different output paths'):
                cohort.main()
            build.assert_not_called()


if __name__ == '__main__':
    unittest.main()
