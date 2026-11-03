import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sim.data import INITIAL_DRIVERS

for d in INITIAL_DRIVERS:
    print(f"{d['id']:15} {d['code']:4} #{d['number']:2} {d.get('team_id')}")
