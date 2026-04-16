from __future__ import annotations

from collections import defaultdict

from pongwars.entities import Ball


class SpatialHash:
    def __init__(self, cell_size: int) -> None:
        self.cell_size = max(8, cell_size)
        self.cells: dict[tuple[int, int], list[int]] = defaultdict(list)

    def clear(self) -> None:
        self.cells.clear()

    def rebuild(self, balls: list[Ball]) -> None:
        self.cells.clear()
        for ball in balls:
            if not ball.alive:
                continue
            key = self._cell(ball.x, ball.y)
            self.cells[key].append(ball.id)

    def nearby_ids(self, x: float, y: float) -> tuple[int, ...]:
        cx, cy = self._cell(x, y)
        candidates: list[int] = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                candidates.extend(self.cells.get((cx + dx, cy + dy), ()))
        return tuple(candidates)

    def _cell(self, x: float, y: float) -> tuple[int, int]:
        return int(x // self.cell_size), int(y // self.cell_size)
