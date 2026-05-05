from src.simulation.ambulance import Ambulance, AmbulanceState
from src.simulation.event_spawner import Accident

class BasicDispatcher:
    def assign(self, ambulances: list[Ambulance], events: list[Accident]) -> None:
        """For each unassigned event, find the nearest IDLE ambulance and dispatch it."""
        unassigned_events = [e for e in events if e.assigned_ambulance_id is None and not e.resolved]
        
        for event in unassigned_events:
            idle_ambulances = [a for a in ambulances if a.state == AmbulanceState.IDLE]
            if not idle_ambulances:
                break
                
            # Nearest ambulance based on current_location. Since we don't have distances readily 
            # available here without running A* for all, we can use euclidean distance between 
            # their pixel positions or graph node positions.
            # To keep it simple: Euclidean distance between pixel_pos.
            best_ambulance = None
            min_dist = float('inf')
            
            ex, ey = event.pixel_pos
            for amb in idle_ambulances:
                ax, ay = amb.pixel_pos
                dist = (ex - ax)**2 + (ey - ay)**2
                if dist < min_dist:
                    min_dist = dist
                    best_ambulance = amb
                    
            if best_ambulance:
                best_ambulance.assigned_task = event
                event.assigned_ambulance_id = best_ambulance.id
                best_ambulance.navigate(event.location)
