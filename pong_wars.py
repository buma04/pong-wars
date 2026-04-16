import argparse
import json
import math
import random
from collections import deque
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Optional

import pygame

MYSTIC_MINT = (217, 232, 227)
NOCTURNAL_EXPEDITION = (23, 43, 54)
ARCTIC_POWDER = (241, 246, 244)
DEEP_SAFFRON = (255, 153, 50)
FORSYTHIA = (255, 200, 1)

DAY_BALL_COLOR = NOCTURNAL_EXPEDITION
NIGHT_BALL_COLOR = MYSTIC_MINT
WALL_COLOR = DEEP_SAFFRON
BACKGROUND_COLOR = ARCTIC_POWDER
HUD_TEXT_COLOR = NOCTURNAL_EXPEDITION


class Team(Enum):
    DAY = "day"
    NIGHT = "night"


class BallAction(Enum):
    NO_OP = auto()
    ACCELERATE = auto()
    DECELERATE = auto()
    TURN_LEFT = auto()
    TURN_RIGHT = auto()


class EventType(Enum):
    BALL_BOUNDARY_COLLISION = auto()
    BALL_WALL_COLLISION = auto()
    BALL_BALL_COLLISION = auto()
    BALL_DAMAGE = auto()
    BALL_ELIMINATION_CHECK = auto()


@dataclass
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
    wall_layout: dict = field(default_factory=lambda: {"type": "cross", "arm_ratio": 0.55, "count": 120})
    wall_blocks: list = field(default_factory=list)
    action_acceleration: float = 70.0
    action_turn_rate_deg: float = 120.0
    seed: Optional[int] = None
    debug_event_log: bool = True

    @classmethod
    def from_dict(cls, data: dict) -> "GameConfig":
        defaults = cls()
        wall_layout = data.get("wall_layout", defaults.wall_layout)
        wall_blocks = data.get("wall_blocks", defaults.wall_blocks)
        parsed_wall_blocks = []
        if isinstance(wall_blocks, list):
            for item in wall_blocks:
                if isinstance(item, (list, tuple)) and len(item) == 2:
                    parsed_wall_blocks.append((int(item[0]), int(item[1])))
        seed = data.get("seed", defaults.seed)
        parsed_seed = int(seed) if seed is not None else None

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
            wall_layout=dict(wall_layout) if isinstance(wall_layout, dict) else dict(defaults.wall_layout),
            wall_blocks=parsed_wall_blocks,
            action_acceleration=float(data.get("action_acceleration", defaults.action_acceleration)),
            action_turn_rate_deg=float(data.get("action_turn_rate_deg", defaults.action_turn_rate_deg)),
            seed=parsed_seed,
            debug_event_log=bool(data.get("debug_event_log", defaults.debug_event_log)),
        )


@dataclass
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
        if speed == 0:
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
            if speed == 0:
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


@dataclass
class GameEvent:
    type: EventType
    a_id: int
    b_id: Optional[int] = None
    normal: tuple[float, float] = (0.0, 0.0)
    penetration: float = 0.0
    wall_cell: Optional[tuple[int, int]] = None


def load_config(path: Path) -> GameConfig:
    if not path.exists():
        return GameConfig()
    with path.open("r", encoding="utf-8") as f:
        raw = json.load(f)
    return GameConfig.from_dict(raw)


def reflect(vx: float, vy: float, nx: float, ny: float) -> tuple[float, float]:
    projection = vx * nx + vy * ny
    return vx - 2.0 * projection * nx, vy - 2.0 * projection * ny


def wall_rect_from_cell(cell: tuple[int, int], block_size: int) -> pygame.Rect:
    return pygame.Rect(cell[0] * block_size, cell[1] * block_size, block_size, block_size)


