from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Dict, List, Tuple

import pygame

from game.entities import Building, Unit, create_building, create_unit


@dataclass
class AIBrain:
    difficulty: str
    style: str
    map_size: Tuple[int, int]
    timer: float = 0
    build_timer: float = 0
    attack_timer: float = 0

    def update(
        self,
        dt: float,
        resources: Dict[str, float],
        units: List[Unit],
        buildings: List[Building],
        enemy_base: Building,
        tech_multiplier: float,
    ) -> None:
        self.timer += dt
        self.build_timer -= dt
        self.attack_timer -= dt
        if self.build_timer <= 0:
            self.build_timer = 2.5 if self.difficulty == "hard" else 4
            self.build_plan(resources, units, buildings, tech_multiplier)
        if self.attack_timer <= 0:
            self.attack_timer = 10 if self.difficulty == "hard" else 16
            self.command_attack(units, enemy_base)

    def build_plan(self, resources: Dict[str, float], units: List[Unit], buildings: List[Building], tech_multiplier: float) -> None:
        my_buildings = [b for b in buildings if b.team == 1]
        if self.style == "turtle" and len(my_buildings) < 6:
            if resources["steel"] >= 120 and resources["gold"] >= 120:
                buildings.append(create_building("turret", self._random_base_pos(), 1))
                resources["gold"] -= 120
                resources["steel"] -= 120
                return
        if resources["gold"] >= 80 and resources["oil"] >= 40:
            unit_type = random.choice(["infantry", "tank", "aircraft"] if self.difficulty == "hard" else ["infantry", "tank"])
            units.append(create_unit(unit_type, self._random_base_pos(), 1, tech_multiplier))
            resources["gold"] -= 80
            resources["oil"] -= 40

    def command_attack(self, units: List[Unit], enemy_base: Building) -> None:
        my_units = [u for u in units if u.team == 1]
        attack_force = [u for u in my_units if u.role != "infantry"] if self.style == "rush" else my_units
        for unit in attack_force:
            unit.waypoints = [enemy_base.position.copy()]
            unit.target = enemy_base

    def _random_base_pos(self) -> pygame.Vector2:
        return pygame.Vector2(random.randint(self.map_size[0] - 480, self.map_size[0] - 280), random.randint(200, self.map_size[1] - 200))
