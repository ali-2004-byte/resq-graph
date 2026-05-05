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
