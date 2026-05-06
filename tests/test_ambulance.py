import pytest
import networkx as nx
from src.simulation.ambulance import Ambulance, AmbulanceState


@pytest.fixture
def mock_graph():
    # Must be MultiGraph: astar.py calls .values() on G[u][v] assuming multigraph structure
    G = nx.MultiGraph()
    G.add_node(1, x=0.0, y=0.0)
    G.add_node(2, x=1.0, y=1.0)
    G.add_edge(1, 2, length=141.4)
    return G


@pytest.fixture
def node_positions():
    # Production code uses pos[0] / pos[1], so values are lists not dicts
    return {
        1: [100, 100],
        2: [200, 200],
    }


def test_initial_state(mock_graph, node_positions):
    amb = Ambulance(id=1, start_node=1, graph=mock_graph)
    assert amb.state == AmbulanceState.IDLE
    assert amb.current_path == []

    amb.update_position(node_positions)
    assert amb.pixel_pos == (100.0, 100.0)


def test_navigate(mock_graph):
    amb = Ambulance(id=1, start_node=1, graph=mock_graph)
    amb.navigate(2)
    assert amb.state == AmbulanceState.IN_TRANSIT
    assert amb.current_path == [1, 2]


def test_update_position(mock_graph, node_positions):
    amb = Ambulance(id=1, start_node=1, graph=mock_graph)
    amb.navigate(2)

    amb.speed = 0.5
    amb.update_position(node_positions)
    assert amb.pixel_pos == (150.0, 150.0)
    assert amb.state == AmbulanceState.IN_TRANSIT

    amb.update_position(node_positions)
    assert amb.pixel_pos == (200.0, 200.0)
    assert amb.state == AmbulanceState.ON_SCENE


def test_sprint5_fields_exist(mock_graph):
    """Sprint 5: Ambulance must have pixel_polyline and dispatch_tick fields."""
    amb = Ambulance(id=0, start_node=1, graph=mock_graph)
    assert hasattr(amb, "pixel_polyline")
    assert hasattr(amb, "dispatch_tick")
    assert amb.pixel_polyline == []
    assert amb.dispatch_tick is None


def test_complete_task_clears_sprint5_fields(mock_graph):
    """Sprint 5: complete_task() must clear pixel_polyline and dispatch_tick."""
    amb = Ambulance(id=0, start_node=1, graph=mock_graph)
    amb.pixel_polyline = [(10, 10), (20, 20)]
    amb.dispatch_tick  = 5
    amb.complete_task()
    assert amb.pixel_polyline == []
    assert amb.dispatch_tick is None
    assert amb.state == AmbulanceState.IDLE
