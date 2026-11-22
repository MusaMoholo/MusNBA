import unittest

import numpy as np

from scripts import a1_availability_starter_audit as audit, a1_availability_starter_sim as starters


class StarterSimulationTests(unittest.TestCase):
    def test_seeded_worlds_preserve_fives_and_do_not_activate_missing_positions(self):
        states = [{'start_share': 1 - i / 10, 'priority': 10 - i} for i in range(6)]
        positions = ['G', 'G', 'F', 'F', 'C', None]
        probability = np.array([1., 1., 1., 1., 1., 0.5])
        first, lineups = starters.simulate(states, positions, probability, seed=7, worlds=1000)
        again, other_lineups = starters.simulate(states, positions, probability, seed=7, worlds=1000)
        self.assertEqual((first, lineups), (again, other_lineups))
        self.assertEqual(first['worlds'], 1000)
        self.assertEqual(first['supported_worlds'] + first['unknown_active_position'], 1000)
        self.assertGreater(first['unknown_active_position'], 0)
        self.assertEqual(set(lineups), {(0, 1, 2, 3, 4)})
        self.assertEqual(sum(lineups.values()), first['supported_worlds'])

    def test_fewer_than_five_active_is_unsupported(self):
        states = [{'start_share': 0.5, 'priority': 1.0} for _ in range(5)]
        result, lineups = starters.simulate(states, ['G', 'G', 'F', 'F', 'C'],
                                            np.array([1., 1., 1., 1., 0.]), seed=7, worlds=50)
        self.assertEqual(result['fewer_than_five_active'], 50)
        self.assertEqual(result['supported_worlds'], 0)
        self.assertFalse(lineups)

    def test_invalid_probabilities_are_rejected(self):
        with self.assertRaisesRegex(ValueError, 'invalid'):
            starters.simulate([{}], ['G'], np.array([1.1]), seed=7)

    def test_independent_world_replay_matches_mask_compression_and_position_fallback(self):
        states = [{'start_share': 1 - i / 10, 'priority': 10 - i} for i in range(8)]
        positions = ['G', 'G', 'G', 'G', 'F', 'C', None, 'F']
        probability = np.array([1., 1., 1., 1., 1., 0.6, 0.2, 0.5])
        summary, lineups = starters.simulate(states, positions, probability, seed=9, worlds=1000)
        replay, counts, identities = audit.independent_worlds(states, positions, probability, seed=9, worlds=1000)
        self.assertEqual(summary, replay)
        self.assertEqual(lineups, identities)
        self.assertEqual(int(counts.sum()), 5 * summary['supported_worlds'])


if __name__ == '__main__':
    unittest.main()
