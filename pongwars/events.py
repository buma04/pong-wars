from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto


class EventType(Enum):
    BALL_BOUNDARY_COLLISION = auto()
    BALL_WALL_COLLISION = auto()
    BALL_BALL_COLLISION = auto()
    BALL_DAMAGE = auto()
    BALL_ELIMINATION_CHECK = auto()


@dataclass(slots=True)
class GameEvent:
    type: EventType
    a_id: int
    b_id: int | None = None
    normal: tuple[float, float] = (0.0, 0.0)
    penetration: float = 0.0
    wall_cell: tuple[int, int] | None = None
