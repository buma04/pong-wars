from __future__ import annotations

import math

import pygame

from pongwars.entities import Ball


def reflect(vx: float, vy: float, nx: float, ny: float) -> tuple[float, float]:
    projection = vx * nx + vy * ny
    return vx - 2.0 * projection * nx, vy - 2.0 * projection * ny


def wall_rect_from_cell(cell: tuple[int, int], block_size: int) -> pygame.Rect:
    return pygame.Rect(cell[0] * block_size, cell[1] * block_size, block_size, block_size)


def circle_rect_collision(ball: Ball, rect: pygame.Rect) -> tuple[float, float, float] | None:
    closest_x = max(rect.left, min(ball.x, rect.right))
    closest_y = max(rect.top, min(ball.y, rect.bottom))
    dx = ball.x - closest_x
    dy = ball.y - closest_y
    dist_sq = dx * dx + dy * dy
    radius_sq = ball.radius * ball.radius

    if dist_sq > radius_sq:
        return None

    if dist_sq > 1e-9:
        dist = math.sqrt(dist_sq)
        nx = dx / dist
        ny = dy / dist
        penetration = ball.radius - dist
        return nx, ny, penetration

    left = ball.x - rect.left
    right = rect.right - ball.x
    top = ball.y - rect.top
    bottom = rect.bottom - ball.y
    closest = min(left, right, top, bottom)

    if closest == left:
        return -1.0, 0.0, ball.radius + left
    if closest == right:
        return 1.0, 0.0, ball.radius + right
    if closest == top:
        return 0.0, -1.0, ball.radius + top
    return 0.0, 1.0, ball.radius + bottom
