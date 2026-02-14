from __future__ import annotations

import json
from typing import Any, Dict, List

import pygame

from game.entities import Building, ResourceNode, Unit, create_building, create_unit
from game.paths import saves_dir


SAVE_DIR = saves_dir()


def serialize_unit(unit: Unit) -> Dict[str, Any]:
    return {
        "type": unit.role,
        "x": unit.position.x,
        "y": unit.position.y,
        "team": unit.team,
        "hp": unit.hp,
        "waypoints": [(p.x, p.y) for p in unit.waypoints],
    }


def serialize_building(building: Building) -> Dict[str, Any]:
    return {
        "type": building.role,
        "x": building.position.x,
        "y": building.position.y,
        "team": building.team,
        "hp": building.hp,
        "queue": list(building.production_queue),
    }


def serialize_resource(node: ResourceNode) -> Dict[str, Any]:
    return {
        "type": node.resource_type,
        "x": node.position.x,
        "y": node.position.y,
        "amount": node.amount,
    }


def save_game(name: str, payload: Dict[str, Any]) -> None:
    path = SAVE_DIR / f"{name}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_game(name: str) -> Dict[str, Any]:
    path = SAVE_DIR / f"{name}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def restore_units(data: List[Dict[str, Any]]) -> List[Unit]:
    units: List[Unit] = []
    for item in data:
        unit = create_unit(item["type"], pygame.Vector2(item["x"], item["y"]), item["team"])
        unit.hp = item["hp"]
        unit.waypoints = [pygame.Vector2(x, y) for x, y in item.get("waypoints", [])]
        units.append(unit)
    return units


def restore_buildings(data: List[Dict[str, Any]]) -> List[Building]:
    buildings: List[Building] = []
    for item in data:
        building = create_building(item["type"], pygame.Vector2(item["x"], item["y"]), item["team"])
        building.hp = item["hp"]
        building.production_queue = list(item.get("queue", []))
        buildings.append(building)
    return buildings


def restore_resources(data: List[Dict[str, Any]]) -> List[ResourceNode]:
    nodes: List[ResourceNode] = []
    for item in data:
        node = ResourceNode(
            position=pygame.Vector2(item["x"], item["y"]),
            radius=24,
            team=-1,
            hp=1,
            max_hp=1,
            resource_type=item["type"],
            amount=item["amount"],
        )
        nodes.append(node)
    return nodes
