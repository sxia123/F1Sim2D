import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sim.tracks import COMPILED_TRACKS
from sim.data import INITIAL_TEAMS, INITIAL_DRIVERS

print(f"Compiled tracks: {len(COMPILED_TRACKS)}")
print(f"Initial teams: {len(INITIAL_TEAMS)}")
print(f"Initial drivers: {len(INITIAL_DRIVERS)}")

