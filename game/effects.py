from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import List, Tuple

import pygame


@dataclass
class Particle:
    position: pygame.Vector2
    velocity: pygame.Vector2
    color: Tuple[int, int, int]
    radius: float
    lifetime: float

    def update(self, dt: float) -> None:
        self.lifetime -= dt
        self.position += self.velocity * dt

    def draw(self, surface: pygame.Surface, offset: pygame.Vector2, scale: float) -> None:
        if self.lifetime <= 0:
            return
        pos = (self.position - offset) * scale
        pygame.draw.circle(surface, self.color, (int(pos.x), int(pos.y)), max(1, int(self.radius * scale)))


@dataclass
class WeatherSystem:
    map_size: Tuple[int, int]
    day_cycle: float = 0.0
    weather: str = "clear"
    particles: List[Particle] = field(default_factory=list)
    change_timer: float = 0.0

    def update(self, dt: float) -> None:
        self.day_cycle = (self.day_cycle + dt * 0.03) % 1.0
        self.change_timer -= dt
        if self.change_timer <= 0:
            self.weather = random.choice(["clear", "rain", "snow"])
            self.change_timer = random.uniform(35, 70)
        self.spawn_particles(dt)
        for particle in list(self.particles):
            particle.update(dt)
            if particle.lifetime <= 0 or particle.position.y > self.map_size[1] + 200:
                self.particles.remove(particle)

    def spawn_particles(self, dt: float) -> None:
        if self.weather == "clear":
            return
        count = int(80 * dt) if self.weather == "rain" else int(40 * dt)
        for _ in range(count):
            x = random.uniform(0, self.map_size[0])
            y = random.uniform(-50, 50)
            if self.weather == "rain":
                velocity = pygame.Vector2(random.uniform(-20, 20), random.uniform(380, 520))
                color = (120, 160, 220)
                radius = 2
                lifetime = 2.2
            else:
                velocity = pygame.Vector2(random.uniform(-20, 20), random.uniform(80, 130))
                color = (230, 230, 240)
                radius = 3
                lifetime = 5
            self.particles.append(Particle(pygame.Vector2(x, y), velocity, color, radius, lifetime))

    def draw(self, surface: pygame.Surface, offset: pygame.Vector2, scale: float) -> None:
        for particle in self.particles:
            particle.draw(surface, offset, scale)
        darkness = 0.45 * (1 - math.cos(self.day_cycle * math.tau)) / 2
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill((10, 20, 40, int(200 * darkness)))
        surface.blit(overlay, (0, 0))


@dataclass
class CommandFeedback(Particle):
    def update(self, dt: float) -> None:
        self.lifetime -= dt
        self.radius += 20 * dt
        
    def draw(self, surface: pygame.Surface, offset: pygame.Vector2, scale: float) -> None:
        if self.lifetime <= 0:
            return
        pos = (self.position - offset) * scale
        alpha = int(255 * (self.lifetime / 0.5))
        s = pygame.Surface((int(self.radius * 2 * scale), int(self.radius * 2 * scale)), pygame.SRCALPHA)
        pygame.draw.circle(s, (*self.color, alpha), (int(self.radius * scale), int(self.radius * scale)), max(1, int(2 * scale)), 1)
        surface.blit(s, (int(pos.x - self.radius * scale), int(pos.y - self.radius * scale)))

def spawn_command_feedback(position: pygame.Vector2, color: Tuple[int, int, int] = (60, 255, 120)) -> List[Particle]:
    return [CommandFeedback(position.copy(), pygame.Vector2(0, 0), color, radius=5, lifetime=0.5)]

def spawn_explosion(position: pygame.Vector2) -> List[Particle]:
    particles: List[Particle] = []
    for _ in range(24):
        angle = random.uniform(0, math.tau)
        speed = random.uniform(120, 240)
        velocity = pygame.Vector2(math.cos(angle), math.sin(angle)) * speed
        color = random.choice([(255, 200, 80), (255, 120, 60), (200, 60, 40)])
        particles.append(Particle(position.copy(), velocity, color, radius=4, lifetime=1.2))
    return particles
