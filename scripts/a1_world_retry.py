"""Research-only isolated-world retry coordinator; not connected to the engine or nightly."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Generic, TypeVar

from scripts.projection import seed_for

T = TypeVar('T')


class RecoverableWorldError(Exception):
    """Explicitly classified world-local failure; callers must not use this for input or accounting errors."""


@dataclass(frozen=True)
class Rejection:
    world: int
    attempt: int
    seed: int
    reason: str


class RetryLimitExceeded(RuntimeError):
    def __init__(self, message: str, rejections: tuple[Rejection, ...]) -> None:
        super().__init__(message)
        self.rejections = rejections


@dataclass(frozen=True)
class RetryResult(Generic[T]):
    worlds: tuple[T, ...]
    accepted_seeds: tuple[int, ...]
    rejections: tuple[Rejection, ...]


def simulate_isolated(simulate: Callable[[int, int, int], T], *, worlds: int, seed: int,
                      attempts_per_world: int, max_rejections: int) -> RetryResult[T]:
    """Run separately seeded single-world attempts; retry only explicitly classified local failures.

    The callback must independently validate a successful world and surface all other errors. Different
    per-world seeds do not reproduce the existing vectorized engine's coupled random streams.
    """
    for name, value, minimum in (('worlds', worlds, 1), ('attempts_per_world', attempts_per_world, 1),
                                  ('max_rejections', max_rejections, 0)):
        if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
            raise ValueError(f'{name} must be an integer >= {minimum}')
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise ValueError('seed must be an integer')
    accepted: list[T] = []
    seeds: list[int] = []
    rejected: list[Rejection] = []
    for world in range(worlds):
        for attempt in range(attempts_per_world):
            attempt_seed = seed_for('a1-isolated-world-v1', seed, world, attempt)
            try:
                result = simulate(world, attempt, attempt_seed)
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
            else:
                accepted.append(result)
                seeds.append(attempt_seed)
                break
    return RetryResult(tuple(accepted), tuple(seeds), tuple(rejected))
