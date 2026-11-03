import sys, pathlib, random
ROOT = pathlib.Path(r'c:\Coding\F1Sim2D')
sys.path.insert(0, str(ROOT))
from sim.data import clone_initial_roster
from sim.physics import RaceSession, _sat_obb_penetration
from sim.tracks import COMPILED_TRACKS

trk = {t.id: t for t in COMPILED_TRACKS}['italy']
DRAWN_HALF_L = 11.866 * 0.5
DRAWN_HALF_W = 5.712 * 0.5

random.seed(0)
teams_list, drivers_list = clone_initial_roster()
teams_by_id = {t['id']: t for t in teams_list}
drivers = [d for d in drivers_list if d.get('team_id')]
race = RaceSession(trk, teams_by_id, drivers, 0.0, 0.1, 'mercedes', is_sprint=False)

for tick in range(455):
    race.step(0.05, lambda *_: None)
    if tick in (449, 450, 451, 452, 453, 454):
        c1 = [c for c in race.cars if c.code == 'LIN'][0]
        c2 = [c for c in race.cars if c.code == 'COL'][0]
        sat = _sat_obb_penetration(c1, c2, half_l=DRAWN_HALF_L, half_w=DRAWN_HALF_W)
        print(f"Tick {tick}: LIN(s={c1.s:.2f}, d={c1.d:.3f}, x={c1.x:.2f}, y={c1.y:.2f}) vs COL(s={c2.s:.2f}, d={c2.d:.3f}, x={c2.x:.2f}, y={c2.y:.2f}) -> sat={sat}")

