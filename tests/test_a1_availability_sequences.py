import unittest

import pandas as pd

from scripts import a1_availability_sequences as sequences


def example_schedule():
    rows = [{'season': 2024, 'team': '7', 'game_id': str(i + 1), 'day': f'2024-01-{2 * i + 1:02d}',
             'team_index': i} for i in range(6)]
    rows.append({'season': 2024, 'team': '8', 'game_id': '20', 'day': '2024-01-02', 'team_index': 0})
    return pd.DataFrame(rows)


def listing(player, game, status, minutes=None, reason=None, team='7'):
    schedule = example_schedule().set_index(['team', 'game_id']).loc[(team, str(game))]
    return {'season': 2024, 'team': team, 'player': player, 'game_id': str(game), 'day': schedule['day'],
            'team_index': schedule['team_index'], 'status': status, 'reason': reason, 'minutes': minutes}


class SequenceTests(unittest.TestCase):
    def test_return_and_rest_use_only_consecutive_known_listings(self):
        box = pd.DataFrame([
            listing('a', 1, 'play', 32), listing('a', 2, 'dnp', reason='INJURY'),
            listing('a', 3, 'dnp', reason='ILLNESS'), listing('a', 4, 'play', 28),
            listing('a', 5, 'dnp', reason='REST'), listing('a', 6, 'play', 20),
        ])
        rows, _ = sequences.construct(box, example_schedule())
        rows = rows.set_index('prior_game_id')
        self.assertEqual(rows.loc['1', 'cohort'], 'rest')
        self.assertEqual(rows.loc['1', 'outcome'], 0)
        self.assertEqual(rows.loc['2', 'prior_reason'], 'explicit_injury_or_illness')
        self.assertEqual(rows.loc['2', 'duration_bin'], '1')
        self.assertEqual(rows.loc['2', 'outcome'], 0)
        self.assertEqual(rows.loc['3', 'duration_bin'], '2-3')
        self.assertEqual(rows.loc['3', 'outcome'], 1)
        self.assertEqual(rows.loc['3', 'prior_role'], 'star')
        self.assertEqual(rows.loc['4', 'outcome'], 1)
        self.assertEqual(rows.loc['5', 'prior_reason'], 'rest')
        self.assertEqual(rows.loc['5', 'outcome'], 1)
        self.assertEqual(rows.loc['6', 'next_status'], 'season_end')
        self.assertTrue(pd.isna(rows.loc['6', 'outcome']))

    def test_unlisted_unknown_trade_and_left_censor_are_not_outcomes(self):
        box = pd.DataFrame([
            listing('gap', 1, 'play', 10), listing('gap', 3, 'dnp', reason='INJURY'),
            listing('gap', 4, 'play', 10),
            listing('first', 1, 'dnp', reason='REST'), listing('first', 2, 'play', 10),
            listing('unknown', 1, 'play', 15), listing('unknown', 2, 'unknown', 0),
            listing('missing-reason', 1, 'play', 20), listing('missing-reason', 2, 'dnp'),
            listing('trade', 1, 'play', 18), listing('trade', 20, 'play', 18, team='8'),
        ])
        rows, counts = sequences.construct(box, example_schedule())
        rows = rows.set_index(['player', 'prior_game_id'])
        self.assertEqual(rows.loc[('gap', '1'), 'next_status'], 'unlisted')
        self.assertEqual(rows.loc[('gap', '3'), 'cohort'], 'left_censored_return')
        self.assertTrue(pd.isna(rows.loc[('gap', '3'), 'outcome']))
        self.assertTrue(pd.isna(rows.loc[('first', '1'), 'outcome']))
        self.assertEqual(rows.loc[('unknown', '1'), 'next_status'], 'unknown')
        self.assertTrue(pd.isna(rows.loc[('unknown', '1'), 'outcome']))
        self.assertTrue(pd.isna(rows.loc[('missing-reason', '1'), 'outcome']))
        self.assertEqual(rows.loc[('trade', '1'), 'next_status'], 'team_change_prior')
        self.assertTrue(pd.isna(rows.loc[('trade', '1'), 'outcome']))
        self.assertEqual(counts['unknown_prior_listings'], 1)

    def test_future_listing_does_not_change_an_earlier_known_transition(self):
        initial = pd.DataFrame([listing('a', 1, 'play', 25), listing('a', 2, 'dnp', reason='REST')])
        before, _ = sequences.construct(initial, example_schedule())
        later = pd.concat([initial, pd.DataFrame([listing('a', 6, 'play', 30)])], ignore_index=True)
        after, _ = sequences.construct(later, example_schedule())
        columns = ['prior_day', 'date_et', 'cohort', 'prior_role', 'next_status', 'outcome']
        pd.testing.assert_series_equal(before.loc[before['prior_game_id'].eq('1'), columns].iloc[0],
                                       after.loc[after['prior_game_id'].eq('1'), columns].iloc[0])


if __name__ == '__main__':
    unittest.main()
