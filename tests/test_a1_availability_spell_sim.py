import unittest

import numpy as np
import pandas as pd

from scripts import a1_availability_spell_sim as spells


def transition(player, prior, target, prior_day, target_day, outcome, status='dnp', duration=1):
    return {
        'season': 2025, 'team': '7', 'player': player, 'prior_game_id': prior, 'game_id': target,
        'prior_day': prior_day, 'date_et': target_day, 'cohort': 'return', 'outcome': outcome,
        'next_status': status, 'prior_reason': 'coach', 'prior_duration': duration, 'prior_role': 'bench',
    }


class SpellSimulationTests(unittest.TestCase):
    def test_build_episodes_censors_unknown_and_fold_end_without_counting_them_as_returns(self):
        rows = [
            transition('a', '1', '2', '2026-01-01', '2026-01-03', 0),
            transition('a', '2', '3', '2026-01-03', '2026-01-05', 0, duration=2),
            transition('a', '3', '4', '2026-01-05', '2026-01-07', 1, 'play', duration=3),
            transition('b', '1', '2', '2026-01-01', '2026-01-03', 0),
            transition('b', '2', '3', '2026-01-03', '2026-01-05', np.nan, 'unlisted', duration=2),
            transition('c', '1', '2', '2026-01-01', '2026-01-03', 1, 'play'),
            transition('d', '5', '6', '2026-04-28', '2026-04-30', 0),
            transition('d', '6', '7', '2026-04-30', '2026-05-02', 1, 'play', duration=2),
        ]
        games = pd.DataFrame([
            {'game_id': '2', 'date_et': '2026-01-03'}, {'game_id': '6', 'date_et': '2026-04-30'},
            *[{'game_id': f'extra{i}', 'date_et': '2026-01-02'} for i in range(198)],
        ])
        episodes = spells.build_episodes(pd.DataFrame(rows), 'F4', games).set_index('player')

        self.assertEqual((episodes.loc['a', 'observed_steps'], episodes.loc['a', 'return_step']), (3, 3))
        self.assertEqual((episodes.loc['b', 'observed_steps'], episodes.loc['b', 'return_step']), (1, 0))
        self.assertEqual(episodes.loc['b', 'censor_reason'], 'unlisted')
        self.assertEqual((episodes.loc['c', 'observed_steps'], episodes.loc['c', 'return_step']), (1, 1))
        self.assertEqual((episodes.loc['d', 'observed_steps'], episodes.loc['d', 'return_step']), (1, 0))
        self.assertEqual(episodes.loc['d', 'censor_reason'], 'fold_end_or_season_end')

    def test_simulation_is_seeded_and_matches_the_fixed_half_return_hazard(self):
        train = pd.DataFrame([
            {'prior_reason': 'coach', 'duration_bin': duration, 'outcome': outcome}
            for duration in ['1', '2-3', '4+'] for outcome in [0, 1]
        ])
        episodes = pd.DataFrame([{'prior_reason': 'coach'}])
        first = spells.add_predictions(train, episodes, 'F4')
        second = spells.add_predictions(train, episodes, 'F4')
        pd.testing.assert_frame_equal(first, second)
        for step in range(1, 6):
            self.assertAlmostEqual(first.loc[0, f'candidate_survival_{step}'], 0.5 ** step)
            self.assertLess(abs(first.loc[0, f'candidate_sim_survival_{step}'] - 0.5 ** step), 0.02)

    def test_unsupported_subgroup_with_empty_bootstrap_draw_stays_inconclusive(self):
        row = {'game_id': 'one', 'observed_steps': 1, 'return_step': 1, 'censor_reason': None}
        for step in range(1, 6):
            for name in ('baseline', 'candidate'):
                row[f'{name}_survival_{step}'] = 0.5 ** step
                row[f'{name}_sim_survival_{step}'] = 0.5 ** step
        ids = ['one'] + [f'other{i}' for i in range(199)]
        weights = np.zeros((2, 200), dtype=np.int64)
        weights[0, 0] = 1
        weights[0, 1] = 199
        weights[1, 1] = 200
        result = spells.summarize(pd.DataFrame([row]), ids, weights)
        self.assertEqual(result['status'], 'insufficient_sample')
        self.assertEqual(result['horizons'][0]['recorded_games_missed_at_least'], 2)
        self.assertIsNone(result['horizons'][0]['observed_survival_ci_95'])
        self.assertIsNone(result['horizons'][1]['observed_survival'])


if __name__ == '__main__':
    unittest.main()
