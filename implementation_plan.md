# Sprint 5 Implementation Plan: Dispatcher Logic & Task Assignment

**Sprint Goal:** Implement a centralized dispatch brain that assigns ambulances to emergencies, tracks response time metrics, and renders dispatch state in real time through the Pygame visualization layer.  
**Duration:** Week 5  
**Total Story Points:** 15  

---

## Table of Contents

1. [Sprint Overview](#sprint-overview)
2. [Architecture Overview](#architecture-overview)
3. [Prerequisites & Dependencies](#prerequisites--dependencies)
4. [US-017 – Dispatcher Brain Class](#us-017--dispatcher-brain-class)
5. [US-018 – Task Assignment Algorithm](#us-018--task-assignment-algorithm)
6. [US-019 – Response Time Metrics](#us-019--response-time-metrics)
7. [US-020 – Integrate Dispatcher into Simulation Loop](#us-020--integrate-dispatcher-into-simulation-loop)
8. [Pygame Rendering Extensions](#pygame-rendering-extensions)
9. [Integration & Cross-Cutting Concerns](#integration--cross-cutting-concerns)
10. [Testing Strategy](#testing-strategy)
11. [Definition of Done](#definition-of-done)
12. [Risk Register](#risk-register)
13. [Suggested File Structure](#suggested-file-structure)

---

## Sprint Overview

| User Story | Title | Points | Priority |
|---|---|---|---|
| US-017 | Dispatcher Brain Class | 5 | High |
| US-018 | Task Assignment Algorithm | 4 | High |
| US-019 | Response Time Metrics | 3 | Medium |
| US-020 | Integrate Dispatcher into Simulation Loop | 3 | High |
| **Total** | | **15** | |

---

## Architecture Overview

Sprint 5 inserts the `DispatcherBrain` between the simulation engine and the ambulance agents. It reads simulation state, makes assignment decisions, and writes back to both agent state and the renderer's path cache.

```
SimulationState
  │   active_events (unassigned)
  │   ambulances    (with states)
  ▼
DispatcherBrain
  ├── assign_task()         →  Ambulance.navigate()  →  A* path
  │                         →  pixel_polyline cached for renderer
  ├── rebalance_fleet()     →  idle ambulances repositioned
  └── metrics_tracker       →  MetricsTracker (logs + HUD + CSV)
  ▼
PygameRenderer
  ├── draws dashed polyline per assigned ambulance
  ├── HUD: live ART display
  └── M key: toggle detailed metrics panel
```

All dispatcher logic is isolated in `src/simulation/dispatcher.py`. The simulation loop calls a single `dispatcher.tick(state)` method each tick.

---

## Prerequisites & Dependencies

### From Sprint 4 (must be complete or stubbed)

| Dependency | Required For |
|---|---|
| `Ambulance` class with `navigate()`, `update_position()`, state machine | US-017, US-018, US-020 |
| `Accident` dataclass with `timestamp`, `location`, `pixel_pos`, `priority` | US-017, US-018, US-019 |
| `SimulationState` with `active_events`, `ambulance_positions` | US-020 |
| `PygameRenderer` with HUD panel and `draw_ambulances()` | US-019, US-020 Pygame extensions |
| `node_positions.json` loaded and accessible | US-018 pixel polyline |
| Distance matrix (`.npy`) from Sprint 1 | US-018 nearest-ambulance lookup |
| A* pathfinder from Sprint 2 | US-018 path computation |

### New Configuration Parameters (`config.py` additions)

```python
# Dispatcher
REBALANCE_INTERVAL   = 50        # ticks between fleet rebalance calls
SCENE_SERVICE_TICKS  = 10        # ticks ambulance spends ON_SCENE before completing

# Metrics
METRICS_CSV_PATH     = "output/metrics.csv"
METRICS_FLUSH_INTERVAL = 100     # write to CSV every N ticks

# Rendering
DASHED_LINE_COLOUR   = (100, 180, 255)   # light blue for path polylines
DASHED_SEGMENT_LEN   = 8                 # pixels per dash segment
DASHED_GAP_LEN       = 5                 # pixels per gap
METRICS_PANEL_WIDTH  = 300
METRICS_PANEL_HEIGHT = 220
```

---

## US-017 – Dispatcher Brain Class

**Story Points:** 5  
**Goal:** Centralized coordinator that tracks simulation state and makes dispatch decisions.

### Responsibilities

The `DispatcherBrain` owns three concerns:
1. Maintaining an up-to-date view of which events are unassigned and which ambulances are idle.
2. Making and recording assignment decisions.
3. Triggering periodic fleet rebalancing.

### Class Design

```python
from dataclasses import dataclass, field
from typing import Optional

class DispatcherBrain:
    def __init__(self, ambulances: list, distance_matrix: np.ndarray,
                 node_index: dict, node_positions: dict):
        self.ambulances       = ambulances          # reference to agent list
        self.distance_matrix  = distance_matrix     # pre-computed O(1) lookup
        self.node_index       = node_index          # node_id → matrix row/col
        self.node_positions   = node_positions      # node_id → pixel (x, y)
        self.active_events:   list[Accident] = []
        self.assigned_events: dict[int, int] = {}   # event_id → ambulance_id
        self.metrics_tracker  = MetricsTracker()
        self._ticks_since_rebalance = 0

    def tick(self, new_events: list[Accident], current_tick: int) -> None:
        """Called once per simulation tick. Ingests new events,
        assigns idle ambulances, checks for completions, and
        triggers rebalancing on schedule."""

    def assign_task(self, ambulance: Ambulance, event: Accident,
                    current_tick: int) -> None:
        """Assign a single event to a single ambulance.
        Computes A* path, caches pixel polyline on ambulance,
        marks event as assigned, records dispatch_tick on event."""

    def rebalance_fleet(self, current_tick: int) -> None:
        """Move idle ambulances toward demand centre.
        Sprint 5: stub implementation — move idle ambulances to
        their current base (no-op). Full K-Means rebalancing
        implemented in Sprint 6."""

    def complete_event(self, ambulance: Ambulance,
                       current_tick: int) -> None:
        """Called when ambulance finishes ON_SCENE service.
        Records arrival_tick, computes response time,
        transitions ambulance to IDLE."""

    def get_idle_ambulances(self) -> list[Ambulance]:
        """Return all ambulances in IDLE state."""

    def get_unassigned_events(self) -> list[Accident]:
        """Return active events with no assigned ambulance."""
```

### Internal Tick Flow

```
dispatcher.tick(new_events, current_tick)
  │
  ├── 1. Add new_events to active_events
  │
  ├── 2. Check on-scene ambulances → complete if service time elapsed
  │        └── complete_event(ambulance, current_tick)
  │
  ├── 3. For each unassigned event:
  │        └── find nearest idle ambulance → assign_task()
  │
  ├── 4. _ticks_since_rebalance += 1
  │        └── if >= REBALANCE_INTERVAL: rebalance_fleet()
  │
  └── 5. metrics_tracker.snapshot(current_tick, active_events, ambulances)
```

### Tasks Breakdown

1. Define `DispatcherBrain.__init__` with all properties and collaborators.
2. Implement `tick()` orchestration method.
3. Implement `get_idle_ambulances()` and `get_unassigned_events()` helpers.
4. Implement `complete_event()` with response time handoff to `MetricsTracker`.
5. Stub `rebalance_fleet()` with a no-op (Sprint 6 replaces this).
6. Write unit tests for dispatcher state transitions.

---

## US-018 – Task Assignment Algorithm

**Story Points:** 4  
**Goal:** Find the optimal ambulance-to-event assignment using the distance matrix, then compute and cache the visual path for the renderer.

### Assignment Algorithm

```
assign_nearest_idle(event, idle_ambulances, distance_matrix, node_index):

  1. For each idle ambulance a_i:
       d_i = distance_matrix[node_index[a_i.current_location]]
                             [node_index[event.location]]

  2. best = ambulance with minimum d_i
     Tie-breaking: if d_i == d_j, choose lower ambulance_id (deterministic)

  3. Call dispatcher.assign_task(best, event, current_tick)
```

### `assign_task()` Implementation Detail

```python
def assign_task(self, ambulance: Ambulance, event: Accident,
                current_tick: int) -> None:
    # 1. Compute A* path (list of node IDs)
    path = astar(self.graph, ambulance.current_location, event.location)

    # 2. Pre-compute pixel polyline and cache on ambulance
    #    pixel_polyline: list of (x, y) tuples, one per node in path
    ambulance.pixel_polyline = [
        (self.node_positions[n]["x"], self.node_positions[n]["y"])
        for n in path
    ]

    # 3. Set ambulance navigation state
    ambulance.navigate(destination=event.location, path=path)

    # 4. Mark event as assigned
    event.assigned_ambulance_id = ambulance.id
    event.dispatch_tick = current_tick
    self.assigned_events[event.id] = ambulance.id
```

### Pixel Polyline Caching

The pixel polyline is pre-computed at dispatch time and stored directly on the `Ambulance` object as `ambulance.pixel_polyline`. This keeps the renderer stateless — it simply iterates `ambulance.pixel_polyline` to draw the dashed line without touching the graph or node positions at render time.

- Polyline is cleared (`ambulance.pixel_polyline = []`) when the ambulance completes the event and returns to IDLE.
- If the ambulance re-routes (Sprint 7), `assign_task()` is called again and the polyline is replaced.

### Ambulance Class Addition (Sprint 4 extension)

```python
class Ambulance:
    # Add to existing properties:
    pixel_polyline: list[tuple[int, int]] = field(default_factory=list)
    dispatch_tick:  Optional[int] = None
```

### Edge Cases

| Case | Handling |
|---|---|
| No idle ambulances | Event remains in `active_events`; retried next tick |
| Event location unreachable via A* | Event logged as `UNREACHABLE`; removed from queue; warning emitted |
| Ambulance already has a task | Guarded by `get_idle_ambulances()` filter; cannot be double-assigned |
| Distance matrix missing node | KeyError caught; fallback to Euclidean pixel distance |

### Tasks Breakdown

1. Implement `assign_nearest_idle()` as a standalone function in `src/simulation/assignment.py`.
2. Integrate tie-breaking by `ambulance_id`.
3. Implement pixel polyline computation in `assign_task()`.
4. Add `pixel_polyline` and `dispatch_tick` fields to `Ambulance`.
5. Handle all edge cases with logging.
6. Write tests covering tie-breaking, unreachable nodes, and empty idle pool.

---

## US-019 – Response Time Metrics

**Story Points:** 3  
**Goal:** Log, compute, and surface response time data both to CSV and to the live Pygame HUD.

### Metric Definitions

| Metric | Formula |
|---|---|
| Response Time (per event) | `arrival_tick − dispatch_tick` (ticks) |
| Average Response Time (ART) | `mean(all recorded response_times)` |
| Events Processed | Count of resolved events |
| Events Pending | Count of active unassigned events |
| Fleet Utilisation | `(non-idle ambulances / total ambulances) × 100%` |

### MetricsTracker Class

```python
import csv
from collections import deque

class MetricsTracker:
    def __init__(self, csv_path: str, flush_interval: int = 100):
        self.csv_path        = csv_path
        self.flush_interval  = flush_interval
        self.response_times: list[float] = []
        self._buffer:        list[dict]  = []
        self._tick_history:  deque       = deque(maxlen=200)  # for HUD sparkline

    def record_response(self, event_id: int, dispatch_tick: int,
                        arrival_tick: int) -> None:
        """Compute and store one response time entry."""
        rt = arrival_tick - dispatch_tick
        self.response_times.append(rt)
        self._buffer.append({
            "event_id":      event_id,
            "dispatch_tick": dispatch_tick,
            "arrival_tick":  arrival_tick,
            "response_time": rt
        })

    @property
    def art(self) -> float:
        return sum(self.response_times) / len(self.response_times) \
               if self.response_times else 0.0

    def snapshot(self, current_tick: int, active_events: list,
                 ambulances: list) -> None:
        """Record per-tick aggregate metrics for HUD display."""
        self._tick_history.append({
            "tick":         current_tick,
            "art":          self.art,
            "active":       len(active_events),
            "utilisation":  self._utilisation(ambulances)
        })

    def flush_csv(self) -> None:
        """Append buffered event rows to CSV. Called every METRICS_FLUSH_INTERVAL ticks."""

    def export_summary_csv(self) -> None:
        """Write final summary (ART, std dev, total events) to a separate summary CSV."""

    def get_hud_data(self) -> dict:
        """Return dict consumed by PygameRenderer HUD and metrics panel."""
        return {
            "art":           round(self.art, 2),
            "total_events":  len(self.response_times),
            "latest_rt":     self.response_times[-1] if self.response_times else 0,
            "tick_history":  list(self._tick_history)
        }
```

### CSV Output Format

**Per-event log (`metrics_events.csv`):**
```
event_id, dispatch_tick, arrival_tick, response_time, priority, location_node
```

**Summary log (`metrics_summary.csv`):**
```
total_events, art, std_dev, min_rt, max_rt, simulation_ticks
```

### Pygame HUD Integration

The existing HUD panel (Sprint 4, top-right) gains a live ART line:

```
┌─────────────────────────────────┐
│  Tick:              1042        │
│  Active Events:     3           │
│  Idle Ambulances:   2 / 5       │
│  Avg Response Time: 6.4 ticks   │  ← NEW
│  Events Resolved:   47          │  ← NEW
│  Fleet Utilisation: 60%         │  ← NEW
└─────────────────────────────────┘
```

### Metrics Panel (M Key Toggle)

Pressing **M** toggles a larger semi-transparent overlay panel displaying detailed metrics:

```
┌──────────────────────────────────────────┐
│         METRICS PANEL  [M to close]      │
│                                          │
│  Average Response Time : 6.4 ticks       │
│  Std Deviation         : 1.8 ticks       │
│  Fastest Response      : 2 ticks         │
│  Slowest Response      : 14 ticks        │
│  Total Events Resolved : 47              │
│  Total Events Pending  : 3               │
│  Fleet Utilisation     : 60%             │
│                                          │
│  Last 5 Response Times:                  │
│  [5, 7, 6, 8, 4]                         │
└──────────────────────────────────────────┘
```

Implementation notes:
- Panel rendered to a `pygame.Surface` with `SRCALPHA`.
- `show_metrics_panel` boolean toggled on `pygame.KEYDOWN` with `event.key == pygame.K_m`.
- Panel drawn on top of all other layers when active.
- `MetricsTracker.get_hud_data()` supplies all values — renderer does no computation.

### Tasks Breakdown

1. Implement `MetricsTracker` class with all methods.
2. Implement `flush_csv()` and `export_summary_csv()`.
3. Wire `record_response()` into `dispatcher.complete_event()`.
4. Wire `get_hud_data()` into `PygameRenderer.draw_hud()`.
5. Implement metrics panel surface in `PygameRenderer`.
6. Add M key toggle to the Pygame event loop.

---

## US-020 – Integrate Dispatcher into Simulation Loop

**Story Points:** 3  
**Goal:** Wire `DispatcherBrain` into the existing tick loop from Sprint 4, add dashed path rendering, and verify the full system runs 1000+ ticks cleanly.

### Updated Tick Lifecycle

The Sprint 4 tick lifecycle gains two new steps (marked **NEW**):

```
Each tick:
  1. Handle Pygame events
     ├── QUIT          → exit
     ├── SPACE         → pause/resume
     └── M             → toggle metrics panel  ← NEW

  2. [If not paused] Update ambulance positions
     └── ambulance.update_position(node_positions)

  3. [If not paused] Spawn new events
     └── new_accidents = spawner.spawn(current_tick)

  4. [If not paused] Dispatcher tick                 ← NEW
     └── dispatcher.tick(new_accidents, current_tick)
         ├── complete on-scene ambulances
         ├── assign idle ambulances to unassigned events
         └── snapshot metrics

  5. [If not paused] Update simulation state snapshot
     └── state.current_tick += 1

  6. Render
     ├── draw_background()
     ├── draw_accidents()
     ├── draw_ambulance_paths()    ← NEW (dashed polylines)
     ├── draw_ambulances()
     ├── draw_hud()
     └── draw_metrics_panel()     ← NEW (if toggled)

  7. clock.tick(TARGET_FPS)
```

Note: step 3 (spawn) now passes `new_accidents` directly into `dispatcher.tick()` rather than appending to `state.active_events` independently. The dispatcher becomes the single owner of the active events list.

### Dashed Path Rendering

`PygameRenderer.draw_ambulance_paths(ambulances)` iterates over all ambulances that have a non-empty `pixel_polyline` and draws a dashed line connecting the waypoints.

```python
def draw_ambulance_paths(self, ambulances: list) -> None:
    for amb in ambulances:
        if not amb.pixel_polyline or amb.state == AmbulanceState.IDLE:
            continue
        colour = DASHED_LINE_COLOUR
        self._draw_dashed_polyline(self.screen, colour, amb.pixel_polyline)

def _draw_dashed_polyline(self, surface, colour: tuple,
                           points: list[tuple]) -> None:
    """Draw a multi-segment dashed line through a list of (x,y) points.
    Dashes are DASHED_SEGMENT_LEN px, gaps are DASHED_GAP_LEN px."""
    for i in range(len(points) - 1):
        self._draw_dashed_segment(surface, colour, points[i], points[i+1])

def _draw_dashed_segment(self, surface, colour, p1, p2) -> None:
    """Interpolate dashes between two points."""
    import math
    dx, dy  = p2[0]-p1[0], p2[1]-p1[1]
    length  = math.hypot(dx, dy)
    if length == 0:
        return
    ux, uy  = dx/length, dy/length
    step    = DASHED_SEGMENT_LEN + DASHED_GAP_LEN
    pos     = 0.0
    drawing = True
    while pos < length:
        end = min(pos + DASHED_SEGMENT_LEN, length)
        if drawing:
            start_pt = (int(p1[0] + ux*pos), int(p1[1] + uy*pos))
            end_pt   = (int(p1[0] + ux*end), int(p1[1] + uy*end))
            pygame.draw.line(surface, colour, start_pt, end_pt, 2)
        pos    += step
        drawing = not drawing
```

The dashed line is drawn in Layer 2 (between accident markers and ambulance sprites) so sprites always appear on top of paths.

### Updated Render Layer Order

```
Layer 0: Background (map_bg.png)
Layer 1: Accident markers (red X)
Layer 2: Ambulance path polylines (dashed blue)   ← NEW
Layer 3: Ambulance sprites (coloured circles)
Layer 4: HUD panel (top-right)
Layer 5: Metrics panel (full overlay, M key)       ← NEW
```

### Integration Checklist

- [ ] `DispatcherBrain` instantiated in `run_simulation()` before loop starts.
- [ ] `spawner.spawn()` result passed to `dispatcher.tick()` each tick.
- [ ] `dispatcher` no longer bypassed — simulation loop does not touch `active_events` directly.
- [ ] `draw_ambulance_paths()` called in renderer each tick after `draw_accidents()`.
- [ ] `show_metrics_panel` flag threaded from event handler to renderer.
- [ ] `metrics_tracker.flush_csv()` called every `METRICS_FLUSH_INTERVAL` ticks.
- [ ] `metrics_tracker.export_summary_csv()` called on loop exit.
- [ ] 1000-tick smoke test passes with no unhandled exceptions.

### Tasks Breakdown

1. Instantiate `DispatcherBrain` in `run_simulation()` with distance matrix and node positions.
2. Refactor tick loop to route new events through `dispatcher.tick()`.
3. Add M key handler and `show_metrics_panel` flag to event loop.
4. Implement `draw_ambulance_paths()` and `_draw_dashed_polyline()` in renderer.
5. Add metrics panel draw call guarded by `show_metrics_panel`.
6. Wire CSV flush and summary export on simulation exit.
7. Run 1000-tick smoke test; verify no exceptions and ART is non-zero.

---

## Pygame Rendering Extensions

This section consolidates all Sprint 5 visual additions for the renderer developer.

### Summary of New Renderer Methods

| Method | Layer | Trigger |
|---|---|---|
| `draw_ambulance_paths(ambulances)` | Layer 2 | Every tick |
| `draw_metrics_panel(hud_data)` | Layer 5 | When `show_metrics_panel == True` |
| Updated `draw_hud()` | Layer 4 | Every tick (adds ART, resolved count, utilisation) |

### HUD Delta from Sprint 4

Add three new lines to the existing HUD surface (no layout restructuring needed):
```
Avg Response Time: X.X ticks
Events Resolved:   N
Fleet Utilisation: X%
```

### Metrics Panel Dimensions

- Width: `METRICS_PANEL_WIDTH = 300` px
- Height: `METRICS_PANEL_HEIGHT = 220` px
- Position: centred on screen — `((WINDOW_WIDTH - 300)//2, (WINDOW_HEIGHT - 220)//2)`
- Background: RGBA `(20, 20, 20, 210)` — dark, semi-transparent
- Font: same monospace font as HUD, size 15

---

## Integration & Cross-Cutting Concerns

### Ownership of `active_events`

In Sprint 4, `SimulationState.active_events` was written by the spawner and read by the renderer. In Sprint 5, `DispatcherBrain` becomes the sole owner:

| Component | Sprint 4 | Sprint 5 |
|---|---|---|
| Writes new events | Simulation loop | `dispatcher.tick()` |
| Reads unassigned events | Renderer (direct) | `dispatcher.get_unassigned_events()` |
| Removes resolved events | Simulation loop | `dispatcher.complete_event()` |

The renderer reads `dispatcher.active_events` (a reference) — no copy needed.

### Response Time Formula Clarification

```
Response Time (Total) = arrival_tick - spawn_tick
```

*   `spawn_tick`: Tick when the event was generated by the Poisson spawner.
*   `dispatch_tick`: Tick when `assign_task()` was called.
*   `arrival_tick`: Tick when ambulance arrives on scene (reaches destination).

US-019 requires `spawn_time - arrival_time` (assumed to be `arrival_tick - spawn_tick` for positive values). We will track:
1.  **Queue Time**: `dispatch_tick - spawn_tick`
2.  **Travel Time**: `arrival_tick - dispatch_tick`
3.  **Total Response Time**: `arrival_tick - spawn_tick` (This is the primary ART metric).

Wait time ON_SCENE (`SCENE_SERVICE_TICKS`) is not part of the response time.

### A* Path Freshness

In Sprint 5, paths are computed once at dispatch time and not updated mid-transit. Re-routing on congestion is a Sprint 7 concern. Document this limitation with a `# TODO Sprint 7: re-route on congestion` comment in `assign_task()`.

---

## Testing Strategy

### US-017 — DispatcherBrain Unit Tests

| Test | Assertion |
|---|---|
| New event ingested | Appears in `active_events` after `tick()` |
| Idle ambulance assigned | State transitions to `IN_TRANSIT`; event has `assigned_ambulance_id` |
| No idle ambulances | Event stays unassigned; no exception raised |
| `complete_event()` | Ambulance returns to IDLE; response time recorded in tracker |
| Rebalance interval | `rebalance_fleet()` called exactly once per `REBALANCE_INTERVAL` ticks |

### US-018 — Assignment Algorithm Tests

| Test | Assertion |
|---|---|
| Nearest ambulance selected | Ambulance with shortest distance matrix distance is chosen |
| Tie-breaking | Lowest `ambulance_id` wins when distances are equal |
| Pixel polyline populated | `ambulance.pixel_polyline` is non-empty after assignment |
| Polyline cleared on completion | `ambulance.pixel_polyline == []` after `complete_event()` |
| Unreachable node | Event logged as UNREACHABLE; no exception; queue length unchanged |

### US-019 — Metrics Tests

| Test | Assertion |
|---|---|
| `record_response()` | `art` updates correctly after each call |
| ART of zero events | Returns 0.0 without division error |
| CSV buffer flush | Rows written equal recorded events after flush |
| `get_hud_data()` | Returns all required keys; no KeyError in renderer |

### US-020 — Integration Tests

| Test | Assertion |
|---|---|
| 1000-tick run | Completes without exception |
| Dashed line visible | `pixel_polyline` non-empty for IN_TRANSIT ambulances |
| M key toggle | `show_metrics_panel` flips True/False on each keypress |
| CSV created on exit | `metrics_events.csv` and `metrics_summary.csv` exist and are non-empty |
| ART > 0 after 100 ticks | At least one event resolved; ART is a positive number |

---

## Definition of Done

A user story is complete when all of the following are satisfied:

- All acceptance criteria from both the original and Pygame-updated specification are met.
- Unit tests pass; dispatcher and assignment logic have ≥ 80% coverage.
- Code reviewed by at least one team member.
- Full simulation loop runs 1000+ ticks without unhandled exceptions.
- Dashed path polylines visible in Pygame window for IN_TRANSIT ambulances.
- Live ART displayed in HUD; M key toggles detailed metrics panel correctly.
- `metrics_events.csv` and `metrics_summary.csv` written on simulation exit.
- No direct access to `active_events` from outside `DispatcherBrain`.
- Sprint board card moved to Done.

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Distance matrix node index mismatch | Medium | High | Validate node_index keys against graph on load; assert coverage |
| A* returns empty path for valid nodes | Low | High | Fallback: log warning, mark event UNREACHABLE, continue |
| Dashed line rendering drops FPS below 30 | Low | Medium | Pre-compute total dash points at dispatch time; cache as flat list |
| Double-assignment race condition | Low | High | Guard `assign_task()` with idle-state check immediately before call |
| CSV write blocking main loop | Low | Low | Buffer writes; flush async or every N ticks, never every tick |
| Metrics panel obscures map at bad position | Low | Low | Centre panel; add close instruction in panel text |

---

## Suggested File Structure

```
src/
├── config.py                          # Updated: dispatcher + metrics + render constants
├── main.py                            # Updated: instantiates DispatcherBrain
├── astar.py                           # Unchanged from Sprint 2/4
├── distance_matrix.py                 # From Sprint 1
├── simulation/
│   ├── ambulance.py                   # Updated: pixel_polyline, dispatch_tick fields
│   ├── event_spawner.py               # Unchanged from Sprint 4
│   ├── simulation_engine.py           # Updated: routes events through dispatcher.tick()
│   ├── dispatcher.py                  # NEW: DispatcherBrain class (replaces BasicDispatcher)
│   ├── assignment.py                  # NEW: assign_nearest_idle(), tie-breaking logic
│   └── metrics_tracker.py             # NEW: MetricsTracker, CSV export
├── rendering/
│   └── pygame_renderer.py             # Updated: dashed paths, metrics panel, HUD delta
data/
├── node_positions.json
├── model_town.graphml                 # Road graph
└── distance_matrix.npy                # From Sprint 1
outputs/
├── metrics_events.csv                 # Generated at runtime
└── metrics_summary.csv                # Generated on exit
└── tests/
    ├── test_dispatcher_brain.py       # NEW
    ├── test_assignment.py             # NEW
    ├── test_metrics_tracker.py        # NEW
    ├── test_ambulance.py              # From Sprint 4
    └── test_simulation_engine.py      # Updated: includes dispatcher integration
```

---

*Plan prepared for Sprint 5 — Week 5. Depends on Sprint 4 deliverables: Ambulance class, EventSpawner, SimulationState, and PygameRenderer base implementation.*