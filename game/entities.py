from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

import pygame


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def distance(a: pygame.Vector2, b: pygame.Vector2) -> float:
    return a.distance_to(b)


_ENTITY_ID = 0


def next_entity_id() -> int:
    global _ENTITY_ID
    _ENTITY_ID += 1
    return _ENTITY_ID


@dataclass
class Entity:
    position: pygame.Vector2
    radius: float
    team: int
    hp: float
    max_hp: float
    entity_id: int = field(default_factory=next_entity_id)
    alive: bool = True

    def update(self, dt: float) -> None:
        if self.hp <= 0:
            self.alive = False

    def take_damage(self, amount: float) -> None:
        self.hp -= amount
        if self.hp <= 0:
            self.alive = False

    def draw(self, surface: pygame.Surface, offset: pygame.Vector2, scale: float) -> None:
        pos = (self.position - offset) * scale
        pygame.draw.circle(surface, (255, 255, 255), (int(pos.x), int(pos.y)), max(1, int(self.radius * scale)))


@dataclass
class ResourceNode(Entity):
    resource_type: str = "gold"
    amount: float = 1000

    def harvest(self, rate: float) -> float:
        harvested = min(self.amount, rate)
        self.amount -= harvested
        if self.amount <= 0:
            self.alive = False
        return harvested

    def draw(self, surface: pygame.Surface, offset: pygame.Vector2, scale: float) -> None:
        pos = (self.position - offset) * scale
        color = {"gold": (230, 200, 60), "oil": (30, 30, 40), "steel": (140, 140, 160)}[self.resource_type]
        pygame.draw.circle(surface, color, (int(pos.x), int(pos.y)), max(3, int(self.radius * scale)))


@dataclass
class Unit(Entity):
    speed: float = 120
    attack_range: float = 120
    damage: float = 10
    cooldown: float = 0.6
    target: Optional[Entity] = None
    waypoints: List[pygame.Vector2] = field(default_factory=list)
    selected: bool = False
    attack_timer: float = 0
    role: str = "infantry"

    def update(self, dt: float) -> None:
        super().update(dt)
        self.attack_timer = max(0.0, self.attack_timer - dt)
        if self.target and not self.target.alive:
            self.target = None
        if self.target and distance(self.position, self.target.position) <= self.attack_range:
            if self.attack_timer == 0:
                self.attack_timer = self.cooldown
                self.target.take_damage(self.damage)
        else:
            self.move_along_waypoints(dt)

    def move_along_waypoints(self, dt: float) -> None:
        if not self.waypoints:
            return
        target = self.waypoints[0]
        direction = target - self.position
        if direction.length() < 4:
            self.waypoints.pop(0)
            return
        direction = direction.normalize()
        self.position += direction * self.speed * dt

    def draw(self, surface: pygame.Surface, offset: pygame.Vector2, scale: float) -> None:
        pos = (self.position - offset) * scale
        color = (90, 220, 120) if self.team == 0 else (220, 80, 80)
        if self.role == "tank":
            pygame.draw.rect(surface, color, pygame.Rect(int(pos.x - 10 * scale), int(pos.y - 6 * scale), int(20 * scale), int(12 * scale)))
        elif self.role == "aircraft":
            pygame.draw.polygon(surface, color, [(pos.x, pos.y - 10 * scale), (pos.x - 8 * scale, pos.y + 6 * scale), (pos.x + 8 * scale, pos.y + 6 * scale)])
        else:
            pygame.draw.circle(surface, color, (int(pos.x), int(pos.y)), max(2, int(self.radius * scale)))
        if self.selected:
            pygame.draw.circle(surface, (255, 255, 255), (int(pos.x), int(pos.y)), max(3, int((self.radius + 4) * scale)), 1)
        health_ratio = clamp(self.hp / self.max_hp, 0, 1)
        bar_w = 20 * scale
        pygame.draw.rect(surface, (60, 60, 60), pygame.Rect(int(pos.x - bar_w / 2), int(pos.y - 18 * scale), int(bar_w), int(3 * scale)))
        pygame.draw.rect(surface, (30, 200, 80), pygame.Rect(int(pos.x - bar_w / 2), int(pos.y - 18 * scale), int(bar_w * health_ratio), int(3 * scale)))