def circle_rect_collision(ball: Ball, rect: pygame.Rect) -> Optional[tuple[float, float, float]]:
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
    probe_ball = Ball(-1, Team.DAY, x, y, 0.0, 0.0, radius, 1.0)
    for cell in walls:
        rect = wall_rect_from_cell(cell, block_size)
        if circle_rect_collision(probe_ball, rect):
            return False
    return True


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

    layout_type = str(cfg.wall_layout.get("type", "cross")).lower()
    if layout_type == "none":
        return blocks

    if layout_type == "random":
        count = int(cfg.wall_layout.get("count", max(10, cols * rows // 35)))
        attempts = 0
        while len(blocks) < count and attempts < count * 40:
            attempts += 1
            cx = random.randint(1, max(1, cols - 2))
            cy = random.randint(1, max(1, rows - 2))
            blocks.add((cx, cy))
        return blocks

    cx = cols // 2
    cy = rows // 2
    arm_ratio = float(cfg.wall_layout.get("arm_ratio", 0.55))
    arm_x = max(1, int((cols * arm_ratio) / 2.0))
    arm_y = max(1, int((rows * arm_ratio) / 2.0))

    for x in range(max(1, cx - arm_x), min(cols - 1, cx + arm_x + 1)):
        blocks.add((x, cy))
    for y in range(max(1, cy - arm_y), min(rows - 1, cy + arm_y + 1)):
        blocks.add((cx, y))
    return blocks


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


class PongWarsGame:
    def __init__(self, cfg: GameConfig) -> None:
        self.cfg = cfg
        if cfg.seed is not None:
            random.seed(cfg.seed)

        pygame.init()
        pygame.display.set_caption("Pong Wars - Queue Collision")
        self.screen = pygame.display.set_mode((cfg.map_width, cfg.map_height))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Consolas", 18)
        self.big_font = pygame.font.SysFont("Consolas", 40)

        self.wall_blocks = generate_wall_blocks(cfg)
        self.balls = spawn_balls(cfg, self.wall_blocks)
        self.ball_by_id = {ball.id: ball for ball in self.balls}
        self.events: deque[GameEvent] = deque()

        self.elapsed_sec = 0.0
        self.running = True
        self.finished = False
        self.winner_text = ""
        self.frame_logs: list[str] = []

    def get_ball(self, ball_id: int) -> Optional[Ball]:
        ball = self.ball_by_id.get(ball_id)
        if ball is None or not ball.alive:
            return None
        return ball

    def count_alive(self) -> tuple[int, int]:
        day_alive = 0
        night_alive = 0
        for ball in self.balls:
            if not ball.alive:
                continue
            if ball.team == Team.DAY:
                day_alive += 1
            else:
                night_alive += 1
        return day_alive, night_alive

    def run(self) -> None:
        while self.running:
            dt = self.clock.tick(self.cfg.fps) / 1000.0
            self.handle_system_events()
            if not self.finished:
                self.step(dt)
            self.render()
        pygame.quit()

    def handle_system_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.running = False

    def step(self, dt: float) -> None:
        self.elapsed_sec += dt
        alive_balls = [ball for ball in self.balls if ball.alive]

        for ball in alive_balls:
            ball.apply_action(
                BallAction.NO_OP,
                dt,
                self.cfg.action_acceleration,
                self.cfg.action_turn_rate_deg,
                self.cfg.min_speed,
                self.cfg.max_speed,
            )
            ball.move(dt)

        self.enqueue_boundary_events(alive_balls)
        self.enqueue_wall_events(alive_balls)
        self.enqueue_ball_events(alive_balls)
        self.process_event_queue()
        self.check_game_end()

    def enqueue_boundary_events(self, alive_balls: list[Ball]) -> None:
        for ball in alive_balls:
            if ball.x - ball.radius < 0:
                self.events.append(
                    GameEvent(
                        type=EventType.BALL_BOUNDARY_COLLISION,
                        a_id=ball.id,
                        normal=(1.0, 0.0),
                        penetration=-(ball.x - ball.radius),
                    )
                )
            elif ball.x + ball.radius > self.cfg.map_width:
                self.events.append(
                    GameEvent(
                        type=EventType.BALL_BOUNDARY_COLLISION,
                        a_id=ball.id,
                        normal=(-1.0, 0.0),
                        penetration=ball.x + ball.radius - self.cfg.map_width,
                    )
                )

            if ball.y - ball.radius < 0:
                self.events.append(
                    GameEvent(
                        type=EventType.BALL_BOUNDARY_COLLISION,
                        a_id=ball.id,
                        normal=(0.0, 1.0),
                        penetration=-(ball.y - ball.radius),
                    )
                )
            elif ball.y + ball.radius > self.cfg.map_height:
                self.events.append(
                    GameEvent(
                        type=EventType.BALL_BOUNDARY_COLLISION,
                        a_id=ball.id,
                        normal=(0.0, -1.0),
                        penetration=ball.y + ball.radius - self.cfg.map_height,
                    )
                )

    def enqueue_wall_events(self, alive_balls: list[Ball]) -> None:
        if not self.wall_blocks:
            return
        block_size = self.cfg.wall_block_size
        for ball in alive_balls:
            best_event: Optional[GameEvent] = None
            for cell in sorted(self.wall_blocks):
                rect = wall_rect_from_cell(cell, block_size)
                collision = circle_rect_collision(ball, rect)
                if not collision:
                    continue
                nx, ny, penetration = collision
                event = GameEvent(
                    type=EventType.BALL_WALL_COLLISION,
                    a_id=ball.id,
                    normal=(nx, ny),
                    penetration=penetration,
                    wall_cell=cell,
                )
                if best_event is None or event.penetration > best_event.penetration:
                    best_event = event
            if best_event is not None:
                self.events.append(best_event)

    def enqueue_ball_events(self, alive_balls: list[Ball]) -> None:
        for i in range(len(alive_balls)):
            a = alive_balls[i]
            for j in range(i + 1, len(alive_balls)):
                b = alive_balls[j]
                dx = b.x - a.x
                dy = b.y - a.y
                radius_sum = a.radius + b.radius
                dist_sq = dx * dx + dy * dy
                if dist_sq > radius_sum * radius_sum:
                    continue

                if dist_sq > 1e-9:
                    dist = math.sqrt(dist_sq)
                    nx = dx / dist
                    ny = dy / dist
                    penetration = radius_sum - dist
                else:
                    rvx = a.vx - b.vx
                    rvy = a.vy - b.vy
                    rv_norm = math.hypot(rvx, rvy)
                    if rv_norm > 1e-9:
                        nx = rvx / rv_norm
                        ny = rvy / rv_norm
                    else:
                        nx, ny = 1.0, 0.0
                    penetration = radius_sum

                self.events.append(
                    GameEvent(
                        type=EventType.BALL_BALL_COLLISION,
                        a_id=a.id,
                        b_id=b.id,
                        normal=(nx, ny),
                        penetration=penetration,
                    )
                )
                self.events.append(GameEvent(type=EventType.BALL_DAMAGE, a_id=a.id, b_id=b.id))
                self.events.append(GameEvent(type=EventType.BALL_ELIMINATION_CHECK, a_id=a.id, b_id=b.id))

    def process_event_queue(self) -> None:
        self.frame_logs.clear()
        while self.events:
            event = self.events.popleft()
            if event.type == EventType.BALL_BOUNDARY_COLLISION:
                self.handle_boundary_collision(event)
            elif event.type == EventType.BALL_WALL_COLLISION:
                self.handle_wall_collision(event)
            elif event.type == EventType.BALL_BALL_COLLISION:
                self.handle_ball_collision(event)
            elif event.type == EventType.BALL_DAMAGE:
                self.handle_ball_damage(event)
            elif event.type == EventType.BALL_ELIMINATION_CHECK:
                self.handle_ball_elimination(event)

    def log_event(self, message: str) -> None:
        if not self.cfg.debug_event_log:
            return
        if len(self.frame_logs) < 20:
            self.frame_logs.append(message)

    def handle_boundary_collision(self, event: GameEvent) -> None:
        ball = self.get_ball(event.a_id)
        if ball is None:
            return
        nx, ny = event.normal
        ball.vx, ball.vy = reflect(ball.vx, ball.vy, nx, ny)
        correction = max(0.0, event.penetration) + 0.5
        ball.x += nx * correction
        ball.y += ny * correction
        ball.clamp_speed(self.cfg.min_speed, self.cfg.max_speed)
        self.log_event(f"boundary b{ball.id}")

    def handle_wall_collision(self, event: GameEvent) -> None:
        ball = self.get_ball(event.a_id)
        if ball is None:
            return
        if event.wall_cell is None or event.wall_cell not in self.wall_blocks:
            return
        nx, ny = event.normal
        ball.vx, ball.vy = reflect(ball.vx, ball.vy, nx, ny)
        correction = max(0.0, event.penetration) + 0.5
        ball.x += nx * correction
        ball.y += ny * correction
        ball.clamp_speed(self.cfg.min_speed, self.cfg.max_speed)
        self.wall_blocks.discard(event.wall_cell)
        self.log_event(f"wall b{ball.id} cell{event.wall_cell}")

    def handle_ball_collision(self, event: GameEvent) -> None:
        a = self.get_ball(event.a_id)
        b = self.get_ball(event.b_id) if event.b_id is not None else None
        if a is None or b is None:
            return
        nx, ny = event.normal

        relative_projection = (a.vx - b.vx) * nx + (a.vy - b.vy) * ny
        if relative_projection > 0:
            a.vx -= relative_projection * nx
            a.vy -= relative_projection * ny
            b.vx += relative_projection * nx
            b.vy += relative_projection * ny

        correction = max(0.0, event.penetration) * 0.5 + 0.1
        a.x -= nx * correction
        a.y -= ny * correction
        b.x += nx * correction
        b.y += ny * correction

        a.clamp_speed(self.cfg.min_speed, self.cfg.max_speed)
        b.clamp_speed(self.cfg.min_speed, self.cfg.max_speed)
        self.log_event(f"ball-hit b{a.id}-b{b.id}")

    def handle_ball_damage(self, event: GameEvent) -> None:
        a = self.get_ball(event.a_id)
        b = self.get_ball(event.b_id) if event.b_id is not None else None
        if a is None or b is None:
            return
        a.health = max(0.0, a.health - self.cfg.collision_damage)
        b.health = max(0.0, b.health - self.cfg.collision_damage)
        self.log_event(f"damage b{a.id}:{a.health:.0f} b{b.id}:{b.health:.0f}")

    def handle_ball_elimination(self, event: GameEvent) -> None:
        a = self.get_ball(event.a_id)
        b = self.get_ball(event.b_id) if event.b_id is not None else None
        if a is None or b is None:
            return

        if a.health <= 0:
            a.alive = False
        if b.health <= 0:
            b.alive = False

        if not a.alive or not b.alive:
            self.log_event(f"eliminate hp<=0 b{event.a_id}-b{event.b_id}")
            return

        if a.health < b.health:
            a.alive = False
            self.log_event(f"eliminate lower hp b{a.id}")
        elif b.health < a.health:
            b.alive = False
            self.log_event(f"eliminate lower hp b{b.id}")

    def check_game_end(self) -> None:
        day_alive, night_alive = self.count_alive()
        total_alive = day_alive + night_alive

        if total_alive <= 1:
            self.finished = True
            if day_alive > night_alive:
                self.winner_text = "DAY wins"
            elif night_alive > day_alive:
                self.winner_text = "NIGHT wins"
            else:
                self.winner_text = "DRAW"
            return

        if day_alive == 0 or night_alive == 0:
            self.finished = True
            self.winner_text = "DAY wins" if day_alive > night_alive else "NIGHT wins"
            return

        if self.elapsed_sec >= self.cfg.time_limit_sec:
            self.finished = True
            if day_alive > night_alive:
                self.winner_text = "DAY wins by timeout"
            elif night_alive > day_alive:
                self.winner_text = "NIGHT wins by timeout"
            else:
                self.winner_text = "DRAW by timeout"

    def render(self) -> None:
        self.screen.fill(BACKGROUND_COLOR)

        block_size = self.cfg.wall_block_size
        for cell in self.wall_blocks:
            pygame.draw.rect(self.screen, WALL_COLOR, wall_rect_from_cell(cell, block_size))

        for ball in self.balls:
            if not ball.alive:
                continue
            color = DAY_BALL_COLOR if ball.team == Team.DAY else NIGHT_BALL_COLOR
            pygame.draw.circle(self.screen, color, (int(ball.x), int(ball.y)), int(ball.radius))

        day_alive, night_alive = self.count_alive()
        time_left = max(0.0, self.cfg.time_limit_sec - self.elapsed_sec)
        hud = f"time {time_left:05.1f}s | day {day_alive} | night {night_alive} | walls {len(self.wall_blocks)}"
        hud_surface = self.font.render(hud, True, HUD_TEXT_COLOR)
        self.screen.blit(hud_surface, (10, 10))

        if self.cfg.debug_event_log and self.frame_logs:
            for index, line in enumerate(self.frame_logs):
                log_surface = self.font.render(line, True, NOCTURNAL_EXPEDITION)
                self.screen.blit(log_surface, (10, 36 + index * 18))

        if self.finished:
            winner_surface = self.big_font.render(self.winner_text, True, FORSYTHIA)
            detail_surface = self.font.render("Press ESC to quit", True, NOCTURNAL_EXPEDITION)
            winner_rect = winner_surface.get_rect(center=(self.cfg.map_width // 2, self.cfg.map_height // 2 - 16))
            detail_rect = detail_surface.get_rect(center=(self.cfg.map_width // 2, self.cfg.map_height // 2 + 20))
            self.screen.blit(winner_surface, winner_rect)
            self.screen.blit(detail_surface, detail_rect)

        pygame.display.flip()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="game_config.json")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config(Path(args.config))
    game = PongWarsGame(config)
    game.run()


if __name__ == "__main__":
    main()
