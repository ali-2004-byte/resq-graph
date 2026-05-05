import pygame
from src.config import *
from src.simulation.ambulance import AmbulanceState

class PygameRenderer:
    def __init__(self, screen, node_positions):
        self.screen = screen
        self.node_positions = node_positions
        
        # Pre-load background
        bg_image = pygame.image.load("data/map_bg.png").convert()
        # map_config uses PADDING=40, meaning the map was baked to a 1120x820 box at (40, 40)
        self.padding = 40
        drawable_w = WINDOW_WIDTH - 2 * self.padding
        drawable_h = WINDOW_HEIGHT - 2 * self.padding
        self.background = pygame.transform.scale(bg_image, (drawable_w, drawable_h))
        
        # Pre-load font
        pygame.font.init()
        self.font = pygame.font.SysFont("monospace", 16)

    def draw(self, state, ambulances):
        # Layer 0: Background
        self.screen.fill((26, 26, 46)) # Fill with dark navy before blitting map to cover padding
        self.screen.blit(self.background, (self.padding, self.padding))
        
        # Layer 1: Accident Markers
        for event in state.active_events:
            self._draw_accident(event.pixel_pos)
            
        # Layer 2: Ambulance Sprites
        for amb in ambulances:
            self._draw_ambulance(amb)
            
        # Layer 3: HUD Panel
        self._draw_hud(state, ambulances)
        
        pygame.display.flip()

    def _draw_accident(self, pixel_pos):
        x, y = pixel_pos
        # Red X drawn with two anti-aliased lines crossing
        pygame.draw.line(self.screen, COLOUR_ACCIDENT, (x - 6, y - 6), (x + 6, y + 6), 2)
        pygame.draw.line(self.screen, COLOUR_ACCIDENT, (x - 6, y + 6), (x + 6, y - 6), 2)

    def _draw_ambulance(self, amb):
        x, y = int(amb.pixel_pos[0]), int(amb.pixel_pos[1])
        if amb.state == AmbulanceState.IDLE:
            colour = COLOUR_IDLE
        elif amb.state == AmbulanceState.IN_TRANSIT:
            colour = COLOUR_TRANSIT
        else:
            colour = COLOUR_ON_SCENE
            
        pygame.draw.circle(self.screen, colour, (x, y), 8)
        pygame.draw.circle(self.screen, (0, 0, 0), (x, y), 8, 1) # Outline

    def _draw_hud(self, state, ambulances):
        hud_w, hud_h = 260, 150
        hud_surface = pygame.Surface((hud_w, hud_h), pygame.SRCALPHA)
        hud_surface.fill((*HUD_BG_COLOUR, 200)) # Semi-transparent
        
        idle_count = sum(1 for a in ambulances if a.state == AmbulanceState.IDLE)
        total_ambs = len(ambulances)
        
        lines = [
            f"Tick:           {state.current_tick}",
            f"Active Events:  {len(state.active_events)}",
            f"Idle Ambulances: {idle_count} / {total_ambs}",
            f"Avg Response:   {state.avg_response_time:.1f} ticks"
        ]
        
        if state.paused:
            lines.append("")
            lines.append("[⏸ PAUSED]")
            
        y_offset = 10
        for line in lines:
            text_surf = self.font.render(line, True, HUD_TEXT_COLOUR)
            hud_surface.blit(text_surf, (15, y_offset))
            y_offset += 20
            
        self.screen.blit(hud_surface, (WINDOW_WIDTH - hud_w - 10, 10))
