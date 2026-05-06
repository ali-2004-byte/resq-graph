# ResQ-Graph

ResQ-Graph is an agent-based graph simulation for emergency ambulance dispatch. It models a fleet of ambulances navigating a city road network (represented as a graph) to respond to dynamically generated emergency events. The project aims to simulate, visualize, and optimize response times using smart dispatch algorithms and fleet rebalancing.

This repository is currently up-to-date through **Sprint 5**.

## Core Architecture & Components

The system relies on a central tick-based simulation engine that orchestrates several distinct sub-systems.

### 1. Simulation Engine (`src/simulation/simulation_engine.py`)
The heart of the project. It runs a `while` loop (capped at a defined number of ticks), updating the state of ambulances, spawning new events, calling the dispatcher, and triggering the Pygame renderer. It ensures deterministic state updates.

### 2. Map & Pathfinding (`src/astar.py`, `src/distance_matrix.py`)
- **Map:** The road network is loaded from `data/model_town.graphml` (converted to an undirected MultiGraph to prevent dead-end trapping).
- **A\* Pathfinding:** `astar.py` calculates the shortest physical route for ambulances using a Haversine heuristic. 
- **Distance Matrix:** To avoid running A* for every single idle ambulance when a new event occurs, the system pre-computes an O(1) all-pairs shortest path distance matrix (`data/distance_matrix.npy`).

### 3. Dispatcher Brain (`src/simulation/dispatcher.py`, `src/simulation/assignment.py`)
Acts as the central command. It owns the queue of `active_events`. When a new emergency is ingested, it checks for idle ambulances and uses `assign_nearest_idle()` to find the closest one via the `distance_matrix`. It then computes the exact A* path for the chosen ambulance. It tracks on-scene service times and frees ambulances when they finish.

### 4. Event Spawner (`src/simulation/event_spawner.py`)
Simulates emergencies using a **Poisson distribution**. At each tick, it has a probability to spawn an `Accident` at a random node on the graph. 

### 5. Ambulance Agents (`src/simulation/ambulance.py`)
State machines that cycle between `IDLE`, `IN_TRANSIT`, and `ON_SCENE`. They follow pre-calculated paths node-by-node and interpolate their pixel positions between nodes for smooth rendering.

### 6. Metrics & Analytics (`src/simulation/metrics_tracker.py`)
Logs response times (Spawn Tick → Arrival Tick) for every event. It provides real-time stats (like Average Response Time and Fleet Utilization) to the HUD and exports `metrics_events.csv` and `metrics_summary.csv` to the `outputs/` directory when the simulation ends.

### 7. Visualization (`src/rendering/pygame_renderer.py`)
A highly optimized Pygame visualizer that renders:
- The static map background
- Ambulance sprites (color-coded by state: IDLE, IN_TRANSIT, ON_SCENE)
- Emergency locations (Red Xs)
- Dynamic dashed polylines representing the route an active ambulance is taking
- A real-time HUD and a detailed metrics overlay (toggled with `M`)

---

## File Structure

```text
resq-graph/
├── data/
│   ├── model_town.graphml       # Road network map data
│   ├── node_positions.json      # Pre-calculated pixel coordinates for nodes
│   ├── map_bg.png               # Visual map background
│   └── distance_matrix.npy      # Precomputed distance matrix (auto-generated)
├── outputs/                     # Generated CSV metrics go here
├── src/
│   ├── main.py                  # Entry point for the simulation
│   ├── config.py                # Hyperparameters, paths, and visual constants
│   ├── astar.py                 # Core A* navigation algorithm
│   ├── distance_matrix.py       # Distance matrix computation script
│   ├── rendering/
│   │   ├── pygame_renderer.py   # Pygame visualization logic
│   │   └── visualizer.py        # Legacy matplotlib visualizer
│   └── simulation/
│       ├── ambulance.py         # Ambulance class & state management
│       ├── assignment.py        # O(1) assignment and tie-breaking logic
│       ├── dispatcher.py        # Centralized dispatcher orchestrator
│       ├── event_spawner.py     # Poisson emergency generation
│       ├── metrics_tracker.py   # Data tracking & CSV export
│       └── simulation_engine.py # Main tick loop
└── tests/                       # Comprehensive Pytest test suite
```

## How to Run

Ensure you have a virtual environment set up with `pygame`, `networkx`, `numpy`, and `pytest` installed.

**Run the simulation:**
```bash
python src/main.py
```
- Press **Spacebar** to pause/resume.
- Press **M** to toggle the detailed metrics panel.

**Run the test suite:**
```bash
pytest tests/ -v
```

## AI Context Notes
If you are an AI reading this to write future code for this project:
- **Sprint 6 (Upcoming):** The focus will likely shift to fleet rebalancing. The `DispatcherBrain` already has a stubbed `rebalance_fleet()` method called every `REBALANCE_INTERVAL` ticks. This will involve using algorithms like K-Means clustering to reposition `IDLE` ambulances to high-risk areas.
- **Rendering:** `pygame_renderer.py` relies strictly on data passed to its `draw()` method. Do not put simulation state mutations inside the renderer.
- **Distance Matrix:** Never bypass `assignment.py` for calculating proximity. Always use the distance matrix for O(1) lookups to keep the simulation performant, falling back to Euclidean distance only if explicitly necessary.
- **Dependencies:** The graph is loaded as `nx.MultiGraph(G)` (undirected) to prevent ambulances from getting stuck in directed dead-ends.
