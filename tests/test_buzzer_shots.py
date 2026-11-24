import copy
import unittest
import numpy as np
from scripts.buzzer_shots import BuzzerShots
from scripts import nodes


def fixture():
    return {'kind': 'b1-buzzer-shots-v1', 'train_through': '2025-12-31', 'latest_training_date': '2025-12-30',
            'geometry': {'distance': [45.] * 100, 'lateral': [20.] * 100},
            'routing': {'start_clock_max': 4, 'action_clock_max': 2,
                        'start_types': ['made_fg', 'made_ft', 'dreb'],
                        'cells': {'inbound': {'probability': 1.}, 'change': {'probability': 0.}}},
            'conversion': {'probability': 1.}}


class BuzzerShotsTests(unittest.TestCase):
    def test_routing_respects_clock_possession_and_shot_opportunity(self):
        policy = BuzzerShots(fixture())
        policy.begin('2026-01-01', 7)
        context = {'start_clock': np.array([3, 5, 4, 3, 3, 3, 3.]),
                   'shot_time': np.array([2, 4, 1, 2, 2, 2, 2.]),
                   'start_code': np.array([nodes.START_TYPES.index(x) for x in
                                         ['made_fg', 'made_fg', 'made_fg', 'oreb', 'made_fg', 'dreb', 'made_ft']])}
        what = np.array([1, 1, 1, 1, 5, 1, -1])
        np.testing.assert_array_equal(policy.select(context, what), [True, False, False, False, False, False, False])
        bands, distance, lateral = policy.locations(np.array([0, 1, 2]), np.array([4, 5, 6]),
                                                     np.array([2., 3., 4.]), np.array([0., 1., 2.]))
        np.testing.assert_array_equal(bands, [20, 5, 6])
        np.testing.assert_array_equal(distance, [45., 3., 4.])
        np.testing.assert_array_equal(lateral, [20., 1., 2.])
        np.testing.assert_array_equal(policy.results(np.array([0, 1, 2]), np.array([0, 2, 0])), [1, 2, 0])
        self.assertEqual(policy.counts, {'eligible_shots': 2, 'routed_long_shots': 1, 'long_makes': 1})

    def test_no_activation_consumes_no_random_draws_and_seed_repeats(self):
        policy = BuzzerShots(fixture())
        context = {'start_clock': np.array([12.]), 'shot_time': np.array([1.]),
                   'start_code': np.array([nodes.START_TYPES.index('made_fg')])}
        policy.begin('2026-01-01', 123)
        before = copy.deepcopy(policy.rng.bit_generator.state)
        self.assertFalse(policy.select(context, np.array([0])).any())
        self.assertEqual(before, policy.rng.bit_generator.state)
        policy.results(np.array([0]), np.array([1]))
        self.assertEqual(before, policy.rng.bit_generator.state)
        policy.begin('2026-01-01', 123)
        self.assertEqual(before, policy.rng.bit_generator.state)

    def test_cutoffs_and_invalid_geometry_fail(self):
        policy = BuzzerShots(fixture())
        with self.assertRaises(ValueError):
            policy.begin('2025-12-31', 1)
        recipe = fixture()
        recipe['latest_training_date'] = '2026-01-01'
        with self.assertRaises(ValueError):
            BuzzerShots(recipe)
        recipe = fixture()
        recipe['geometry']['distance'][0] = 30
        with self.assertRaises(ValueError):
            BuzzerShots(recipe)


if __name__ == '__main__':
    unittest.main()
