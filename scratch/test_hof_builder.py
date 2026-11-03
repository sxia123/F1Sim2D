import sys
import random
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sim.tracks import get_season_tracks
from sim.championship import get_season_regulations
from sim.data import INITIAL_TEAMS, INITIAL_DRIVERS

TEAM_MAP = {t["id"]: t for t in INITIAL_TEAMS}
DRIVER_MAP = {d["id"]: d for d in INITIAL_DRIVERS}

# Test generating 2026 and 2028
tracks_2026 = get_season_tracks(2026)
print(f"Tracks in 2026: {len(tracks_2026)}")
for i, t in enumerate(tracks_2026[:3]):
    print(f"  R{t.round}: {t.name} ({t.city}, {t.country}) - sprint={t.is_sprint}")

