import unittest

import pandas as pd

from scripts.a1_prior_roster_screen import classify


class PriorRosterScreenTests(unittest.TestCase):
    def fixture(self):
        rows = pd.DataFrame([{'game_id': '1', 'team': '2', 'player': str(i),
                              'date_et': '2024-01-02', 'prior_day': '2023-12-31',
                              'prior_profile_date': '2024-01-01', 'prior_minutes_date': '2023-12-31',
                              'availability_fallback': 1. if i < 5 else .5} for i in range(6)])
        profiles = pd.DataFrame([{'date_et': '2024-01-01', 'player': str(i), 'team': '2', 'pos': pos}
                                 for i, pos in enumerate(('PG', 'SG', 'SF', 'PF', 'C'))])
        return rows, profiles

    def test_unknown_bench_is_counted_without_inventing_a_position(self):
        rows, profiles = self.fixture()
        out, teams = classify(rows, profiles)
        self.assertTrue(teams[0]['supported_starter_pool'])
        self.assertFalse(teams[0]['all_profiles_positions_known'])
        self.assertEqual(teams[0]['missing_profiles'], 1)
        self.assertTrue(pd.isna(out.loc[out['player'].eq('5'), 'prior_position'].iloc[0]))

    def test_insufficient_sure_players_considers_uncertain_missing_positions(self):
        rows, profiles = self.fixture()
        rows.loc[0, 'availability_fallback'] = .5
        _, teams = classify(rows, profiles)
        self.assertFalse(teams[0]['supported_starter_pool'])
        self.assertEqual(teams[0]['starter_pool_missing_positions'], ['5'])

    def test_same_day_or_future_provenance_fails(self):
        for key in ('prior_day', 'prior_profile_date', 'prior_minutes_date'):
            rows, profiles = self.fixture()
            rows.loc[0, key] = rows.loc[0, 'date_et']
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'strictly before'):
                classify(rows, profiles)

    def test_duplicate_snapshots_cannot_multiply_the_roster(self):
        rows, profiles = self.fixture()
        with self.assertRaisesRegex(ValueError, 'ambiguous'):
            classify(rows, pd.concat([profiles, profiles.iloc[:1]], ignore_index=True))


if __name__ == '__main__':
    unittest.main()
