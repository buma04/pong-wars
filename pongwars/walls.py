from __future__ import annotations

import random

from pongwars.config import GameConfig
from pongwars.entities import Ball, Team
from pongwars.physics import circle_rect_collision, wall_rect_from_cell


def generate_wall_blocks(cfg: GameConfig) -> set[tuple[int, int]]:
    cols = max(1, cfg.map_width // cfg.wall_block_size)
    rows = max(1, cfg.map_height // cfg.wall_block_size)
    blocks: set[tuple[int, int]] = set()

    if cfg.wall_blocks:
        for cell in cfg.wall_blocks:
            cx = int(cell[0])
            cy = int(cell[1])
            if 0 < cx < cols - 1 and 0 < cy < rows - 1:
                blocks.add((cx, cy))
        return blocks

    layout_type = cfg.wall_layout.type.lower()
    if layout_type == "none":
        return blocks

    if layout_type == "random":
        target_count = int(cfg.wall_layout.count)
        attempts = 0
        while len(blocks) < target_count and attempts < target_count * 40:
            attempts += 1
            cx = random.randint(1, max(1, cols - 2))
            cy = random.randint(1, max(1, rows - 2))
            blocks.add((cx, cy))
        return blocks

    center_x = cols // 2
    center_y = rows // 2
    arm_x = max(1, int((cols * cfg.wall_layout.arm_ratio) / 2.0))
    arm_y = max(1, int((rows * cfg.wall_layout.arm_ratio) / 2.0))

    for x in range(max(1, center_x - arm_x), min(cols - 1, center_x + arm_x + 1)):
        blocks.add((x, center_y))
    for y in range(max(1, center_y - arm_y), min(rows - 1, center_y + arm_y + 1)):
        blocks.add((center_x, y))

    return blocks


def is_spawn_valid(
    x: float,
    y: float,
    radius: float,
    existing: list[Ball],
    walls: set[tuple[int, int]],
    block_size: int,
) -> bool:
    for ball in existing:
        dx = x - ball.x
        dy = y - ball.y
        if dx * dx + dy * dy < (radius + ball.radius) ** 2:
            return False

    probe = Ball(
        id=-1,
        team=Team.DAY,
        x=x,
        y=y,
        vx=0.0,
        vy=0.0,
        radius=radius,
        health=1.0,
    )
    for cell in walls:
        rect = wall_rect_from_cell(cell, block_size)
        if circle_rect_collision(probe, rect):
            return False

    return True


def can_place_wall_at_cell(
    cell: tuple[int, int],
    walls: set[tuple[int, int]],
    balls: list[Ball],
    block_size: int,
    map_width: int,
    map_height: int,
    extra_margin: float,
) -> bool:
    if cell in walls:
        return False

    cols = max(1, map_width // block_size)
    rows = max(1, map_height // block_size)
    x_cell, y_cell = cell

    if not (0 < x_cell < cols - 1 and 0 < y_cell < rows - 1):
        return False

    rect = wall_rect_from_cell(cell, block_size)

    for ball in balls:
        if not ball.alive:
            continue
        inflated_probe = Ball(
            id=-1,
            team=ball.team,
            x=ball.x,
            y=ball.y,
            vx=0.0,
            vy=0.0,
            radius=ball.radius + max(0.0, extra_margin),
            health=1.0,
        )
        if circle_rect_collision(inflated_probe, rect):
            return False

    return True


def spawn_random_walls(
    walls: set[tuple[int, int]],
    balls: list[Ball],
    cfg: GameConfig,
) -> list[tuple[int, int]]:
    if not cfg.random_wall_spawn.enabled:
        return []

    if len(walls) >= cfg.random_wall_spawn.max_walls:
        return []

    cols = max(1, cfg.map_width // cfg.wall_block_size)
    rows = max(1, cfg.map_height // cfg.wall_block_size)

    spawned_cells: list[tuple[int, int]] = []
    max_new = min(
        cfg.random_wall_spawn.blocks_per_spawn,
        max(0, cfg.random_wall_spawn.max_walls - len(walls)),
    )

    for _ in range(max_new):
        placed = False
        for _attempt in range(cfg.random_wall_spawn.max_attempts_per_block):
            candidate = (
                random.randint(1, max(1, cols - 2)),
                random.randint(1, max(1, rows - 2)),
            )

            if not can_place_wall_at_cell(
                cell=candidate,
                walls=walls,
                balls=balls,
                block_size=cfg.wall_block_size,
                map_width=cfg.map_width,
                map_height=cfg.map_height,
                extra_margin=cfg.random_wall_spawn.avoid_ball_margin,
            ):
                continue

            walls.add(candidate)
            spawned_cells.append(candidate)
            placed = True
            break

        if not placed:
            break

    return spawned_cells
