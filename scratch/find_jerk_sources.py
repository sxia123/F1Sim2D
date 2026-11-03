import sys, pathlib, math
from collections import Counter
ROOT = pathlib.Path(r'c:\Coding\F1Sim2D')
sys.path.insert(0, str(ROOT))
from sim.data import clone_initial_roster
from sim.physics import RaceSession
from sim.tracks import COMPILED_TRACKS

trk = {t.id: t for t in COMPILED_TRACKS}['australia']
teams_list, drivers_list = clone_initial_roster()
teams_by_id = {t['id']: t for t in teams_list}
drivers = [d for d in drivers_list if d.get('team_id')]
race = RaceSession(trk, teams_by_id, drivers, 0.0, 0.1, 'mercedes', is_sprint=False)

# Track who causes accel jerk
jerk_causes = Counter()
snap_causes = Counter()

prev_v = {}
prev_d = {}

for tick in range(400):
    for c in race.cars:
        prev_v[c.driver_id] = c.v
        prev_d[c.driver_id] = c.d
    race.step(0.05, lambda *_: None)
    if not race.lights_out:
        continue
    for c in race.cars:
        if c.spin_timer > 0 or c.in_pits:
            continue
        dv = c.v - prev_v[c.driver_id]
        accel = dv / 0.05
        if abs(accel) > 60.0:
            jerk_causes[f'v={c.v:.1f}, dv={dv:.2f}, man={c.maneuver}, pass={c.maneuver_pass_timer>0}'] += 1
        dd = c.d - prev_d[c.driver_id]
        if abs(dd) > 0.15:
            snap_causes[f'd={c.d:.2f}, dd={dd:.2f}, tgt_d={c.target_d:.2f}, man={c.maneuver}, pass={c.maneuver_pass_timer>0}'] += 1

print('--- TOP ACCEL JERK CAUSES ---')
for k, v in jerk_causes.most_common(10):
    print(f'{v:3d}x: {k}')

print('\n--- TOP LATERAL SNAP CAUSES ---')
for k, v in snap_causes.most_common(10):
    print(f'{v:3d}x: {k}')

