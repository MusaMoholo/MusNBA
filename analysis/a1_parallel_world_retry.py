"""Research-only bounded parallel coordinator for independently seeded worlds."""
from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import Executor, Future
from typing import TypeVar

from scripts.a1_world_retry import Rejection, RecoverableWorldError, RetryLimitExceeded, RetryResult
from scripts.projection import seed_for

T = TypeVar('T')


def simulate_parallel(simulate: Callable[[int, int, int], T], executor: Executor, *,
                      worlds: int, seed: int, attempts_per_world: int,
                      max_rejections: int, window: int) -> RetryResult[T]:
    """Run a bounded window of first attempts; consume worlds and retry failures in serial order."""
    for name, value, minimum in (('worlds', worlds, 1), ('attempts_per_world', attempts_per_world, 1),
                                  ('max_rejections', max_rejections, 0), ('window', window, 1)):
        if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
            raise ValueError(f'{name} must be an integer >= {minimum}')
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise ValueError('seed must be an integer')

    def submit(world: int, attempt: int) -> tuple[int, Future[T]]:
        attempt_seed = seed_for('a1-isolated-world-v1', seed, world, attempt)
        return attempt_seed, executor.submit(simulate, world, attempt, attempt_seed)

    accepted: list[T] = []
    seeds: list[int] = []
    rejected: list[Rejection] = []
    for start in range(0, worlds, window):
        batch = [(world, *submit(world, 0)) for world in range(start, min(start + window, worlds))]
        for _, _, future in batch:
            error = future.exception()
            if error is not None and not isinstance(error, RecoverableWorldError):
                raise error
        for world, attempt_seed, future in batch:
            for attempt in range(attempts_per_world):
                try:
                    result = future.result()
                except RecoverableWorldError as exc:
                    reason = str(exc)
                    if not reason:
                        raise ValueError('recoverable world failures require an explicit reason') from exc
                    rejected.append(Rejection(world, attempt, attempt_seed, reason))
                    if len(rejected) > max_rejections or attempt + 1 == attempts_per_world:
                        raise RetryLimitExceeded(
                            f'isolated world retry limit exceeded after {len(rejected)} rejected attempts',
                            tuple(rejected),
                        ) from exc
                    attempt_seed, future = submit(world, attempt + 1)
                else:
                    accepted.append(result)
                    seeds.append(attempt_seed)
                    break
    return RetryResult(tuple(accepted), tuple(seeds), tuple(rejected))
