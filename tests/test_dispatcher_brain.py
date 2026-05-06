"""
test_dispatcher_brain.py – Sprint 5 (US-017)

Unit tests for DispatcherBrain state transitions and tick orchestration.
"""
import numpy as np
import networkx as nx
import pytest

from src.simulation.ambulance import Ambulance, AmbulanceState
from src.simulation.event_spawner import Accident
from src.simulation.dispatcher import DispatcherBrain


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture
def simple_graph():
    G = nx.MultiGraph()
    G.add_node(1, x=0.0, y=0.0)
    G.add_node(2, x=1.0, y=1.0)
    G.add_node(3, x=2.0, y=0.0)
    G.add_edge(1, 2, length=100.0)
    G.add_edge(2, 3, length=100.0)
    return G


@pytest.fixture
def node_positions():
    return {
        1: [100, 100],
        2: [200, 200],
        3: [300, 100],
    }


@pytest.fixture
def distance_matrix_and_index(simple_graph):
    nodes      = list(simple_graph.nodes())
    node_index = {n: i for i, n in enumerate(nodes)}
    n          = len(nodes)
    mat        = np.full((n, n), np.inf)
    for i in range(n):
        mat[i][i] = 0.0
    # 1↔2 = 100, 2↔3 = 100, 1↔3 = 200
    mat[node_index[1]][node_index[2]] = mat[node_index[2]][node_index[1]] = 100.0
    mat[node_index[2]][node_index[3]] = mat[node_index[3]][node_index[2]] = 100.0
    mat[node_index[1]][node_index[3]] = mat[node_index[3]][node_index[1]] = 200.0
    return mat, node_index


@pytest.fixture
def dispatcher(simple_graph, node_positions, distance_matrix_and_index):
    mat, idx   = distance_matrix_and_index
    ambulances = [
        Ambulance(id=0, start_node=1, graph=simple_graph),
        Ambulance(id=1, start_node=3, graph=simple_graph),
    ]
    for amb in ambulances:
        amb.pixel_pos = tuple(node_positions[amb.current_location])
    d = DispatcherBrain(
        ambulances      = ambulances,
        distance_matrix = mat,
        node_index      = idx,
        node_positions  = node_positions,
        graph           = simple_graph,
    )
    return d


def _make_event(event_id: int, location: int, pixel_pos=(200, 200)) -> Accident:
    return Accident(
        id=event_id, timestamp=0, location=location,
        pixel_pos=pixel_pos, priority=1,
    )


# ── Tests ──────────────────────────────────────────────────────────────────────

class TestEventIngestion:
    def test_new_event_added_to_active(self, dispatcher):
        event = _make_event(1, location=2)
        dispatcher.tick([event], current_tick=1)
        assert event in dispatcher.active_events

    def test_empty_tick_no_crash(self, dispatcher):
        dispatcher.tick([], current_tick=0)  # must not raise


class TestAssignment:
    def test_idle_ambulance_gets_assigned(self, dispatcher):
        event = _make_event(1, location=2)
        dispatcher.tick([event], current_tick=1)
        assert event.assigned_ambulance_id is not None
        assert event.assigned_ambulance_id != -1  # not UNREACHABLE

    def test_ambulance_transitions_to_in_transit(self, dispatcher):
        event = _make_event(1, location=2)
        dispatcher.tick([event], current_tick=1)
        assigned_id = event.assigned_ambulance_id
        assigned_amb = next(a for a in dispatcher.ambulances if a.id == assigned_id)
        assert assigned_amb.state == AmbulanceState.IN_TRANSIT

    def test_no_idle_ambulances_event_stays_unassigned(self, dispatcher):
        # Force all ambulances to IN_TRANSIT
        for amb in dispatcher.ambulances:
            amb.state = AmbulanceState.IN_TRANSIT
        event = _make_event(1, location=2)
        dispatcher.tick([event], current_tick=1)
        assert event.assigned_ambulance_id is None

    def test_pixel_polyline_populated_after_assign(self, dispatcher):
        event = _make_event(1, location=2)
        dispatcher.tick([event], current_tick=1)
        assigned_id = event.assigned_ambulance_id
        if assigned_id and assigned_id != -1:
            assigned_amb = next(a for a in dispatcher.ambulances if a.id == assigned_id)
            assert len(assigned_amb.pixel_polyline) > 0


class TestCompleteEvent:
    def test_complete_event_returns_ambulance_to_idle(self, dispatcher):
        event = _make_event(1, location=2)
        dispatcher.tick([event], current_tick=1)
        assigned_id = event.assigned_ambulance_id
        if assigned_id is None or assigned_id == -1:
            pytest.skip("Event not assigned – no idle ambulance available")
        amb = next(a for a in dispatcher.ambulances if a.id == assigned_id)
        # Manually put ambulance ON_SCENE so complete_event can be called
        amb.state = AmbulanceState.ON_SCENE
        dispatcher.complete_event(amb, current_tick=5)
        assert amb.state == AmbulanceState.IDLE

    def test_complete_event_records_response_time(self, dispatcher):
        event = _make_event(1, location=2)
        dispatcher.tick([event], current_tick=1)
        assigned_id = event.assigned_ambulance_id
        if assigned_id is None or assigned_id == -1:
            pytest.skip("Event not assigned")
        amb = next(a for a in dispatcher.ambulances if a.id == assigned_id)
        amb.state = AmbulanceState.ON_SCENE
        dispatcher.complete_event(amb, current_tick=5)
        assert len(dispatcher.metrics_tracker.response_times) == 1

    def test_complete_event_clears_polyline(self, dispatcher):
        event = _make_event(1, location=2)
        dispatcher.tick([event], current_tick=1)
        assigned_id = event.assigned_ambulance_id
        if assigned_id is None or assigned_id == -1:
            pytest.skip("Event not assigned")
        amb = next(a for a in dispatcher.ambulances if a.id == assigned_id)
        amb.state = AmbulanceState.ON_SCENE
        dispatcher.complete_event(amb, current_tick=5)
        assert amb.pixel_polyline == []


class TestRebalance:
    def test_rebalance_called_on_interval(self, dispatcher, monkeypatch):
        calls = []
        monkeypatch.setattr(dispatcher, "rebalance_fleet", lambda tick: calls.append(tick))
        from src.config import REBALANCE_INTERVAL
        for t in range(REBALANCE_INTERVAL):
            dispatcher.tick([], current_tick=t)
        assert len(calls) == 1


class TestHelpers:
    def test_get_idle_ambulances(self, dispatcher):
        idle = dispatcher.get_idle_ambulances()
        assert len(idle) == 2  # both start IDLE

    def test_get_unassigned_events(self, dispatcher):
        event = _make_event(99, location=2)
        dispatcher.active_events.append(event)
        unassigned = dispatcher.get_unassigned_events()
        assert event in unassigned
