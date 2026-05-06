"""
simulation_engine.py – Sprint 5 (US-020)

Wires DispatcherBrain into the tick loop. Key changes from Sprint 4:
- New events are routed through dispatcher.tick() (dispatcher owns active_events).
- M key toggles the detailed metrics panel.
- CSV flushed every METRICS_FLUSH_INTERVAL ticks; summary exported on exit.
- Renderer receives dispatcher so it can read active_events and HUD metrics.
"""
import logging
import os
from dataclasses import dataclass, field

import networkx as nx
import json
import numpy as np
import pygame

from src.config import (
    NUM_AMBULANCES,
    SIMULATION_TICKS,
    TARGET_FPS,
    REDRAW_INTERVAL,
    POISSON_LAMBDA,
    METRICS_FLUSH_INTERVAL,
    WINDOW_WIDTH,
    WINDOW_HEIGHT,
)
from src.simulation.ambulance import Ambulance, AmbulanceState
from src.simulation.event_spawner import Accident, EventSpawner
from src.simulation.dispatcher import DispatcherBrain
from src.distance_matrix import compute_distance_matrix, load_distance_matrix
from src.rendering.pygame_renderer import PygameRenderer

logger = logging.getLogger(__name__)


# ── Simulation State ───────────────────────────────────────────────────────────

@dataclass
class SimulationState:
    """Lightweight snapshot of simulation progress.

    In Sprint 5, active_events is owned by DispatcherBrain.
    This class retains tick, pause, and position info used by the renderer.
    """
    current_tick:        int              = 0
    ambulance_positions: dict[int, tuple] = field(default_factory=dict)
    paused:              bool             = False


# ── Data loaders ───────────────────────────────────────────────────────────────

def load_node_positions(filepath: str) -> dict:
    with open(filepath, "r") as f:
        data = json.load(f)
    return {int(k): v for k, v in data.items()}


def load_graph(filepath: str):
    G = nx.read_graphml(filepath)
    # Convert to undirected to prevent ambulances from getting trapped in dead-ends
    G_undirected = nx.MultiGraph(G)
    return nx.relabel_nodes(G_undirected, {n: int(n) for n in G_undirected.nodes()})


def _build_node_index(graph) -> dict:
    """Produce the same node→row/col mapping used when the matrix was saved."""
    return {node: i for i, node in enumerate(graph.nodes())}


def _load_or_compute_matrix(graph, matrix_path: str = "data/distance_matrix.npy"):
    """Load the pre-computed distance matrix, or compute and save it on first run."""
    node_index = _build_node_index(graph)
    if os.path.exists(matrix_path):
        logger.info("Loading distance matrix from %s …", matrix_path)
        matrix = load_distance_matrix(matrix_path)
    else:
        logger.info("Distance matrix not found. Computing … (this may take a moment)")
        matrix, node_index = compute_distance_matrix(graph, save_path=matrix_path)
    return matrix, node_index


# ── Tick logic ─────────────────────────────────────────────────────────────────

def _tick(
    state:         SimulationState,
    ambulances:    list[Ambulance],
    spawner:       EventSpawner,
    dispatcher:    DispatcherBrain,
    node_positions: dict,
) -> None:
    """One simulation tick.

    Tick order (Sprint 5):
    1. Update ambulance positions (movement interpolation).
    2. Spawn new events via Poisson process.
    3. Dispatcher tick: ingests events, assigns ambulances, completes on-scene,
       rebalances, snapshots metrics.
    4. Update state snapshot (tick counter, position map).
    """
    # Step 1: move ambulances
    for amb in ambulances:
        amb.update_position(node_positions)

    # Step 2: spawn
    new_accidents = spawner.spawn(state.current_tick)

    # Step 3: dispatcher owns event lifecycle from here
    dispatcher.tick(new_accidents, state.current_tick)

    # Step 4: bookkeeping
    state.ambulance_positions = {a.id: a.pixel_pos for a in ambulances}
    state.current_tick += 1


# ── Main entry point ───────────────────────────────────────────────────────────

def run_simulation() -> None:
    """Initialise all components and run the main Pygame loop."""
    logging.basicConfig(level=logging.WARNING)

    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("ResQ-Graph – Dispatcher Simulation")
    clock = pygame.time.Clock()

    # ── Load map data ──────────────────────────────────────────────────────────
    node_positions = load_node_positions("data/node_positions.json")
    graph          = load_graph("data/model_town.graphml")

    # ── Build / load distance matrix ──────────────────────────────────────────
    distance_matrix, node_index = _load_or_compute_matrix(graph)

    # ── Initialise ambulances ──────────────────────────────────────────────────
    node_ids   = list(node_positions.keys())
    ambulances = [
        Ambulance(id=i, start_node=int(node_ids[i % len(node_ids)]), graph=graph)
        for i in range(NUM_AMBULANCES)
    ]
    for amb in ambulances:
        amb.update_position(node_positions)

    # ── Initialise subsystems ──────────────────────────────────────────────────
    spawner    = EventSpawner(lambda_rate=POISSON_LAMBDA, node_positions=node_positions)
    dispatcher = DispatcherBrain(
        ambulances      = ambulances,
        distance_matrix = distance_matrix,
        node_index      = node_index,
        node_positions  = node_positions,
        graph           = graph,
    )
    renderer = PygameRenderer(screen, node_positions)
    state    = SimulationState()

    show_metrics_panel = False
    running = True

    # ── Main loop ──────────────────────────────────────────────────────────────
    while running and state.current_tick < SIMULATION_TICKS:

        # Step 1: handle Pygame events
        for pg_event in pygame.event.get():
            if pg_event.type == pygame.QUIT:
                running = False
            elif pg_event.type == pygame.KEYDOWN:
                if pg_event.key == pygame.K_SPACE:
                    state.paused = not state.paused
                elif pg_event.key == pygame.K_m:            # ← NEW (Sprint 5)
                    show_metrics_panel = not show_metrics_panel

        # Step 2-4: simulation tick (skipped while paused)
        if not state.paused:
            _tick(state, ambulances, spawner, dispatcher, node_positions)

        # Step 5: render
        if state.current_tick % REDRAW_INTERVAL == 0:
            renderer.draw(state, ambulances, dispatcher, show_metrics_panel)

        clock.tick(TARGET_FPS)

    # ── Cleanup ────────────────────────────────────────────────────────────────
    dispatcher.metrics_tracker.flush_csv()
    dispatcher.metrics_tracker.export_summary_csv()
    pygame.quit()
