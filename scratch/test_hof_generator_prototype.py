import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sim.tracks import get_season_tracks
from sim.championship import get_season_regulations
from sim.data import INITIAL_TEAMS, INITIAL_DRIVERS

print("Testing full season generation prototype...")

TEAM_MAP = {t["id"]: t for t in INITIAL_TEAMS}
DRIVER_MAP = {d["id"]: d for d in INITIAL_DRIVERS}

print("Loaded teams:", len(TEAM_MAP))
print("Loaded drivers:", len(DRIVER_MAP))

