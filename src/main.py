import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.simulation.simulation_engine import run_simulation

if __name__ == "__main__":
    try:
        run_simulation()
    except KeyboardInterrupt:
        pass
