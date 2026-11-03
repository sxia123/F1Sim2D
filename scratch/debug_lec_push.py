import sys, pathlib, random
ROOT = pathlib.Path(r'c:\Coding\F1Sim2D')
sys.path.insert(0, str(ROOT))
from sim.data import clone_initial_roster
from sim.physics import RaceSession, _sat_obb_penetration
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

for tick in range(165):
    t = race.race_clock
    td_before = lec.total_dist
    race.step(dt, lambda *_: None)
    if race.lights_out and 2.40 <= t <= 2.55:
        print(f"t={t:.3f} | LEC total_dist before={td_before:.2f} after={lec.total_dist:.2f} delta={lec.total_dist - td_before:+.2f}")

