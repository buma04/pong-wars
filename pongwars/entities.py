from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto


class Team(Enum):
    DAY = "day"
    NIGHT = "night"


class BallAction(Enum):
    NO_OP = auto()
    ACCELERATE = auto()
    DECELERATE = auto()
    TURN_LEFT = auto()
    TURN_RIGHT = auto()


@dataclass(slots=True)
class Ball:
    id: int
    team: Team
    x: float
    y: float
    vx: float
    vy: float
    radius: float
    health: float
    alive: bool = True
    last_action: BallAction = BallAction.NO_OP

    def speed(self) -> float:
        return math.hypot(self.vx, self.vy)

    def clamp_speed(self, min_speed: float, max_speed: float) -> None:
        speed = self.speed()
        if speed == 0.0:
            angle = random.uniform(0.0, math.tau)
            self.vx = math.cos(angle) * min_speed
            self.vy = math.sin(angle) * min_speed
            return

        target = min(max(speed, min_speed), max_speed)
        if not math.isclose(target, speed):
            scale = target / speed
            self.vx *= scale
            self.vy *= scale

    def apply_action(
        self,
        action: BallAction,
        dt: float,
        acceleration: float,
        turn_rate_deg: float,
        min_speed: float,
        max_speed: float,
    ) -> None:
        self.last_action = action
        if action == BallAction.NO_OP:
            return

        if action in (BallAction.TURN_LEFT, BallAction.TURN_RIGHT):
            direction = -1.0 if action == BallAction.TURN_LEFT else 1.0
            angle = math.radians(turn_rate_deg) * dt * direction
            cos_a = math.cos(angle)
            sin_a = math.sin(angle)
            vx, vy = self.vx, self.vy
            self.vx = vx * cos_a - vy * sin_a
            self.vy = vx * sin_a + vy * cos_a
        elif action in (BallAction.ACCELERATE, BallAction.DECELERATE):
            sign = 1.0 if action == BallAction.ACCELERATE else -1.0
            speed = self.speed()
            target = max(min_speed, speed + sign * acceleration * dt)
            if speed == 0.0:
                self.vx = target
                self.vy = 0.0
            else:
                scale = target / speed
                self.vx *= scale
                self.vy *= scale

        self.clamp_speed(min_speed, max_speed)

    def move(self, dt: float) -> None:
        self.x += self.vx * dt
        self.y += self.vy * dt
