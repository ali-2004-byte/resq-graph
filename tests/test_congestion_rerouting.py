import pytest
import networkx as nx
import numpy as np
from src.simulation.ambulance import Ambulance, AmbulanceState
from src.simulation.dispatcher import DispatcherBrain
from src.simulation.traffic import TrafficModel
from src.simulation.event_spawner import Accident

def test_congestion_rerouting_logic():
    """
    Scenario:
    - Two paths exist from Node 1 to Node 3.
    - Path A (Short): 1 -> 2 -> 3 (Base Length: 20)
    - Path B (Long):  1 -> 4 -> 5 -> 3 (Base Length: 30)
    
    Steps:
    1. Assign ambulance to event at Node 3. It should pick Path A.
    2. Add heavy congestion to Path A.
    3. Run the dispatcher reroute check.
    4. Assert the ambulance switched to Path B.
    """
    # 1. Setup Graph with realistic node coordinates (approx 11m per 0.0001 deg)
    G = nx.Graph()
    G.add_node(1, x=0.0000, y=0.0000)
    G.add_node(2, x=0.0001, y=0.0000) # ~11m away
    G.add_node(3, x=0.0002, y=0.0000) # ~22m away from 1
    G.add_node(4, x=0.0000, y=0.0001) # ~11m away (North)
    G.add_node(5, x=0.0002, y=0.0001) # ~22m away from 4

    G.add_edge(1, 2, length=11.0)
    G.add_edge(2, 3, length=11.0)
    G.add_edge(1, 4, length=11.0)
    G.add_edge(4, 5, length=22.0)
    G.add_edge(5, 3, length=11.0)
    
    node_positions = {
        1: (0, 0), 2: (100, 0), 3: (200, 0),
        4: (0, 100), 5: (200, 100)
    }
    
    # Mapping for distance matrix
    node_index = {1: 0, 2: 1, 3: 2, 4: 3, 5: 4}
    dist_matrix = np.full((5, 5), np.inf)
    dist_matrix[0, 2] = 22.0 # Initial shortest distance (1-2-3)
    
    # 2. Setup Components
    amb = Ambulance(id=0, start_node=1, graph=G)
    amb.pixel_pos = (0, 0)
    traffic = TrafficModel(G, node_positions, max_multiplier=5.0, decay_rate=0.0)
    
    # Use a 10% threshold for sensitive testing
    cfg = {"REROUTE_THRESHOLD": 0.10, "REROUTE_CHECK_INTERVAL": 1}
    dispatcher = DispatcherBrain(
        ambulances=[amb],
        distance_matrix=dist_matrix,
        node_index=node_index,
        node_positions=node_positions,
        graph=G,
        traffic=traffic,
        cfg=cfg
    )
    
    # 3. Assign Task
    event = Accident(id=1, timestamp=0, location=3, pixel_pos=(200, 0), priority=1)
    dispatcher.assign_task(amb, event, current_tick=0)
    
    # Initial path should be 1-2-3
    assert amb.current_path == [1, 2, 3]
    assert amb.path_weight_at_dispatch == 22.0
    
    # 4. Inject Congestion on edge 1-2 (multiplier = 4.0)
    # Path A weight becomes: (11 * 4) + 11 = 55
    traffic._multipliers[frozenset({1, 2})] = 4.0
    
    # 5. Trigger Dispatcher Check
    dispatcher._check_rerouting(current_tick=1)
    
    # 6. Final Assertions
    # Path B (1-4-5-3) weight is 11+22+11 = 44, which is now faster than Path A (55)
    assert amb.current_path == [1, 4, 5, 3], f"Expected path [1,4,5,3], got {amb.current_path}"
    # Baseline weight should be updated to the new path weight (44.0)
    assert amb.path_weight_at_dispatch == 44.0
    
    print("\nSUCCESS: Congestion detection and re-routing verified!")

if __name__ == "__main__":
    test_congestion_rerouting_logic()
