from __future__ import annotations

import random
from collections import deque

import pygame

from pongwars.config import GameConfig
from pongwars.constants import (
    BACKGROUND_COLOR,
    DAY_BALL_COLOR,
    FORSYTHIA,
    HUD_TEXT_COLOR,
    NIGHT_BALL_COLOR,
    NOCTURNAL_EXPEDITION,
    WALL_COLOR,
)
from pongwars.entities import Ball, BallAction, Team
from pongwars.events import EventType, GameEvent
from pongwars.physics import circle_rect_collision, reflect, wall_rect_from_cell
from pongwars.spawn import spawn_balls
from pongwars.walls import generate_wall_blocks, spawn_random_walls


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
        self.random_wall_spawn_elapsed_sec = 0.0
        self.running = True
        self.finished = False
        self.winner_text = ""
        self.frame_logs: list[str] = []

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
        self.random_wall_spawn_elapsed_sec += dt

        alive_balls = self.alive_balls()
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
        self.spawn_runtime_walls_if_needed()
        self.check_game_end()

    def alive_balls(self) -> list[Ball]:
        return [ball for ball in self.balls if ball.alive]

    def get_ball(self, ball_id: int) -> Ball | None:
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
            best_event: GameEvent | None = None
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
                    dist = dist_sq**0.5
                    nx = dx / dist
                    ny = dy / dist
                    penetration = radius_sum - dist
                else:
                    rvx = a.vx - b.vx
                    rvy = a.vy - b.vy
                    rv_norm = (rvx * rvx + rvy * rvy) ** 0.5
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

    def spawn_runtime_walls_if_needed(self) -> None:
        if not self.cfg.random_wall_spawn.enabled:
            return

        if self.random_wall_spawn_elapsed_sec < self.cfg.random_wall_spawn.interval_sec:
            return

        self.random_wall_spawn_elapsed_sec = 0.0
        spawned = spawn_random_walls(self.wall_blocks, self.balls, self.cfg)
        if spawned:
            self.log_event(f"wall-spawn +{len(spawned)}")

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
        hud = (
            f"time {time_left:05.1f}s | day {day_alive} | "
            f"night {night_alive} | walls {len(self.wall_blocks)}"
        )
        hud_surface = self.font.render(hud, True, HUD_TEXT_COLOR)
        self.screen.blit(hud_surface, (10, 10))

        if self.cfg.debug_event_log and self.frame_logs:
            for index, line in enumerate(self.frame_logs):
                log_surface = self.font.render(line, True, NOCTURNAL_EXPEDITION)
                self.screen.blit(log_surface, (10, 36 + index * 18))

        if self.finished:
            winner_surface = self.big_font.render(self.winner_text, True, FORSYTHIA)
            detail_surface = self.font.render("Press ESC to quit", True, NOCTURNAL_EXPEDITION)
            winner_rect = winner_surface.get_rect(
                center=(self.cfg.map_width // 2, self.cfg.map_height // 2 - 16)
            )
            detail_rect = detail_surface.get_rect(
                center=(self.cfg.map_width // 2, self.cfg.map_height // 2 + 20)
            )
            self.screen.blit(winner_surface, winner_rect)
            self.screen.blit(detail_surface, detail_rect)

        pygame.display.flip()
