from __future__ import annotations

import math
from dataclasses import dataclass, field

from pongwars.entities import Ball


@dataclass(slots=True)
class MotionCache:
    normalized_direction: tuple[float, float] = (0.0, 0.0)
    speed: float = 0.0
    predicted_next_position: tuple[float, float] = (0.0, 0.0)
    planned_dt: float = 0.0
    validity_steps: int = 0
    dirty: bool = True
    version: int = 0
    cached_candidate_ids: tuple[int, ...] = ()
    candidate_validity_steps: int = 0


@dataclass(slots=True)
class BallRuntimeState:
    motion: MotionCache = field(default_factory=MotionCache)


def build_motion_cache(ball: Ball, dt: float, validity_steps: int) -> MotionCache:
    speed = ball.speed()
    if speed > 1e-9:
        direction = (ball.vx / speed, ball.vy / speed)
    else:
        direction = (0.0, 0.0)

    next_position = (ball.x + ball.vx * dt, ball.y + ball.vy * dt)

    return MotionCache(
        normalized_direction=direction,
        speed=speed,
        predicted_next_position=next_position,
        planned_dt=dt,
        validity_steps=max(1, validity_steps),
        dirty=False,
        version=0,
        cached_candidate_ids=(),
        candidate_validity_steps=0,
    )


def refresh_motion_plan(ball: Ball, cache: MotionCache, dt: float, validity_steps: int) -> None:
    speed = ball.speed()
    if speed > 1e-9:
        direction = (ball.vx / speed, ball.vy / speed)
    else:
        direction = (0.0, 0.0)

    cache.normalized_direction = direction
    cache.speed = speed
    cache.predicted_next_position = (ball.x + ball.vx * dt, ball.y + ball.vy * dt)
    cache.planned_dt = dt
    cache.validity_steps = max(1, validity_steps)
    cache.dirty = False


def consume_motion_plan(
    ball: Ball,
    cache: MotionCache,
    dt: float,
    dt_tolerance: float,
    validity_steps: int,
) -> bool:
    if cache.dirty:
        return False

    if cache.validity_steps <= 0:
        return False

    if math.fabs(cache.planned_dt - dt) > dt_tolerance:
        return False

    ball.x, ball.y = cache.predicted_next_position
    cache.validity_steps -= 1

    if cache.validity_steps > 0:
        cache.predicted_next_position = (ball.x + ball.vx * dt, ball.y + ball.vy * dt)
    else:
        cache.dirty = True

    return True


def invalidate_motion(cache: MotionCache) -> None:
    cache.dirty = True
    cache.validity_steps = 0
    cache.version += 1


def set_candidate_cache(cache: MotionCache, candidate_ids: tuple[int, ...], validity_steps: int) -> None:
    cache.cached_candidate_ids = candidate_ids
    cache.candidate_validity_steps = max(0, validity_steps)


def consume_candidate_cache(cache: MotionCache) -> tuple[int, ...] | None:
    if cache.candidate_validity_steps <= 0:
        return None

    cache.candidate_validity_steps -= 1
    return cache.cached_candidate_ids


def invalidate_candidate_cache(cache: MotionCache) -> None:
    cache.cached_candidate_ids = ()
    cache.candidate_validity_steps = 0
