from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class WallLayoutConfig:
    type: str = "cross"
    arm_ratio: float = 0.55
    count: int = 120


@dataclass(slots=True)
class RandomWallSpawnConfig:
    enabled: bool = True
    interval_sec: float = 2.5
    blocks_per_spawn: int = 3
    max_walls: int = 220
    max_attempts_per_block: int = 80
    avoid_ball_margin: float = 2.0


@dataclass(slots=True)
class GameConfig:
    map_width: int = 900
    map_height: int = 600
    fps: int = 120
    balls_per_team: int = 16
    ball_radius: float = 8.0
    initial_speed: float = 180.0
    min_speed: float = 80.0
    max_speed: float = 280.0
    initial_health: float = 100.0
    collision_damage: float = 20.0
    time_limit_sec: float = 90.0
    wall_block_size: int = 20
    wall_layout: WallLayoutConfig = field(default_factory=WallLayoutConfig)
    wall_blocks: list[tuple[int, int]] = field(default_factory=list)
    random_wall_spawn: RandomWallSpawnConfig = field(default_factory=RandomWallSpawnConfig)
    action_acceleration: float = 70.0
    action_turn_rate_deg: float = 120.0
    seed: int | None = None
    debug_event_log: bool = True

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GameConfig":
        defaults = cls()

        wall_layout_data = data.get("wall_layout", {})
        if not isinstance(wall_layout_data, dict):
            wall_layout_data = {}

        random_spawn_data = data.get("random_wall_spawn", {})
        if not isinstance(random_spawn_data, dict):
            random_spawn_data = {}

        raw_wall_blocks = data.get("wall_blocks", defaults.wall_blocks)
        parsed_wall_blocks: list[tuple[int, int]] = []
        if isinstance(raw_wall_blocks, list):
            for item in raw_wall_blocks:
                if isinstance(item, (list, tuple)) and len(item) == 2:
                    parsed_wall_blocks.append((int(item[0]), int(item[1])))

        raw_seed = data.get("seed", defaults.seed)
        parsed_seed = int(raw_seed) if raw_seed is not None else None

        return cls(
            map_width=int(data.get("map_width", defaults.map_width)),
            map_height=int(data.get("map_height", defaults.map_height)),
            fps=int(data.get("fps", defaults.fps)),
            balls_per_team=int(data.get("balls_per_team", defaults.balls_per_team)),
            ball_radius=float(data.get("ball_radius", defaults.ball_radius)),
            initial_speed=float(data.get("initial_speed", defaults.initial_speed)),
            min_speed=float(data.get("min_speed", defaults.min_speed)),
            max_speed=float(data.get("max_speed", defaults.max_speed)),
            initial_health=float(data.get("initial_health", defaults.initial_health)),
            collision_damage=float(data.get("collision_damage", defaults.collision_damage)),
            time_limit_sec=float(data.get("time_limit_sec", defaults.time_limit_sec)),
            wall_block_size=int(data.get("wall_block_size", defaults.wall_block_size)),
            wall_layout=WallLayoutConfig(
                type=str(wall_layout_data.get("type", defaults.wall_layout.type)),
                arm_ratio=float(wall_layout_data.get("arm_ratio", defaults.wall_layout.arm_ratio)),
                count=int(wall_layout_data.get("count", defaults.wall_layout.count)),
            ),
            wall_blocks=parsed_wall_blocks,
            random_wall_spawn=RandomWallSpawnConfig(
                enabled=bool(random_spawn_data.get("enabled", defaults.random_wall_spawn.enabled)),
                interval_sec=float(
                    random_spawn_data.get("interval_sec", defaults.random_wall_spawn.interval_sec)
                ),
                blocks_per_spawn=int(
                    random_spawn_data.get("blocks_per_spawn", defaults.random_wall_spawn.blocks_per_spawn)
                ),
                max_walls=int(random_spawn_data.get("max_walls", defaults.random_wall_spawn.max_walls)),
                max_attempts_per_block=int(
                    random_spawn_data.get(
                        "max_attempts_per_block",
                        defaults.random_wall_spawn.max_attempts_per_block,
                    )
                ),
                avoid_ball_margin=float(
                    random_spawn_data.get(
                        "avoid_ball_margin",
                        defaults.random_wall_spawn.avoid_ball_margin,
                    )
                ),
            ),
            action_acceleration=float(data.get("action_acceleration", defaults.action_acceleration)),
            action_turn_rate_deg=float(data.get("action_turn_rate_deg", defaults.action_turn_rate_deg)),
            seed=parsed_seed,
            debug_event_log=bool(data.get("debug_event_log", defaults.debug_event_log)),
        )


def load_config(path: Path) -> GameConfig:
    if not path.exists():
        return GameConfig()

    with path.open("r", encoding="utf-8") as file:
        raw_data = json.load(file)

    if not isinstance(raw_data, dict):
        return GameConfig()

    return GameConfig.from_dict(raw_data)
