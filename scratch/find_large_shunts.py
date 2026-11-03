import sys, pathlib
ROOT = pathlib.Path(r'c:\Coding\F1Sim2D')
sys.path.insert(0, str(ROOT))
from sim.data import clone_initial_roster
from sim.physics import RaceSession
from sim.tracks import COMPILED_TRACKS

tracks = {t.id: t for t in COMPILED_TRACKS}
trk = tracks['australia']
teams_list, drivers_list = clone_initial_roster()
teams_by_id = {t['id']: t for t in teams_list}
drivers = [d for d in drivers_list if d.get('team_id')]

race = RaceSession(trk, teams_by_id, drivers, 0.0, 0.1, 'mercedes', is_sprint=False)
dt = 0.05

for tick in range(300):
    prev_s = {c.driver_id: c.s for c in race.cars}
    prev_td = {c.driver_id: c.total_dist for c in race.cars}
    race.step(dt, lambda *_: None)
    if race.lights_out:
        for c in race.cars:
            dtd = c.total_dist - prev_td[c.driver_id]
            if dtd < -0.5:
                print(f"t={race.race_clock:.2f}s | {c.code}: total_dist went from {prev_td[c.driver_id]:.2f} to {c.total_dist:.2f} (delta={dtd:.2f}m) | s={c.s:.1f} v={c.v:.1f}")

