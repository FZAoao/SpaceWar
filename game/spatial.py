from __future__ import annotations

from collections import defaultdict
from typing import Dict, Iterable, List, Set, Tuple


class SpatialHash:
    def __init__(self, cell_size: int = 64) -> None:
        self.cell_size = cell_size
        self.cells: Dict[Tuple[int, int], Set[int]] = defaultdict(set)

    def _cell(self, x: float, y: float) -> Tuple[int, int]:
        return int(x // self.cell_size), int(y // self.cell_size)

    def clear(self) -> None:
        self.cells.clear()

    def insert(self, entity_id: int, x: float, y: float, radius: float) -> None:
        min_cell = self._cell(x - radius, y - radius)
        max_cell = self._cell(x + radius, y + radius)
        for cx in range(min_cell[0], max_cell[0] + 1):
            for cy in range(min_cell[1], max_cell[1] + 1):
                self.cells[(cx, cy)].add(entity_id)

    def query(self, x: float, y: float, radius: float) -> Iterable[int]:
        min_cell = self._cell(x - radius, y - radius)
        max_cell = self._cell(x + radius, y + radius)
        visited: Set[int] = set()
        for cx in range(min_cell[0], max_cell[0] + 1):
            for cy in range(min_cell[1], max_cell[1] + 1):
                for entity_id in self.cells.get((cx, cy), ()):
                    if entity_id not in visited:
                        visited.add(entity_id)
                        yield entity_id


def nearby_pairs(ids: Iterable[int], positions: Dict[int, Tuple[float, float]], radius: float) -> List[Tuple[int, int]]:
    spatial = SpatialHash(cell_size=max(int(radius), 32))
    for entity_id in ids:
        x, y = positions[entity_id]
        spatial.insert(entity_id, x, y, radius)
    pairs: List[Tuple[int, int]] = []
    for entity_id in ids:
        x, y = positions[entity_id]
        for other_id in spatial.query(x, y, radius):
            if other_id > entity_id:
                pairs.append((entity_id, other_id))
    return pairs
