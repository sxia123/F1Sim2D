import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sim.tracks import get_season_tracks
from sim.championship import get_season_regulations

def generate_season_archive(year: int):
    tracks = get_season_tracks(year)
    reg = get_season_regulations(year)
    print(f"Season {year}: {len(tracks)} tracks, Reg: {reg['name']}")
    return len(tracks)

for y in range(2026, 2031):
    generate_season_archive(y)

