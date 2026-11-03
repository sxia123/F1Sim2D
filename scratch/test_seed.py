import sys, pathlib, random
ROOT = pathlib.Path(r'c:\Coding\F1Sim2D')
sys.path.insert(0, str(ROOT))
from sim.data import clone_initial_roster
from sim.physics import RaceSession
from sim.tracks import COMPILED_TRACKS

random.seed(2026)
tracks = {t.id: t for t in COMPILED_TRACKS}
trk = tracks['monaco']
teams_list, drivers_list = clone_initial_roster()
teams_by_id = {t['id']: t for t in teams_list}
drivers = [d for d in drivers_list if d.get('team_id')]

race = RaceSession(trk, teams_by_id, drivers, 0.0, 0.1, 'mercedes', is_sprint=False)

dt = 0.05
prev_d = {}
snaps = []
for tick in range(250):
    race.step(dt, lambda *_: None)
    if race.lights_out:
        for c in race.cars:
            if c.driver_id in prev_d:
                dd = c.d - prev_d[c.driver_id]
                if abs(dd) > 0.15:
                    snaps.append((race.race_clock, c.code, dd, c.d, c.target_d, c.s))
            prev_d[c.driver_id] = c.d

print(f"Total snaps with seed 2026: {len(snaps)}")
for s in snaps[:15]:
    print(f"  t={s[0]:.2f}s | {s[1]} dd={s[2]:+.3f} d={s[3]:.3f} target={s[4]:.3f} s={s[5]:.1f}")