@dataclass
class Building(Entity):
    size: Tuple[int, int] = (80, 80)
    production_queue: List[str] = field(default_factory=list)
    production_timer: float = 0
    role: str = "base"

    def enqueue(self, unit_type: str) -> None:
        self.production_queue.append(unit_type)

    def update(self, dt: float) -> Optional[str]:
        super().update(dt)
        produced: Optional[str] = None
        if self.production_queue:
            self.production_timer = max(0.0, self.production_timer - dt)
            if self.production_timer == 0:
                produced = self.production_queue.pop(0)
                self.production_timer = 1.4
        return produced

    def draw(self, surface: pygame.Surface, offset: pygame.Vector2, scale: float) -> None:
        pos = (self.position - offset) * scale
        color = (60, 160, 220) if self.team == 0 else (220, 100, 60)
        rect = pygame.Rect(int(pos.x - self.size[0] * scale / 2), int(pos.y - self.size[1] * scale / 2), int(self.size[0] * scale), int(self.size[1] * scale))
        pygame.draw.rect(surface, color, rect)
        health_ratio = clamp(self.hp / self.max_hp, 0, 1)
        pygame.draw.rect(surface, (60, 60, 60), pygame.Rect(rect.x, rect.y - int(6 * scale), rect.width, int(4 * scale)))
        pygame.draw.rect(surface, (30, 200, 80), pygame.Rect(rect.x, rect.y - int(6 * scale), int(rect.width * health_ratio), int(4 * scale)))


@dataclass
class Projectile(Entity):
    velocity: pygame.Vector2 = field(default_factory=pygame.Vector2)
    lifetime: float = 1.2
    damage: float = 20

    def update(self, dt: float) -> None:
        self.lifetime -= dt
        if self.lifetime <= 0:
            self.alive = False
        self.position += self.velocity * dt

    def draw(self, surface: pygame.Surface, offset: pygame.Vector2, scale: float) -> None:
        pos = (self.position - offset) * scale
        pygame.draw.circle(surface, (255, 200, 80), (int(pos.x), int(pos.y)), max(2, int(self.radius * scale)))


def create_unit(unit_type: str, position: pygame.Vector2, team: int, tech_multiplier: float = 1.0) -> Unit:
    if unit_type == "infantry":
        unit = Unit(position=position, radius=12, team=team, hp=80, max_hp=80, speed=130, attack_range=130, damage=12, cooldown=0.7, role="infantry")
    elif unit_type == "tank":
        unit = Unit(position=position, radius=16, team=team, hp=200, max_hp=200, speed=90, attack_range=160, damage=24, cooldown=0.9, role="tank")
    else:
        unit = Unit(position=position, radius=14, team=team, hp=140, max_hp=140, speed=160, attack_range=190, damage=18, cooldown=0.8, role="aircraft")
    unit.hp *= tech_multiplier
    unit.max_hp *= tech_multiplier
    unit.damage *= tech_multiplier
    return unit


def create_building(building_type: str, position: pygame.Vector2, team: int) -> Building:
    if building_type == "turret":
        return Building(position=position, radius=32, team=team, hp=260, max_hp=260, size=(60, 60), role="turret")
    if building_type == "factory":
        return Building(position=position, radius=44, team=team, hp=420, max_hp=420, size=(90, 70), role="factory")
    if building_type == "airfield":
        return Building(position=position, radius=48, team=team, hp=380, max_hp=380, size=(100, 60), role="airfield")
    if building_type == "refinery":
        return Building(position=position, radius=38, team=team, hp=320, max_hp=320, size=(70, 70), role="refinery")
    return Building(position=position, radius=50, team=team, hp=520, max_hp=520, size=(100, 100), role="base")


def random_resource_node(map_size: Tuple[int, int]) -> ResourceNode:
    resource_type = random.choice(["gold", "oil", "steel"])
    position = pygame.Vector2(random.randint(120, map_size[0] - 120), random.randint(120, map_size[1] - 120))
    return ResourceNode(position=position, radius=24, team=-1, hp=1, max_hp=1, resource_type=resource_type, amount=1200)
