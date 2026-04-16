from __future__ import annotations

import math
import random

from pongwars.config import GameConfig
from pongwars.entities import Ball, Team
from pongwars.walls import is_spawn_valid


def spawn_balls(cfg: GameConfig, walls: set[tuple[int, int]]) -> list[Ball]:
    balls: list[Ball] = []
    next_id = 1
    radius = cfg.ball_radius

    left_min = radius + 2
    left_max = max(left_min + 1, cfg.map_width * 0.45 - radius - 2)
    right_min = min(cfg.map_width - radius - 2, cfg.map_width * 0.55 + radius + 2)
    right_max = cfg.map_width - radius - 2

    for team in (Team.DAY, Team.NIGHT):
        for _ in range(cfg.balls_per_team):
            x = cfg.map_width / 2
            y = cfg.map_height / 2

            for _attempt in range(1200):
                if team == Team.DAY and left_max > left_min:
                    x = random.uniform(left_min, left_max)
                elif team == Team.NIGHT and right_max > right_min:
                    x = random.uniform(right_min, right_max)
                else:
                    x = random.uniform(radius + 2, cfg.map_width - radius - 2)

                y = random.uniform(radius + 2, cfg.map_height - radius - 2)
                if is_spawn_valid(x, y, radius, balls, walls, cfg.wall_block_size):
                    break

            angle = random.uniform(-math.pi * 0.35, math.pi * 0.35)
            direction = 1.0 if team == Team.DAY else -1.0
            vx = direction * cfg.initial_speed * math.cos(angle)
            vy = cfg.initial_speed * math.sin(angle)

            balls.append(
                Ball(
                    id=next_id,
                    team=team,
                    x=x,
                    y=y,
                    vx=vx,
                    vy=vy,
                    radius=radius,
                    health=cfg.initial_health,
                )
            )
            next_id += 1

    return balls
