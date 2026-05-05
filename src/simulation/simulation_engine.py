from dataclasses import dataclass, field
import pygame
import json
import networkx as nx

from src.config import *
from src.simulation.ambulance import Ambulance, AmbulanceState
from src.simulation.event_spawner import Accident, EventSpawner
from src.simulation.dispatcher import BasicDispatcher
from src.rendering.pygame_renderer import PygameRenderer


@dataclass
class SimulationState:
    current_tick:         int               = 0
    active_events:        list[Accident]    = field(default_factory=list)
    resolved_events:      list[Accident]    = field(default_factory=list)
    ambulance_positions:  dict[int, tuple]  = field(default_factory=dict)
    paused:               bool              = False
    total_response_times: list[float]       = field(default_factory=list)

    @property
    def avg_response_time(self) -> float:
        return sum(self.total_response_times) / len(self.total_response_times) \
               if self.total_response_times else 0.0


def load_node_positions(filepath):
    with open(filepath, 'r') as f:
        data = json.load(f)
        return {int(k): v for k, v in data.items()}

def load_graph(filepath):
    G = nx.read_graphml(filepath)
    return nx.relabel_nodes(G, {n: int(n) for n in G.nodes()})

def _tick(state: SimulationState, ambulances: list[Ambulance], spawner: EventSpawner, dispatcher: BasicDispatcher, node_positions: dict):
    # Step 2: Update ambulance positions
    for amb in ambulances:
        amb.update_position(node_positions)

    # Step 3: Spawn new events
    new_accidents = spawner.spawn(state.current_tick)
    state.active_events.extend(new_accidents)

    # Step 4: Dispatch idle ambulances
    dispatcher.assign(ambulances, state.active_events)

    # Step 5: Resolve on-scene ambulances
    for amb in ambulances:
        if amb.state == AmbulanceState.ON_SCENE:
            task = amb.assigned_task
            if task and not task.resolved:
                response_time = state.current_tick - task.timestamp
                state.total_response_times.append(response_time)
                amb.complete_task()
                # Move to resolved
                state.active_events = [e for e in state.active_events if e.id != task.id]
                state.resolved_events.append(task)

    # Step 6: Update state snapshot
    state.ambulance_positions = {a.id: a.pixel_pos for a in ambulances}
    state.current_tick += 1

def run_simulation():
    pygame.init()
    screen  = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    clock   = pygame.time.Clock()
    
    node_positions = load_node_positions("data/node_positions.json")
    graph          = load_graph("data/model_town.graphml")
    
    # Initialize ambulances at arbitrary nodes
    node_ids = list(node_positions.keys())
    
    ambulances = [Ambulance(id=i, start_node=int(node_ids[i % len(node_ids)]), graph=graph) for i in range(NUM_AMBULANCES)]
    for amb in ambulances:
        amb.update_position(node_positions)

    spawner     = EventSpawner(lambda_rate=POISSON_LAMBDA, node_positions=node_positions)
    dispatcher  = BasicDispatcher()
    renderer    = PygameRenderer(screen, node_positions)
    state       = SimulationState()
    
    running = True
    while running and state.current_tick < SIMULATION_TICKS:
        # Step 1: Events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                state.paused = not state.paused
        
        if not state.paused:
            _tick(state, ambulances, spawner, dispatcher, node_positions)
        
        # Step 7: Render
        if state.current_tick % REDRAW_INTERVAL == 0:
            renderer.draw(state, ambulances)
            
        clock.tick(TARGET_FPS)
    
    pygame.quit()
