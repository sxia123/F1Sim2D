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

for tick in range(449):
    race.step(0.05, lambda *_: None)

# In step 450, monitor LIN and COL closely
c1 = [c for c in race.cars if c.code == 'LIN'][0]
c2 = [c for c in race.cars if c.code == 'COL'][0]
print(f"Tick 449 end: LIN.d={c1.d:.4f}, target_d={c1.target_d:.4f}, COL.d={c2.d:.4f}, target_d={c2.target_d:.4f}")

race.step(0.05, lambda *_: None)
print(f"Tick 450 end: LIN.d={c1.d:.4f}, target_d={c1.target_d:.4f}, COL.d={c2.d:.4f}, target_d={c2.target_d:.4f}")
sat = _sat_obb_penetration(c1, c2, half_l=DRAWN_HALF_L, half_w=DRAWN_HALF_W)
print("Drawn SAT at tick 450:", sat)
sat_def = _sat_obb_penetration(c1, c2)
print("Default SAT at tick 450:", sat_def)

