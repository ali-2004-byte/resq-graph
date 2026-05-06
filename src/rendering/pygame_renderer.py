"""
pygame_renderer.py – Sprint 5

Rendering changes from Sprint 4:
- Layer 2 (NEW): dashed ambulance path polylines.
- Layer 4: HUD panel extended with ART, resolved count, fleet utilisation.
- Layer 5 (NEW): semi-transparent metrics panel, toggled by M key.

draw() signature updated: draw(state, ambulances, dispatcher, show_metrics_panel).
"""
import math
import pygame

from src.config import (
    WINDOW_WIDTH,
    WINDOW_HEIGHT,
    COLOUR_IDLE,
    COLOUR_TRANSIT,
    COLOUR_ON_SCENE,
    COLOUR_ACCIDENT,
    HUD_BG_COLOUR,
    HUD_TEXT_COLOUR,
    DASHED_LINE_COLOUR,
    DASHED_SEGMENT_LEN,
    DASHED_GAP_LEN,
    METRICS_PANEL_WIDTH,
    METRICS_PANEL_HEIGHT,
)
from src.simulation.ambulance import AmbulanceState


class PygameRenderer:
    """Renders the simulation to a Pygame surface.

    Layer order
    -----------
    0  Background map
    1  Accident markers (red X)
    2  Ambulance path polylines (dashed blue)   ← Sprint 5 NEW
    3  Ambulance sprites (coloured circles)
    4  HUD panel (top-right)
    5  Metrics panel overlay (M key)             ← Sprint 5 NEW
    """

    def __init__(self, screen: pygame.Surface, node_positions: dict):
        self.screen         = screen
        self.node_positions = node_positions

        # ── Background ─────────────────────────────────────────────────────
        bg_image   = pygame.image.load("data/map_bg.png").convert()
        self.padding    = 40
        drawable_w = WINDOW_WIDTH  - 2 * self.padding
        drawable_h = WINDOW_HEIGHT - 2 * self.padding
        self.background = pygame.transform.scale(bg_image, (drawable_w, drawable_h))

        # ── Fonts ──────────────────────────────────────────────────────────
        pygame.font.init()
        self.font        = pygame.font.SysFont("monospace", 16)
        self.font_small  = pygame.font.SysFont("monospace", 14)
        self.font_title  = pygame.font.SysFont("monospace", 16, bold=True)

    # ── Public draw entry point ────────────────────────────────────────────────

    def draw(
        self,
        state,
        ambulances:         list,
        dispatcher          = None,
        show_metrics_panel: bool = False,
    ) -> None:
        """Render one frame.

        Parameters
        ----------
        state               SimulationState (tick, paused flag).
        ambulances          All Ambulance objects.
        dispatcher          DispatcherBrain – provides active_events and metrics.
        show_metrics_panel  Whether to draw the detailed M-key overlay.
        """
        active_events = dispatcher.active_events if dispatcher else []
        hud_data      = (
            dispatcher.metrics_tracker.get_hud_data() if dispatcher else {}
        )
        idle_count = sum(1 for a in ambulances if a.state == AmbulanceState.IDLE)

        # Layer 0: Background
        self.screen.fill((26, 26, 46))
        self.screen.blit(self.background, (self.padding, self.padding))

        # Layer 1: Accident markers
        for event in active_events:
            self._draw_accident(event.pixel_pos)

        # Layer 2: Ambulance path polylines (Sprint 5)
        self.draw_ambulance_paths(ambulances)

        # Layer 3: Ambulance sprites
        for amb in ambulances:
            self._draw_ambulance(amb)

        # Layer 4: HUD
        self._draw_hud(state, ambulances, idle_count, hud_data)

        # Layer 5: Metrics panel (Sprint 5)
        if show_metrics_panel:
            self.draw_metrics_panel(hud_data, len(active_events))

        pygame.display.flip()

    # ── Layer 1: Accidents ─────────────────────────────────────────────────────

    def _draw_accident(self, pixel_pos: tuple) -> None:
        x, y = int(pixel_pos[0]), int(pixel_pos[1])
        pygame.draw.line(self.screen, COLOUR_ACCIDENT, (x-6, y-6), (x+6, y+6), 2)
        pygame.draw.line(self.screen, COLOUR_ACCIDENT, (x-6, y+6), (x+6, y-6), 2)

    # ── Layer 2: Dashed path polylines (Sprint 5) ──────────────────────────────

    def draw_ambulance_paths(self, ambulances: list) -> None:
        """Draw dashed path polylines for all IN_TRANSIT ambulances."""
        for amb in ambulances:
            if not amb.pixel_polyline or amb.state == AmbulanceState.IDLE:
                continue
            self._draw_dashed_polyline(self.screen, DASHED_LINE_COLOUR, amb.pixel_polyline)

    def _draw_dashed_polyline(
        self, surface: pygame.Surface, colour: tuple, points: list[tuple]
    ) -> None:
        """Draw a multi-segment dashed line through a sequence of (x, y) points."""
        for i in range(len(points) - 1):
            self._draw_dashed_segment(surface, colour, points[i], points[i + 1])

    def _draw_dashed_segment(
        self,
        surface: pygame.Surface,
        colour:  tuple,
        p1:      tuple,
        p2:      tuple,
    ) -> None:
        """Interpolate dashes between two points.

        Dashes are DASHED_SEGMENT_LEN px; gaps are DASHED_GAP_LEN px.
        """
        dx, dy = p2[0] - p1[0], p2[1] - p1[1]
        length = math.hypot(dx, dy)
        if length == 0:
            return
        ux, uy = dx / length, dy / length
        step   = DASHED_SEGMENT_LEN + DASHED_GAP_LEN
        pos    = 0.0
        draw   = True
        while pos < length:
            end = min(pos + DASHED_SEGMENT_LEN, length)
            if draw:
                start_pt = (int(p1[0] + ux * pos), int(p1[1] + uy * pos))
                end_pt   = (int(p1[0] + ux * end), int(p1[1] + uy * end))
                pygame.draw.line(surface, colour, start_pt, end_pt, 2)
            pos  += step
            draw  = not draw

    # ── Layer 3: Ambulances ────────────────────────────────────────────────────

    def _draw_ambulance(self, amb) -> None:
        x, y = int(amb.pixel_pos[0]), int(amb.pixel_pos[1])
        if amb.state == AmbulanceState.IDLE:
            colour = COLOUR_IDLE
        elif amb.state == AmbulanceState.IN_TRANSIT:
            colour = COLOUR_TRANSIT
        else:
            colour = COLOUR_ON_SCENE
        pygame.draw.circle(self.screen, colour, (x, y), 8)
        pygame.draw.circle(self.screen, (0, 0, 0), (x, y), 8, 1)  # outline
        # Draw ambulance ID label
        label = self.font_small.render(str(amb.id), True, (255, 255, 255))
        self.screen.blit(label, (x + 10, y - 8))

    # ── Layer 4: HUD panel ─────────────────────────────────────────────────────

    def _draw_hud(
        self, state, ambulances: list, idle_count: int, hud_data: dict
    ) -> None:
        art          = hud_data.get("art", 0.0)
        total_events = hud_data.get("total_events", 0)
        utilisation  = (
            round((1 - idle_count / max(len(ambulances), 1)) * 100)
            if ambulances else 0
        )

        hud_w, hud_h = 270, 175
        hud_surf     = pygame.Surface((hud_w, hud_h), pygame.SRCALPHA)
        hud_surf.fill((*HUD_BG_COLOUR, 200))

        lines = [
            f"Tick:              {state.current_tick}",
            f"Active Events:     {len(getattr(state, 'active_events', []))}",   # compat
            f"Idle Ambulances:   {idle_count} / {len(ambulances)}",
            f"Avg Response Time: {art:.1f} ticks",       # ← Sprint 5 NEW
            f"Events Resolved:   {total_events}",        # ← Sprint 5 NEW
            f"Fleet Utilisation: {utilisation}%",        # ← Sprint 5 NEW
        ]
        if state.paused:
            lines.append("")
            lines.append("  [ ⏸  PAUSED ]")
        if not hud_data:
            lines.append("  [ M ] Metrics panel")

        y_off = 10
        for line in lines:
            surf = self.font.render(line, True, HUD_TEXT_COLOUR)
            hud_surf.blit(surf, (12, y_off))
            y_off += 22

        self.screen.blit(hud_surf, (WINDOW_WIDTH - hud_w - 10, 10))

    # ── Layer 5: Metrics panel (Sprint 5) ─────────────────────────────────────

    def draw_metrics_panel(self, hud_data: dict, active_count: int = 0) -> None:
        """Draw the semi-transparent detailed metrics overlay (toggled by M key)."""
        pw = METRICS_PANEL_WIDTH
        ph = METRICS_PANEL_HEIGHT
        px = (WINDOW_WIDTH  - pw) // 2
        py = (WINDOW_HEIGHT - ph) // 2

        panel = pygame.Surface((pw, ph), pygame.SRCALPHA)
        panel.fill((20, 20, 20, 210))

        # Title
        title = self.font_title.render("  METRICS PANEL  [ M to close ]", True, (180, 220, 255))
        panel.blit(title, (10, 8))

        # Divider
        pygame.draw.line(panel, (80, 80, 80), (10, 28), (pw - 10, 28), 1)

        art          = hud_data.get("art",          0.0)
        std_dev      = hud_data.get("std_dev",       0.0)
        fastest      = hud_data.get("min_rt",        0)
        slowest      = hud_data.get("max_rt",        0)
        total_events = hud_data.get("total_events",  0)
        latest_rt    = hud_data.get("latest_rt",     0)
        last_five    = hud_data.get("last_five",     [])

        rows = [
            ("Average Response Time", f"{art:.2f} ticks"),
            ("Std Deviation",         f"{std_dev:.2f} ticks"),
            ("Fastest Response",      f"{fastest} ticks"),
            ("Slowest Response",      f"{slowest} ticks"),
            ("Total Events Resolved", str(total_events)),
            ("Total Events Pending",  str(active_count)),
            ("Latest Response Time",  f"{latest_rt} ticks"),
            ("Last 5 Response Times", str(last_five) if last_five else "—"),
        ]

        y = 38
        label_colour = (200, 200, 200)
        value_colour = (255, 255, 100)
        for label, value in rows:
            lbl_surf = self.font_small.render(f"  {label}:", True, label_colour)
            val_surf = self.font_small.render(value,          True, value_colour)
            panel.blit(lbl_surf, (10, y))
            panel.blit(val_surf, (pw - val_surf.get_width() - 10, y))
            y += 19

        self.screen.blit(panel, (px, py))
