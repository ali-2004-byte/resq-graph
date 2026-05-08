# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ResQ-Graph is an agent-based emergency ambulance dispatch simulation. Ambulances navigate a city road network (graph) to respond to dynamically generated emergency events. The system optimizes response times using smart dispatch algorithms, dynamic fleet rebalancing, and traffic models.

## Common Commands

```bash
# Run simulation (visual mode)
python src/main.py

# Run headless (no display)
python src/main.py --headless

# Run baseline batch experiment (Sprint 8)
python src/run_baseline.py --headless --config headless_baseline.yaml

# Run test suite
pytest tests/ -v

# Run specific test file
pytest tests/test_assignment.py -v
```

## Architecture

The simulation runs on a tick-based engine (`src/simulation/simulation_engine.py`) that orchestrates several subsystems:

- **Map & Pathfinding**: Road network from `data/model_town.graphml` loaded as `nx.MultiGraph` (undirected to prevent dead-end trapping). A* uses Haversine heuristic. Pre-computed distance matrix (`data/distance_matrix.npy`) enables O(1) ambulance-event assignment.

- **Traffic Model**: Dynamic edge congestion based on local event density. Modifies edge weights, triggers mid-route rerouting when conditions worsen significantly.

- **Dispatcher**: Owns the queue of active events. Assigns idle ambulances via distance matrix lookups. Coordinates periodic fleet rebalancing to detected hotspots.

- **Intelligence**: Custom HDBSCAN implementation detects demand hotspots from active event locations. Clusters are used for proactive ambulance positioning.

- **Event Spawner**: Poisson distribution generates emergencies at random graph nodes.

- **Ambulance Agents**: State machines cycling through IDLE → IN_TRANSIT → ON_SCENE → REBALANCING. Follow pre-calculated paths node-by-node, interpolate pixel positions for rendering.

## Key Design Decisions

- **Distance Matrix**: Never bypass `assignment.py` for proximity calculations. Always use the distance matrix for O(1) lookups. Fall back to Euclidean distance only if explicitly necessary.

- **Rendering**: `pygame_renderer.py` relies strictly on data passed to its `draw()` method. Never put simulation state mutations inside the renderer.

- **Seeds**: All randomness flows through `sim_config_loader.py`. Zero hardcoded seeds. Use `event_seed`, `random_seed`, and `ambulance_seed` from config.

- **Headless Mode**: Set `SDL_VIDEODRIVER=dummy` BEFORE any `pygame` import. This is enforced in `main.py` and `run_baseline.py`.

- **HDBSCAN**: Custom implementation in `src/intelligence/hdbscan.py`. Uses Excess of Mass formula `(birth_level - death_level) * size` for cluster stability extraction.

## Current Sprint

Sprint 8 is complete. Features include headless baseline runner, random fleet placement generator, and baseline analysis tools with matplotlib visualizations.