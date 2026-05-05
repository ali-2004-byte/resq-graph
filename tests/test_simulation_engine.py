import pytest
import networkx as nx
from src.simulation.simulation_engine import SimulationState, _tick
from src.simulation.ambulance import Ambulance, AmbulanceState
from src.simulation.event_spawner import EventSpawner, Accident
from src.simulation.dispatcher import BasicDispatcher

@pytest.fixture
def mock_components():
    node_positions = {
        1: {"x": 100, "y": 100},
        2: {"x": 200, "y": 200}
    }
    G = nx.Graph()
    G.add_node(1, x=100.0, y=100.0)
    G.add_node(2, x=200.0, y=200.0)
    G.add_edge(1, 2, length=141.4)
    
    state = SimulationState()
    ambulances = [Ambulance(id=1, start_node=1, graph=G)]
    spawner = EventSpawner(lambda_rate=0.0, node_positions=node_positions) # no random spawn
    dispatcher = BasicDispatcher()
    
    return state, ambulances, spawner, dispatcher, node_positions

def test_simulation_tick(mock_components):
    state, ambulances, spawner, dispatcher, node_positions = mock_components
    
    # Tick 1
    _tick(state, ambulances, spawner, dispatcher, node_positions)
    assert state.current_tick == 1
    assert state.ambulance_positions[1] == (100.0, 100.0)
    
    # Add a manual event to test dispatch
    event = Accident(id=1, timestamp=1, location=2, pixel_pos=(200, 200), priority=1)
    state.active_events.append(event)
    
    # Tick 2 - ambulance should dispatch
    _tick(state, ambulances, spawner, dispatcher, node_positions)
    assert state.current_tick == 2
    assert ambulances[0].state == AmbulanceState.IN_TRANSIT
    assert ambulances[0].assigned_task == event
    assert event.assigned_ambulance_id == 1
    
    # Speed up ambulance to arrive immediately
    ambulances[0].speed = 1.0
    
    # Tick 3 - ambulance arrives
    _tick(state, ambulances, spawner, dispatcher, node_positions)
    assert state.current_tick == 3
    # During tick 3, it updates position, reaches ON_SCENE. 
    # But resolution happens at the end of the tick.
    # Actually, in _tick, update_position happens first, then resolution. 
    # Let's check state.
    assert len(state.resolved_events) == 1
    assert state.resolved_events[0] == event
    assert len(state.active_events) == 0
    assert len(state.total_response_times) == 1
