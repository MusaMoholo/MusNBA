import unittest
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from functools import partial

from analysis.a1_parallel_world_retry import simulate_parallel
from scripts.a1_world_retry import RecoverableWorldError, RetryLimitExceeded, simulate_isolated


def sample(world, attempt, seed, *, failures=(), unknown=()):
    if (world, attempt) in unknown:
        raise ValueError('corrupt input')
    if (world, attempt) in failures:
        raise RecoverableWorldError(f'world {world} rejected')
    return (world, seed % 1_000_003)


class ParallelWorldRetryTests(unittest.TestCase):
    def test_equal_to_serial_across_windows_and_process_workers(self):
        callback = partial(sample, failures=((1, 0), (1, 1), (4, 0)))
        options = dict(worlds=8, seed=77, attempts_per_world=3, max_rejections=3)
        expected = simulate_isolated(callback, **options)
        for workers in (1, 2, 4):
            with self.subTest(workers=workers), ProcessPoolExecutor(max_workers=workers) as pool:
                self.assertEqual(simulate_parallel(callback, pool, window=workers, **options), expected)

    def test_caps_match_serial_rejection_order(self):
        callback = partial(sample, failures=((0, 0), (0, 1), (1, 0)))
        options = dict(worlds=3, seed=5, attempts_per_world=3, max_rejections=1)
        with self.assertRaises(RetryLimitExceeded) as serial:
            simulate_isolated(callback, **options)
        with ThreadPoolExecutor(max_workers=3) as pool, self.assertRaises(RetryLimitExceeded) as parallel:
            simulate_parallel(callback, pool, window=3, **options)
        self.assertEqual(parallel.exception.rejections, serial.exception.rejections)

    def test_speculative_unknown_error_is_not_hidden_by_earlier_cap(self):
        callback = partial(sample, failures=((0, 0),), unknown=((1, 0),))
        with ThreadPoolExecutor(max_workers=2) as pool, self.assertRaisesRegex(ValueError, 'corrupt input'):
            simulate_parallel(callback, pool, worlds=2, seed=1, attempts_per_world=1, max_rejections=0, window=2)

    def test_invalid_inputs_fail_explicitly(self):
        with ThreadPoolExecutor(max_workers=1) as pool:
            for changes in ({'window': 0}, {'worlds': False}, {'attempts_per_world': 0},
                            {'max_rejections': -1}, {'seed': True}):
                args = dict(worlds=1, seed=1, attempts_per_world=1, max_rejections=0, window=1)
                args.update(changes)
                with self.subTest(changes=changes), self.assertRaises(ValueError):
                    simulate_parallel(sample, pool, **args)


if __name__ == '__main__':
    unittest.main()
