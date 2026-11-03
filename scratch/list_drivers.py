import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sim.data import INITIAL_DRIVERS

for d in INITIAL_DRIVERS:
    print(f"{d['id']}: {d['name']} ({d['code']}) - {d.get('team_id')}")
