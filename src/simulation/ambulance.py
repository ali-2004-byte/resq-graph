import math
from enum import Enum
from src.astar import astar

class AmbulanceState(Enum):
    IDLE       = "IDLE"
    IN_TRANSIT = "IN_TRANSIT"
    ON_SCENE   = "ON_SCENE"

class Ambulance:
    def __init__(self, id: int, start_node: int, graph):
        self.id = id
        self.state = AmbulanceState.IDLE
        self.current_location = start_node
        self.pixel_pos = (0.0, 0.0) 
        self.current_path = []
        self.assigned_task = None
        self.progress = 0.0
        self.speed = 1.00  # Nodes traversed per tick (adjust as needed)
        self.graph = graph

    def navigate(self, destination: int) -> None:
        """Compute A* path from current_location to destination."""
        path = astar(self.graph, self.current_location, destination)
        if path:
            self.current_path = path
            self.state = AmbulanceState.IN_TRANSIT
            self.progress = 0.0
        else:
            # Fallback direct
            self.current_path = [self.current_location, destination]
            self.state = AmbulanceState.IN_TRANSIT
            self.progress = 0.0

    def update_position(self, node_positions: dict) -> None:
        """Called once per tick."""
        if self.state == AmbulanceState.IDLE:
            if self.current_location in node_positions:
                pos = node_positions[self.current_location]
                self.pixel_pos = (float(pos[0]), float(pos[1]))
            return

        if self.state == AmbulanceState.IN_TRANSIT:
            if not self.current_path:
                self.state = AmbulanceState.ON_SCENE
                return

            if len(self.current_path) == 1:
                self.current_location = self.current_path[0]
                pos = node_positions[self.current_location]
                self.pixel_pos = (float(pos[0]), float(pos[1]))
                self.current_path.pop(0)
                self.state = AmbulanceState.ON_SCENE
                self.progress = 0.0
                return

            # Interpolate between current_path[0] and current_path[1]
            start_node = self.current_path[0]
            end_node = self.current_path[1]

            self.progress += self.speed
            while self.progress >= 1.0 and len(self.current_path) > 1:
                self.progress -= 1.0
                self.current_location = self.current_path[1]
                self.current_path.pop(0)

            if len(self.current_path) == 1:
                self.current_location = self.current_path[0]
                pos = node_positions[self.current_location]
                self.pixel_pos = (float(pos[0]), float(pos[1]))
                self.current_path.pop(0)
                self.state = AmbulanceState.ON_SCENE
                self.progress = 0.0
                return

            start_node = self.current_path[0]
            end_node = self.current_path[1]

            self.pixel_pos = self._interpolate_pixel(node_positions, start_node, end_node, self.progress)

    def _interpolate_pixel(self, node_positions: dict, start_node: int, end_node: int, progress: float) -> tuple[float, float]:
        start_pos = node_positions.get(start_node, [0, 0])
        end_pos = node_positions.get(end_node, [0, 0])

        start_px = (float(start_pos[0]), float(start_pos[1]))
        end_px = (float(end_pos[0]), float(end_pos[1]))

        px_x = start_px[0] + progress * (end_px[0] - start_px[0])
        px_y = start_px[1] + progress * (end_px[1] - start_px[1])
        return (px_x, px_y)

    def get_status(self) -> dict:
        return {
            "id": self.id,
            "state": self.state.value,
            "location": self.current_location,
            "pixel_pos": self.pixel_pos,
            "task_id": self.assigned_task.id if self.assigned_task else None
        }

    def complete_task(self) -> None:
        if self.assigned_task:
            self.assigned_task.resolved = True
        self.assigned_task = None
        self.current_path = []
        self.state = AmbulanceState.IDLE
        self.progress = 0.0
