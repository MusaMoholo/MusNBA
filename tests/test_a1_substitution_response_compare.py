import unittest

import pandas as pd

from scripts import a1_substitution_response_compare as response


class HistoricalFoulStateTests(unittest.TestCase):
    def test_incomplete_or_inconsistent_fouls_remain_unknown(self):
        events = pd.DataFrame([
            {'game_id': game, 'period_number': period, 'type_text': 'jump ball', 'athlete_id_1': None}
            for game in ['1', '2'] for period in (1, 2, 3)
        ] + [
            {'game_id': '1', 'period_number': 2, 'type_text': 'personal foul', 'athlete_id_1': 10},
            {'game_id': '2', 'period_number': 2, 'type_text': 'personal foul', 'athlete_id_1': None},
        ])
        box = pd.DataFrame([
            {'game_id': '1', 'player': '10', 'fouls': 2},
            {'game_id': '1', 'player': '11', 'fouls': 0},
            {'game_id': '1', 'player': '12', 'fouls': None},
            {'game_id': '2', 'player': '13', 'fouls': 1},
            {'game_id': '3', 'player': '14', 'fouls': 0},
        ])
        keys = box[['game_id', 'player']]
        rows, coverage = response.historical_fouls(events, box, keys)
        rows = rows.set_index(['game_id', 'player'])
        self.assertEqual(rows.loc[('1', '10'), 'q3_fouls'], 1)
        self.assertEqual(rows.loc[('1', '11'), 'foul_state'], 'under_four')
        self.assertEqual(rows.loc[('1', '12'), 'foul_state'], 'unknown')
        self.assertEqual(rows.loc[('2', '13'), 'foul_state'], 'unknown')
        self.assertEqual(rows.loc[('3', '14'), 'foul_state'], 'unknown')
        self.assertEqual(coverage['games_without_all_q1_q3_periods'], ['3'])
        self.assertEqual(coverage['games_with_unidentified_personal_fouler'], ['2'])

    def test_partial_count_above_final_box_is_reported_not_used(self):
        events = pd.DataFrame([
            {'game_id': '1', 'period_number': period, 'type_text': 'personal foul', 'athlete_id_1': 10}
            for period in (1, 2, 3)
        ])
        box = pd.DataFrame([{'game_id': '1', 'player': '10', 'fouls': 1}])
        rows, coverage = response.historical_fouls(events, box, box[['game_id', 'player']])
        self.assertEqual(rows.loc[0, 'foul_state'], 'unknown')
        self.assertTrue(pd.isna(rows.loc[0, 'q3_fouls']))
        self.assertEqual(coverage['partial_count_exceeds_final_box'], 1)


if __name__ == '__main__':
    unittest.main()
