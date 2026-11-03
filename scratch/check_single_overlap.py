import sys, pathlib
ROOT = pathlib.Path(r'c:\Coding\F1Sim2D')
sys.path.insert(0, str(ROOT))
from sim.data import clone_initial_roster
from sim.physics import RaceSession, _sat_obb_penetration
from sim.tracks import COMPILED_TRACKS

DRAWN_HALF_L = 11.866 * 0.5
DRAWN_HALF_W = 5.712 * 0.5

tracks = {t.id: t for t in COMPILED_TRACKS}
trk = tracks['italy']
teams_list, drivers_list = clone_initial_roster()
teams_by_id = {t['id']: t for t in teams_list}
drivers = [d for d in drivers_list if d.get('team_id')]

race = RaceSession(trk, teams_by_id, drivers, 0.0, 0.1, 'mercedes', is_sprint=False)
dt = 0.05

for tick in range(450):
    race.step(dt, lambda *_: None)
    if race.lights_out and 15.55 <= race.race_clock <= 15.70:
        had = next(c for c in race.cars if c.code == 'HAD')
        pia = next(c for c in race.cars if c.code == 'PIA')
        sat = _sat_obb_penetration(had, pia, half_l=DRAWN_HALF_L, half_w=DRAWN_HALF_W)
        print(f"t={race.race_clock:.2f}s | HAD: ({had.x}, {had.y}, h={had.heading:.3f}) PIA: ({pia.x}, {pia.y}, h={pia.heading:.3f}) | SAT: {sat}")
