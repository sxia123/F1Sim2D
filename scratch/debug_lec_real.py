import sys, pathlib, random
ROOT = pathlib.Path(r'c:\Coding\F1Sim2D')
sys.path.insert(0, str(ROOT))
from sim.data import clone_initial_roster
from sim.physics import RaceSession, enforce_2d_car_separation
import sim.physics as physics
from sim.tracks import COMPILED_TRACKS

random.seed(2026)
tracks = {t.id: t for t in COMPILED_TRACKS}
trk = tracks['monaco']
teams_list, drivers_list = clone_initial_roster()
teams_by_id = {t['id']: t for t in teams_list}
drivers = [d for d in drivers_list if d.get('team_id')]

race = RaceSession(trk, teams_by_id, drivers, 0.0, 0.1, 'mercedes', is_sprint=False)
lec = next(c for c in race.cars if c.code == 'LEC')
dt = 0.05

orig_step_car = race._step_car
orig_resolve = race._resolve_battles_and_incidents
orig_enforce = physics.enforce_2d_car_separation

def traced_step():
    pass

for tick in range(165):
    d_before = lec.d
    s_before = lec.s
    race.step(dt, lambda *_: None)
    if race.lights_out and 2.30 <= race.race_clock <= 2.50:
        print(f"t={race.race_clock:.3f} | LEC d: {d_before:.3f} -> {lec.d:.3f} (diff={lec.d - d_before:+.3f}) | s={s_before:.1f}->{lec.s:.1f} total_dist={lec.total_dist:.1f}")

