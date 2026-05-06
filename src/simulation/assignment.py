"""
assignment.py – Sprint 5 (US-018)

Nearest-idle-ambulance selection using the pre-computed distance matrix.
Ties are broken by ambulance_id (lowest wins) for determinism.
"""
import math
import logging
from typing import Optional

import numpy as np

from src.simulation.ambulance import Ambulance, AmbulanceState
from src.simulation.event_spawner import Accident

logger = logging.getLogger(__name__)


def assign_nearest_idle(
    event: Accident,
    idle_ambulances: list[Ambulance],
    distance_matrix: np.ndarray,
    node_index: dict,
) -> Optional[Ambulance]:
    """Return the idle ambulance closest to *event* via the distance matrix.

    Parameters
    ----------
    event : Accident
        The unassigned emergency event.
    idle_ambulances : list[Ambulance]
        Ambulances currently in IDLE state (pre-filtered by caller).
    distance_matrix : np.ndarray
        Square matrix where ``distance_matrix[i][j]`` is the graph distance
        between node *i* and node *j* (as indexed by *node_index*).
    node_index : dict
        Mapping ``{node_id: matrix_row_col}`` produced at matrix build time.

    Returns
    -------
    Ambulance | None
        The best ambulance, or ``None`` if *idle_ambulances* is empty.
    """
    if not idle_ambulances:
        return None

    best: Optional[Ambulance] = None
    best_dist = float("inf")

    event_node = event.location

    for amb in idle_ambulances:
        dist = _get_distance(
            amb, event_node, distance_matrix, node_index, event.pixel_pos
        )

        if math.isinf(dist):
            continue

        # Tie-breaking: prefer lower ambulance_id for determinism
        if dist < best_dist or (
            dist == best_dist and (best is None or amb.id < best.id)
        ):
            best_dist = dist
            best = amb

    return best


# ── Internal helpers ───────────────────────────────────────────────────────────

def _get_distance(
    amb: Ambulance,
    event_node: int,
    distance_matrix: np.ndarray,
    node_index: dict,
    event_pixel_pos: tuple,
) -> float:
    """O(1) lookup from distance matrix with Euclidean pixel fallback."""
    try:
        i = node_index[amb.current_location]
        j = node_index[event_node]
        return float(distance_matrix[i][j])
    except KeyError:
        # Node genuinely not in matrix index → fall back to Euclidean pixel distance
        logger.warning(
            "Node %s or %s missing from distance matrix index; "
            "falling back to Euclidean distance for ambulance %s.",
            amb.current_location, event_node, amb.id,
        )
        ax, ay = amb.pixel_pos
        ex, ey = event_pixel_pos
        return math.hypot(ex - ax, ey - ay)
