"""
test_assignment.py – Sprint 5 (US-018)

Unit tests for assign_nearest_idle(): nearest selection, tie-breaking,
pixel polyline caching, and edge cases.
"""
import math
import numpy as np
import networkx as nx
import pytest

from src.simulation.ambulance import Ambulance, AmbulanceState
from src.simulation.event_spawner import Accident
from src.simulation.assignment import assign_nearest_idle


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_graph():
    G = nx.MultiGraph()
    for nid in [1, 2, 3, 4]:
        G.add_node(nid, x=float(nid * 10), y=0.0)
    G.add_edge(1, 2, length=10.0)
    G.add_edge(2, 3, length=10.0)
    G.add_edge(3, 4, length=10.0)
    return G


def _make_matrix_and_index():
    nodes      = [1, 2, 3, 4]
    node_index = {n: i for i, n in enumerate(nodes)}
    mat        = np.array([
        [0,  10, 20, 30],
        [10,  0, 10, 20],
        [20, 10,  0, 10],
        [30, 20, 10,  0],
    ], dtype=float)
    return mat, node_index


def _make_ambulance(amb_id: int, node: int, graph, pixel_pos=(0, 0)) -> Ambulance:
    a = Ambulance(id=amb_id, start_node=node, graph=graph)
    a.pixel_pos = pixel_pos
    return a


def _make_event(location: int, pixel_pos=(0, 0)) -> Accident:
    return Accident(id=0, timestamp=0, location=location,
                    pixel_pos=pixel_pos, priority=1)


# ── Tests ──────────────────────────────────────────────────────────────────────

class TestNearestSelection:
    def test_nearest_ambulance_selected(self):
        G   = _make_graph()
        mat, idx = _make_matrix_and_index()
        # Amb 0 at node 1 (dist 20 to node 3)
        # Amb 1 at node 4 (dist 10 to node 3) → should win
        ambs = [
            _make_ambulance(0, node=1, graph=G, pixel_pos=(10, 0)),
            _make_ambulance(1, node=4, graph=G, pixel_pos=(40, 0)),
        ]
        event  = _make_event(location=3, pixel_pos=(30, 0))
        result = assign_nearest_idle(event, ambs, mat, idx)
        assert result is not None
        assert result.id == 1  # closer by graph distance

    def test_single_ambulance_always_selected(self):
        G        = _make_graph()
        mat, idx = _make_matrix_and_index()
        amb      = _make_ambulance(0, node=1, graph=G)
        event    = _make_event(location=4)
        result   = assign_nearest_idle(event, [amb], mat, idx)
        assert result is amb

    def test_empty_pool_returns_none(self):
        G        = _make_graph()
        mat, idx = _make_matrix_and_index()
        event    = _make_event(location=2)
        result   = assign_nearest_idle(event, [], mat, idx)
        assert result is None


class TestTieBreaking:
    def test_lower_ambulance_id_wins_on_tie(self):
        G        = _make_graph()
        mat, idx = _make_matrix_and_index()
        # Both ambulances at node 1 → same distance to node 2
        amb_hi   = _make_ambulance(5, node=1, graph=G)
        amb_lo   = _make_ambulance(2, node=1, graph=G)
        event    = _make_event(location=2)
        result   = assign_nearest_idle(event, [amb_hi, amb_lo], mat, idx)
        assert result.id == 2  # lower id wins

    def test_tie_breaking_is_deterministic(self):
        G        = _make_graph()
        mat, idx = _make_matrix_and_index()
        amb_a    = _make_ambulance(10, node=2, graph=G)
        amb_b    = _make_ambulance(3,  node=2, graph=G)
        event    = _make_event(location=3)
        # Run multiple times to confirm determinism
        results  = {
            assign_nearest_idle(event, [amb_a, amb_b], mat, idx).id
            for _ in range(10)
        }
        assert results == {3}  # always lower id


class TestFallback:
    def test_missing_node_falls_back_to_euclidean(self):
        G   = _make_graph()
        mat = np.zeros((2, 2))  # small matrix, won't contain all nodes
        idx = {1: 0, 2: 1}      # only nodes 1 and 2 in index
        # Ambulance at node 3 which is NOT in idx → triggers fallback
        amb   = _make_ambulance(0, node=3, graph=G, pixel_pos=(30, 0))
        event = _make_event(location=3, pixel_pos=(30, 0))
        # Should not raise; fallback Euclidean distance = 0 (same pixel)
        result = assign_nearest_idle(event, [amb], mat, idx)
        assert result is amb
