import numpy as np
from dataclasses import dataclass
from typing import Optional

@dataclass
class Accident:
    id:        int
    timestamp: int           # simulation tick when spawned
    location:  int           # graph node ID
    pixel_pos: tuple[int, int]  # resolved from node_positions.json (for Pygame rendering)
    priority:  int           # 1 (high) – 3 (low)
    resolved:  bool = False
    assigned_ambulance_id: Optional[int] = None


class EventSpawner:
    def __init__(self, lambda_rate: float, node_positions: dict, rng_seed: int = None):
        self.lambda_rate    = lambda_rate       # avg accidents per tick
        self.node_positions = node_positions
        self.rng            = np.random.default_rng(rng_seed)
        self._next_id       = 0
        self.node_ids       = list(node_positions.keys())

    def spawn(self, current_tick: int) -> list[Accident]:
        """Draw n ~ Poisson(lambda_rate). Return n new Accident objects
        at random nodes with random priorities. Returns empty list if n == 0."""
        n_accidents = self.rng.poisson(self.lambda_rate)
        accidents = []
        for _ in range(n_accidents):
            node_id, pixel_pos = self._random_node()
            priority = self.rng.choice([1, 2, 3])
            acc = Accident(
                id=self._next_id,
                timestamp=current_tick,
                location=node_id,
                pixel_pos=pixel_pos,
                priority=priority
            )
            self._next_id += 1
            accidents.append(acc)
        return accidents

    def set_lambda(self, new_lambda: float) -> None:
        """Hot-update rate parameter without restarting the simulation."""
        self.lambda_rate = new_lambda

    def _random_node(self) -> tuple[int, tuple[int, int]]:
        """Pick a random node ID and return (node_id, pixel_pos)."""
        node_id = self.rng.choice(self.node_ids)
        pos = self.node_positions[node_id]
        # Cast node_id to int in case it's a string from JSON
        return int(node_id), (int(pos[0]), int(pos[1]))
