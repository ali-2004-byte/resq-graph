"""
dispatcher.py – Sprint 5 (US-017)

DispatcherBrain: centralised coordinator that owns the active event queue,
makes ambulance-to-event assignments, tracks on-scene timers, triggers
periodic fleet rebalancing, and hands off data to MetricsTracker.

Replaces the Sprint 4 BasicDispatcher stub.
"""
import logging
from typing import Optional

import numpy as np
import math

from src.simulation.ambulance import Ambulance, AmbulanceState
from src.simulation.event_spawner import Accident
from src.simulation.assignment import assign_nearest_idle
from src.simulation.metrics_tracker import MetricsTracker
from src.astar import astar
from src.config import REBALANCE_INTERVAL, SCENE_SERVICE_TICKS

logger = logging.getLogger(__name__)


class DispatcherBrain:
    """Central dispatch coordinator for the ResQ-Graph simulation.

    Owns three concerns:
    1. Maintaining an up-to-date view of unassigned events and idle ambulances.
    2. Making and recording assignment decisions (nearest-idle with A* path).
    3. Tracking on-scene service timers and triggering periodic rebalancing.

    The simulation loop calls ``dispatcher.tick(new_events, current_tick)``
    once per tick; no other component touches the active-events list directly.
    """

    def __init__(
        self,
        ambulances:      list[Ambulance],
        distance_matrix: np.ndarray,
        node_index:      dict,
        node_positions:  dict,
        graph,
    ):
        self.ambulances      = ambulances
        self.distance_matrix = distance_matrix
        self.node_index      = node_index
        self.node_positions  = node_positions
        self.graph           = graph

        self.active_events:   list[Accident]  = []
        self.assigned_events: dict[int, int]  = {}   # event_id → ambulance_id
        self.metrics_tracker                  = MetricsTracker()

        self._ticks_since_rebalance = 0
        # ambulance_id → tick the ambulance entered ON_SCENE
        self._on_scene_since: dict[int, int] = {}

    # ── Main tick entry point ──────────────────────────────────────────────────

    def tick(self, new_events: list[Accident], current_tick: int) -> None:
        """Called once per simulation tick by the engine.

        Order of operations
        -------------------
        1. Ingest new events.
        2. Check on-scene ambulances; complete if service time has elapsed.
        3. Assign nearest idle ambulance to each unassigned event.
        4. Increment rebalance counter; call rebalance_fleet() on schedule.
        5. Snapshot metrics.
        """
        # 1. Add new events to the active queue (filtering unreachable ones)
        for event in new_events:
            reachable = False
            for amb in self.ambulances:
                try:
                    i = self.node_index[amb.current_location]
                    j = self.node_index[event.location]
                    if not math.isinf(float(self.distance_matrix[i][j])):
                        reachable = True
                        break
                except KeyError:
                    reachable = True
                    break
            
            if reachable:
                self.active_events.append(event)
            else:
                event.assigned_ambulance_id = -1
                logger.debug("Event %d is completely unreachable by fleet.", event.id)

        # 2. Check on-scene ambulances
        for amb in self.ambulances:
            if amb.state == AmbulanceState.ON_SCENE:
                if amb.id not in self._on_scene_since:
                    self._on_scene_since[amb.id] = current_tick
                elif current_tick - self._on_scene_since[amb.id] >= SCENE_SERVICE_TICKS:
                    self.complete_event(amb, current_tick)

        # 3. Assign idle ambulances to unassigned events
        for event in self.get_unassigned_events():
            idle = self.get_idle_ambulances()
            if not idle:
                break
            best = assign_nearest_idle(
                event, idle, self.distance_matrix, self.node_index
            )
            if best is not None:
                self.assign_task(best, event, current_tick)

        # 4. Periodic rebalancing
        self._ticks_since_rebalance += 1
        if self._ticks_since_rebalance >= REBALANCE_INTERVAL:
            self.rebalance_fleet(current_tick)
            self._ticks_since_rebalance = 0

        # 5. Metrics snapshot
        self.metrics_tracker.snapshot(
            current_tick, self.active_events, self.ambulances
        )

    # ── Core dispatcher actions ────────────────────────────────────────────────

    def assign_task(
        self, ambulance: Ambulance, event: Accident, current_tick: int
    ) -> None:
        """Assign *event* to *ambulance*.

        Steps
        -----
        1. Guard: skip if ambulance is no longer idle.
        2. Compute A* path from ambulance's current location to event location.
        3. Pre-compute pixel polyline and cache it on the ambulance for the renderer.
        4. Set ambulance navigation state.
        5. Mark event as assigned and record dispatch tick.
        """
        # Guard: only assign if still idle
        if ambulance.state != AmbulanceState.IDLE:
            return

        # 1. Compute A* path
        # TODO Sprint 7: re-route on congestion
        path = astar(self.graph, ambulance.current_location, event.location)

        if path is None:
            logger.warning(
                "Event %d at node %d is UNREACHABLE from ambulance %d at node %d. "
                "Skipping assignment.",
                event.id, event.location, ambulance.id, ambulance.current_location,
            )
            # Mark as unreachable so it is not retried
            event.assigned_ambulance_id = -1
            return

        # 2. Pre-compute pixel polyline and cache on ambulance
        ambulance.pixel_polyline = [
            self._node_to_pixel(n)
            for n in path
            if n in self.node_positions
        ]

        # 3. Set ambulance navigation state (path already computed above)
        ambulance.navigate(destination=event.location, path=path)
        ambulance.assigned_task  = event
        ambulance.dispatch_tick  = current_tick

        # 4. Mark event as assigned
        event.assigned_ambulance_id = ambulance.id
        event.dispatch_tick         = current_tick
        self.assigned_events[event.id] = ambulance.id

        logger.debug(
            "Ambulance %d → Event %d (tick %d, path length %d).",
            ambulance.id, event.id, current_tick, len(path),
        )

    def rebalance_fleet(self, current_tick: int) -> None:
        """Stub: no-op in Sprint 5.  Sprint 6 replaces this with K-Means."""
        pass

    def complete_event(self, ambulance: Ambulance, current_tick: int) -> None:
        """Called when an ambulance finishes ON_SCENE service.

        Records response time, resets ambulance to IDLE, and removes the
        resolved event from the active queue.
        """
        task = ambulance.assigned_task

        if task and not task.resolved:
            spawn_tick    = task.timestamp
            dispatch_tick = getattr(task, "dispatch_tick", current_tick)

            self.metrics_tracker.record_response(
                event_id      = task.id,
                spawn_tick    = spawn_tick,
                dispatch_tick = dispatch_tick,
                arrival_tick  = current_tick,
                priority      = task.priority,
                location_node = task.location,
            )
            task.resolved = True

            # Remove from active queue
            self.active_events = [
                e for e in self.active_events if e.id != task.id
            ]
            if task.id in self.assigned_events:
                del self.assigned_events[task.id]

        # Reset ambulance
        ambulance.assigned_task  = None
        ambulance.current_path   = []
        ambulance.pixel_polyline = []
        ambulance.dispatch_tick  = None
        ambulance.state          = AmbulanceState.IDLE
        ambulance.progress       = 0.0

        # Clear on-scene timer
        self._on_scene_since.pop(ambulance.id, None)

        logger.debug(
            "Ambulance %d completed task at tick %d; returning to IDLE.",
            ambulance.id, current_tick,
        )

    # ── State query helpers ────────────────────────────────────────────────────

    def get_idle_ambulances(self) -> list[Ambulance]:
        """Return all ambulances currently in IDLE state."""
        return [a for a in self.ambulances if a.state == AmbulanceState.IDLE]

    def get_unassigned_events(self) -> list[Accident]:
        """Return active events that have no ambulance assigned and are not resolved."""
        return [
            e for e in self.active_events
            if e.assigned_ambulance_id is None and not e.resolved
        ]

    # ── Private helpers ────────────────────────────────────────────────────────

    def _node_to_pixel(self, node_id: int) -> tuple[int, int]:
        """Convert a graph node ID to pixel coordinates.

        Handles both list/tuple ``[x, y]`` and dict ``{"x": ..., "y": ...}``
        node_positions formats.
        """
        pos = self.node_positions[node_id]
        if isinstance(pos, dict):
            return (int(pos.get("x", pos.get(0, 0))), int(pos.get("y", pos.get(1, 0))))
        return (int(pos[0]), int(pos[1]))
