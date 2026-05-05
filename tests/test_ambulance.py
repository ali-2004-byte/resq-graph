import pytest
import numpy as np
from src.simulation.ambulance import Ambulance, AmbulanceState
import networkx as nx

@pytest.fixture
def mock_graph():
    G = nx.Graph()
    G.add_node(1, x=100.0, y=100.0)
    G.add_node(2, x=200.0, y=200.0)
    G.add_edge(1, 2, length=141.4)
    return G

@pytest.fixture
def node_positions():
    return {
        1: {"x": 100, "y": 100},
        2: {"x": 200, "y": 200}
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
