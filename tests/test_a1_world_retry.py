import unittest

import numpy as np

from scripts.a1_world_retry import RecoverableWorldError, RetryLimitExceeded, simulate_isolated


class IsolatedWorldRetryTests(unittest.TestCase):
    def run_worlds(self, failures=()):
        def simulate(world, attempt, seed):
            if (world, attempt) in failures:
                raise RecoverableWorldError('isolated test failure')
            return int(np.random.default_rng(seed).integers(1_000_000))

        return simulate_isolated(simulate, worlds=5, seed=77, attempts_per_world=3, max_rejections=3)

    def test_retry_replaces_only_the_failed_world_and_is_reproducible(self):
        control = self.run_worlds()
        retry = self.run_worlds({(2, 0)})
        self.assertEqual(retry, self.run_worlds({(2, 0)}))
        self.assertEqual(len(retry.worlds), 5)
        self.assertEqual(retry.worlds[:2], control.worlds[:2])
        self.assertEqual(retry.worlds[3:], control.worlds[3:])
        self.assertEqual(retry.accepted_seeds[:2], control.accepted_seeds[:2])
        self.assertEqual(retry.accepted_seeds[3:], control.accepted_seeds[3:])
        self.assertNotEqual(retry.accepted_seeds[2], control.accepted_seeds[2])
        self.assertEqual((retry.rejections[0].world, retry.rejections[0].attempt), (2, 0))
        self.assertEqual(retry.rejections[0].reason, 'isolated test failure')

    def test_per_world_and_total_retry_caps_include_rejection_evidence(self):
        def fail(world, attempt, seed):
            raise RecoverableWorldError('roster exhausted')

        for per_world, total, expected in ((2, 9, 2), (9, 1, 2), (9, 0, 1)):
            with self.subTest(per_world=per_world, total=total):
                with self.assertRaises(RetryLimitExceeded) as error:
                    simulate_isolated(fail, worlds=5, seed=1, attempts_per_world=per_world,
                                      max_rejections=total)
                self.assertEqual(len(error.exception.rejections), expected)
                self.assertTrue(all(r.reason == 'roster exhausted' for r in error.exception.rejections))

    def test_unknown_errors_and_unlabelled_rejections_fail_immediately(self):
        def broken(world, attempt, seed):
            raise ValueError('corrupt input')

        with self.assertRaisesRegex(ValueError, 'corrupt input'):
            simulate_isolated(broken, worlds=1, seed=0, attempts_per_world=3, max_rejections=3)

        def unlabelled(world, attempt, seed):
            raise RecoverableWorldError()

        with self.assertRaisesRegex(ValueError, 'explicit reason'):
            simulate_isolated(unlabelled, worlds=1, seed=0, attempts_per_world=3, max_rejections=3)
        for kwargs in ({'worlds': 0, 'attempts_per_world': 1, 'max_rejections': 0},
                       {'worlds': 1, 'attempts_per_world': 0, 'max_rejections': 0},
                       {'worlds': 1, 'attempts_per_world': 1, 'max_rejections': -1}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                simulate_isolated(lambda *_: 1, seed=0, **kwargs)
        with self.assertRaisesRegex(ValueError, 'seed'):
            simulate_isolated(lambda *_: 1, worlds=1, seed=True, attempts_per_world=1, max_rejections=0)


if __name__ == '__main__':
    unittest.main()
