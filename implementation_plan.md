# Sprint 4 Implementation Plan: Simulation Engine & Ambulance Agents

**Sprint Goal:** Build a tick-based simulation loop with mobile ambulance agents, Poisson-driven accident spawning, and a real-time Pygame rendering engine.  
**Duration:** Week 4  
**Total Story Points:** 21  

---

## Table of Contents

1. [Sprint Overview](#sprint-overview)
2. [Architecture Overview](#architecture-overview)
3. [Prerequisites & Environment Setup](#prerequisites--environment-setup)
4. [US-013 – Ambulance Agent Class](#us-013--ambulance-agent-class)
5. [US-014 – Event Spawner (Poisson Distribution)](#us-014--event-spawner-poisson-distribution)
6. [US-015 – Main Simulation Loop](#us-015--main-simulation-loop)
7. [US-016 – Real-Time Live Visualization (Pygame)](#us-016--real-time-live-visualization-pygame)
8. [Integration & Cross-Cutting Concerns](#integration--cross-cutting-concerns)
9. [Testing Strategy](#testing-strategy)
10. [Definition of Done](#definition-of-done)
11. [Risk Register](#risk-register)
12. [Suggested File Structure](#suggested-file-structure)

---

## Sprint Overview

| User Story | Title | Points | Priority |
|---|---|---|---|
| US-013 | Ambulance Agent Class | 5 | High |
| US-014 | Event Spawner (Poisson) | 4 | High |
| US-015 | Main Simulation Loop | 6 | High |
| US-016 | Real-Time Visualization (Pygame) | 6 | Medium |
| **Total** | | **21** | |

---

## Architecture Overview

The simulation follows a layered, tick-based architecture:

```
Config Layer         →  src/config.py (TARGET_FPS, lambda, num_ambulances, etc.)
Data Layer           →  node_positions.json, map_bg.png, road graph
Agent Layer          →  Ambulance (state machine + A* navigation)
Event Layer          →  EventSpawner (Poisson process → Accident dataclass)
Simulation Core      →  SimulationEngine (tick loop, state management)
Dispatcher Layer     →  Basic dispatcher (assigns idle ambulances to events)
Rendering Layer      →  PygameRenderer (background, sprites, HUD)
```

All layers communicate through shared simulation state. The Pygame event loop wraps the simulation ticks so rendering, input handling, and logic are synchronised.

---

## Prerequisites & Environment Setup

### Dependencies

```bash
pip install pygame numpy scipy networkx
```

### Required Assets

- `data/map_bg.png` — background map image (target: 1200×900 px)
- `data/node_positions.json` — maps node IDs to `(x, y)` pixel coordinates
- `data/road_graph.json` (or equivalent) — adjacency list for A* pathfinding

### Configuration File (`src/config.py`)

```python
# Simulation
NUM_AMBULANCES   = 5
SIMULATION_TICKS = 10_000
TARGET_FPS       = 30
TICK_RATE        = 1          # simulated seconds per tick

# Event spawning
POISSON_LAMBDA   = 0.05       # average accidents per tick
PRIORITY_LEVELS  = [1, 2, 3]  # 1 = highest

# Rendering
WINDOW_WIDTH     = 1200
WINDOW_HEIGHT    = 900
REDRAW_INTERVAL  = 1          # redraw every N ticks

# Colours (R, G, B)
COLOUR_IDLE      = (0,   200,  0)
COLOUR_TRANSIT   = (255, 220,  0)
COLOUR_ON_SCENE  = (220,  30, 30)
COLOUR_ACCIDENT  = (255,   0,  0)
HUD_BG_COLOUR    = (20,  20,  20)
HUD_TEXT_COLOUR  = (255, 255, 255)
```

---

## US-013 – Ambulance Agent Class

**Story Points:** 5  
**Goal:** Represent individual ambulance agents with state, position, and navigation logic.

### State Machine

```
          assign_task()           arrive()
  IDLE ─────────────────► IN_TRANSIT ──────► ON_SCENE
   ▲                                              │
   └──────────────────────────────────────────────┘
                    complete_task()
```

| State | Description |
|---|---|
| `IDLE` | Stationary; eligible for dispatch |
| `IN_TRANSIT` | Moving along A* path toward destination |
| `ON_SCENE` | At accident location; handling the event |

### Properties

| Property | Type | Description |
|---|---|---|
| `id` | `int` | Unique identifier |
| `state` | `AmbulanceState` (Enum) | Current FSM state |
| `current_location` | `int` (node ID) | Current graph node |
| `pixel_pos` | `tuple[float, float]` | Interpolated pixel position for rendering |
| `current_path` | `list[int]` | Ordered list of node IDs to destination |
| `assigned_task` | `Accident \| None` | Currently assigned accident |
| `progress` | `float` | Interpolation progress between nodes (0.0–1.0) |
| `speed` | `float` | Nodes traversed per tick |

### Methods

```python
class AmbulanceState(Enum):
    IDLE       = "IDLE"
    IN_TRANSIT = "IN_TRANSIT"
    ON_SCENE   = "ON_SCENE"

class Ambulance:
    def navigate(self, destination: int) -> None:
        """Compute A* path from current_location to destination.
        Sets current_path and transitions state to IN_TRANSIT."""

    def update_position(self, node_positions: dict) -> None:
        """Called once per tick.
        - Advances progress along the edge between current_path[0] and current_path[1].
        - Interpolates pixel_pos between the two nodes' pixel coordinates.
        - When progress >= 1.0: pops the head node, resets progress.
        - When path is exhausted: sets current_location = destination, 
          transitions to ON_SCENE."""

    def get_status(self) -> dict:
        """Returns a snapshot dict: {id, state, location, pixel_pos, task_id}"""

    def complete_task(self) -> None:
        """Clears assigned_task, resets path, transitions to IDLE."""
```

### Pixel Position Interpolation

```python
def _interpolate_pixel(self, node_positions: dict) -> tuple[float, float]:
    """Linear interpolation between two adjacent node pixel positions.
    
    pixel_pos = start_px + progress * (end_px - start_px)
    
    Uses node_positions[node_id] = {"x": int, "y": int} from node_positions.json.
    """
```

### Tasks Breakdown

1. Define `AmbulanceState` enum.
2. Implement `Ambulance.__init__` with all properties.
3. Implement `navigate()` — integrate A* from Sprint 3 (or a stub returning shortest path).
4. Implement `update_position()` with smooth pixel interpolation.
5. Implement `get_status()` and `complete_task()`.
6. Write unit tests (see Testing Strategy).

---

## US-014 – Event Spawner (Poisson Distribution)

**Story Points:** 4  
**Goal:** Realistically generate emergency accident events using a Poisson process.

### Accident Dataclass

```python
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class Accident:
    id:        int
    timestamp: int           # simulation tick when spawned
    location:  int           # graph node ID
    pixel_pos: tuple[int, int]  # resolved from node_positions.json (for Pygame rendering)
    priority:  int           # 1 (high) – 3 (low)
    resolved:  bool = False
    assigned_ambulance_id: Optional[int] = None
```

`pixel_pos` is populated at spawn time by looking up the node in `node_positions.json`, making rendering stateless with respect to the graph.

### EventSpawner

```python
import numpy as np

class EventSpawner:
    def __init__(self, lambda_rate: float, node_positions: dict, rng_seed: int = None):
        self.lambda_rate    = lambda_rate       # avg accidents per tick
        self.node_positions = node_positions
        self.rng            = np.random.default_rng(rng_seed)
        self._next_id       = 0

    def spawn(self, current_tick: int) -> list[Accident]:
        """Draw n ~ Poisson(lambda_rate). Return n new Accident objects
        at random nodes with random priorities. Returns empty list if n == 0."""

    def set_lambda(self, new_lambda: float) -> None:
        """Hot-update rate parameter without restarting the simulation."""

    def _random_node(self) -> tuple[int, tuple[int, int]]:
        """Pick a random node ID and return (node_id, pixel_pos)."""
```

### Configurability

- `lambda_rate` is read from `src/config.py` at initialisation but can be changed at runtime via `set_lambda()`.
- Seed the RNG for reproducible runs during testing.
- Spawning logic lives entirely in `EventSpawner` — the simulation loop only calls `spawner.spawn(tick)`.

### Tasks Breakdown

1. Define `Accident` dataclass with `pixel_pos` field.
2. Implement `EventSpawner.__init__` and `spawn()` using `numpy` Poisson draw.
3. Implement `set_lambda()` for runtime configurability.
4. Write distribution tests to validate Poisson statistics.
5. Document configuration parameters.

---

## US-015 – Main Simulation Loop

**Story Points:** 6  
**Goal:** Drive all simulation components through a tick-based Pygame event loop.

### Simulation State

```python
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
```

### Tick Lifecycle

Each simulation tick executes the following steps **in order**:

```
1. Handle Pygame events
   ├── pygame.QUIT → exit loop cleanly
   ├── SPACE key   → toggle state.paused
   └── Other keys  → (extensible)

2. [If not paused] Update ambulance positions
   └── for each ambulance: ambulance.update_position(node_positions)

3. [If not paused] Spawn new events
   └── new_accidents = spawner.spawn(current_tick)
   └── state.active_events.extend(new_accidents)

4. [If not paused] Dispatch idle ambulances
   └── dispatcher.assign(state.ambulances, state.active_events)

5. [If not paused] Resolve on-scene ambulances
   └── Check if on-scene ambulances have completed service time
   └── Move resolved events to state.resolved_events
   └── Record response time

6. [If not paused] Update simulation state snapshot
   └── state.ambulance_positions = {a.id: a.pixel_pos for a in ambulances}
   └── state.current_tick += 1

7. Render (always — even when paused, to keep window responsive)
   └── renderer.draw(state, ambulances)

8. Clock tick
   └── clock.tick(TARGET_FPS)
```

### Main Loop Skeleton

```python
def run_simulation():
    pygame.init()
    screen  = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    clock   = pygame.time.Clock()
    
    node_positions = load_node_positions("data/node_positions.json")
    graph          = load_graph("data/road_graph.json")
    
    ambulances  = [Ambulance(id=i, start_node=..., graph=graph) for i in range(NUM_AMBULANCES)]
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
            # Steps 2–6
            _tick(state, ambulances, spawner, dispatcher, node_positions)
        
        # Step 7: Render
        renderer.draw(state, ambulances)
        clock.tick(TARGET_FPS)
    
    pygame.quit()
```

### Basic Dispatcher

A simple greedy dispatcher suffices for Sprint 4. It will be replaced by an optimised algorithm in a future sprint.

```python
class BasicDispatcher:
    def assign(self, ambulances: list[Ambulance], events: list[Accident]) -> None:
        """For each unassigned event, find the nearest IDLE ambulance and dispatch it."""
```

### Pause / Resume

- `SPACE` key toggles `state.paused`.
- While paused: Pygame events still drain (window stays responsive), rendering still runs.
- HUD displays `⏸ PAUSED` overlay when paused.

### Tasks Breakdown

1. Design and document tick lifecycle diagram.
2. Implement `SimulationState` dataclass.
3. Implement main Pygame event loop with quit and pause handling.
4. Implement `_tick()` function encapsulating steps 2–6.
5. Implement `BasicDispatcher`.
6. Integrate `Ambulance`, `EventSpawner`, dispatcher, and renderer.
7. Validate: loop runs 1000+ ticks without error.

---

## US-016 – Real-Time Live Visualization (Pygame)

**Story Points:** 6  
**Goal:** Render the simulation in a stable, informative Pygame window at ≥30 FPS.

### Renderer Architecture

```
PygameRenderer.draw(state, ambulances)
 ├── Layer 0: blit map_bg.png (static background)
 ├── Layer 1: draw accident markers (red X at pixel_pos)
 ├── Layer 2: draw ambulance sprites (coloured circles)
 ├── Layer 3: draw HUD panel (top-right)
 └── pygame.display.flip()
```

### Layer 0 — Background

- Load `data/map_bg.png` once at renderer init. Cache as `self.background`.
- Each tick: `screen.blit(self.background, (0, 0))`.
- This clears previous frame cheaply without `screen.fill()`.

### Layer 1 — Accident Markers

```
Red X drawn with two anti-aliased lines crossing at accident.pixel_pos.
Size: 12px arms, line width: 2px.
Only draw active (unresolved) accidents.
```

### Layer 2 — Ambulance Sprites

```
Ambulance rendered as a filled circle (radius 8px) + outline.

Colour coding:
  IDLE        → (0, 200, 0)    green
  IN_TRANSIT  → (255, 220, 0)  yellow
  ON_SCENE    → (220, 30, 30)  red

Draw at ambulance.pixel_pos (float coords → int for pygame).
Optionally draw ambulance ID as small text label above the circle.
```

### Layer 3 — HUD Panel

Position: top-right corner, semi-transparent dark background panel.

```
┌─────────────────────────────┐
│  Tick:           1042       │
│  Active Events:  3          │
│  Idle Ambulances: 2 / 5     │
│  Avg Response:   4.2 ticks  │
│                             │
│  [⏸ PAUSED]   (if paused)  │
└─────────────────────────────┘
```

Implementation notes:
- Render HUD to a dedicated `pygame.Surface` with `SRCALPHA` for transparency.
- Font: `pygame.font.SysFont("monospace", 16)` — pre-loaded once at init.
- Draw HUD surface with `screen.blit(hud_surface, (WINDOW_WIDTH - 260, 10))`.
- Only reconstruct HUD text each tick (font rendering is fast at this resolution).

### FPS Optimisation

| Technique | Benefit |
|---|---|
| Cache background surface | Avoids disk I/O and surface creation per tick |
| Pre-load font at init | Avoids `SysFont` overhead per tick |
| Use `clock.tick(TARGET_FPS)` | Caps loop to 30 FPS, saves CPU |
| `REDRAW_INTERVAL` config | Option to render every N ticks (set to 1 for real-time) |
| Dirty rect updates (optional) | Only redraw changed regions — implement if FPS drops below 30 |

### Performance Target

≥ 30 FPS at 1200×900 with 5 ambulances and λ=0.05 on development hardware.

### Tasks Breakdown

1. Implement `PygameRenderer.__init__`: load background, pre-load font.
2. Implement `draw_background()`.
3. Implement `draw_accidents()` with red X markers at `pixel_pos`.
4. Implement `draw_ambulances()` with colour-coded circles at `pixel_pos`.
5. Implement `draw_hud()` with semi-transparent panel and all four metrics.
6. Add `⏸ PAUSED` overlay when `state.paused == True`.
7. Profile FPS under full load; apply dirty rect optimisation if needed.

---

## Integration & Cross-Cutting Concerns

### Data Flow Between Components

```
node_positions.json
       │
       ├──► Ambulance.update_position()  (smooth interpolation)
       └──► EventSpawner.spawn()         (accident pixel_pos resolution)
                   │
                   └──► SimulationState.active_events
                                │
                                ├──► BasicDispatcher.assign()
                                └──► PygameRenderer.draw_accidents()

Ambulance.pixel_pos ──────────────► PygameRenderer.draw_ambulances()
SimulationState     ──────────────► PygameRenderer.draw_hud()
```

### A* Integration

US-013 depends on A* pathfinding from Sprint 3.  
- If A* is unavailable, stub `navigate()` to return `[start, end]` (direct edge) and mark with `# TODO: replace with A*`.
- The stub allows all other Sprint 4 work to proceed in parallel.

### Response Time Tracking

- When an ambulance is dispatched to an accident: record `dispatch_tick`.
- When the ambulance transitions to `ON_SCENE`: compute `response_time = current_tick - dispatch_tick`.
- Append to `state.total_response_times`.
- HUD displays `state.avg_response_time`.

### Graceful Shutdown

```python
try:
    run_simulation()
except KeyboardInterrupt:
    pass
finally:
    pygame.quit()
```

---

## Testing Strategy

### US-013 — Ambulance Unit Tests

| Test | Assertion |
|---|---|
| Initial state | State is `IDLE`, path is empty, pixel_pos equals start node |
| `navigate()` | Path is non-empty, state becomes `IN_TRANSIT` |
| `update_position()` — mid-edge | `pixel_pos` interpolated between two node coords |
| `update_position()` — path complete | State becomes `ON_SCENE`, `current_location` updated |
| `complete_task()` | State returns to `IDLE`, path and task cleared |

### US-014 — EventSpawner Tests

| Test | Assertion |
|---|---|
| Poisson distribution | Over 10,000 ticks, mean ≈ λ × ticks (within 5% tolerance) |
| Zero-spawn ticks | Fraction of empty ticks ≈ `e^(-λ)` |
| Accident attributes | `pixel_pos` is a valid `(int, int)`, priority in `{1,2,3}` |
| `set_lambda()` | Rate change reflected in subsequent spawn distribution |
| Determinism | Same seed → same sequence of accidents |

### US-015 — Simulation Loop Tests

| Test | Assertion |
|---|---|
| 1000-tick run | Completes without exception |
| Pause toggle | `state.current_tick` does not advance while paused |
| Dispatcher | After dispatch, ambulance is `IN_TRANSIT` and event has `assigned_ambulance_id` |
| State tracking | `ambulance_positions` dict updated every tick |

### US-016 — Renderer Tests (Manual / Smoke)

| Test | Method |
|---|---|
| Window opens | Visual check: 1200×900 window appears |
| Background renders | Map image visible as background |
| Ambulance colours | Green/yellow/red match state |
| Accident markers | Red X visible at accident node positions |
| HUD values update | Tick count increments live in HUD |
| FPS ≥ 30 | `clock.get_fps()` logged to console; verify ≥ 30 over 500 ticks |
| Pause overlay | ⏸ PAUSED text appears on SPACE, disappears on second SPACE |

---

## Definition of Done

A user story is complete when all of the following are satisfied:

- All acceptance criteria from both the original and Pygame-updated specification are met.
- Unit tests pass with ≥ 80% code coverage on agent and spawner logic.
- Code reviewed by at least one team member.
- No unhandled exceptions during a 1000+ tick run.
- Renderer sustains ≥ 30 FPS at 1200×900 during a 500-tick smoke test.
- `pixel_pos` is correctly interpolated or resolved for all visual elements.
- Code conforms to the project's style guide (PEP 8, type hints on all public methods).
- Sprint board card moved to Done.

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| A* from Sprint 3 not ready | Medium | High | Stub navigate() with direct path; unblock US-013 |
| FPS drops below 30 | Low | Medium | Profile early; use dirty rect rendering as fallback |
| `node_positions.json` format mismatch | Low | High | Define schema early; validate on load with assertion |
| Poisson lambda too high causing event flood | Medium | Low | Cap active events at configurable `MAX_ACTIVE_EVENTS`; log warning |
| Pygame surface blitting incorrect order | Low | Medium | Document layer order; use helper `draw_layers()` to enforce sequence |

---

## Suggested File Structure

```
resq-graph/
├── src/
│   ├── config.py                    # All constants and tunable parameters
│   ├── main.py                      # Entry point; calls run_simulation()
│   ├── simulation/
│   │   ├── __init__.py
│   │   ├── ambulance.py             # Ambulance class, AmbulanceState enum
│   │   ├── event_spawner.py         # EventSpawner, Accident dataclass
│   │   ├── simulation_engine.py     # SimulationState, run_simulation(), _tick()
│   │   └── dispatcher.py            # BasicDispatcher
│   ├── rendering/
│   │   ├── __init__.py
│   │   └── pygame_renderer.py       # PygameRenderer
│   └── astar.py                     # A* (from Sprint 3)
├── data/
│   ├── map_bg.png                   # Background map image
│   ├── node_positions.json
│   └── road_graph.json              # Or model_town.graphml
└── tests/
    ├── test_ambulance.py
    ├── test_event_spawner.py
    └── test_simulation_engine.py
```

---

*Plan prepared for Sprint 4 — Week 4. Review with the team at sprint planning before implementation begins.*