import sys, pathlib, random
ROOT = pathlib.Path(r'c:\Coding\F1Sim2D')
sys.path.insert(0, str(ROOT))
from sim.data import clone_initial_roster
from sim.physics import RaceSession, enforce_2d_car_separation
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

def wrap_step():
    # step inside RaceSession manually:
    t = race.race_clock
    if not race.lights_out:
        race.lights_countdown -= dt
        if race.lights_countdown <= 0.0:
            race.lights_out = True
            race.flag_state = "GREEN"
            for c in race.cars:
                c.v = 10.0
        return

    race.race_clock += dt
    leader = race.standings[0] if race.standings else None
    leader_finished = leader.finished if leader else False

    d0 = lec.d
    for idx, car in enumerate(race.standings):
        car_ahead = race.standings[idx - 1] if idx > 0 and not race.standings[idx - 1].dnf else None
        race._step_car(car, car_ahead, leader, leader_finished, dt, lambda *_: None)

    d1 = lec.d
    race._resolve_battles_and_incidents(dt, lambda *_: None)
    d2 = lec.d
    allow_passing = race.flag_state not in ("VSC", "SC", "LIGHTS")
    enforce_2d_car_separation(race.track, race.cars, allow_passing, race._update_xy)
    d3 = lec.d

    if 2.30 <= race.race_clock <= 2.50:
        print(f"t={race.race_clock:.3f} | d0={d0:.3f} -> after _step_car: {d1:.3f} -> after battles: {d2:.3f} -> after enforce_sep: {d3:.3f}")

for tick in range(165):
    wrap_step()

