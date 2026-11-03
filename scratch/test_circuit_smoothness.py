import sys, pathlib, random
ROOT = pathlib.Path(r'c:\Coding\F1Sim2D')
sys.path.insert(0, str(ROOT))
from sim.data import clone_initial_roster
from sim.physics import RaceSession
from sim.tracks import COMPILED_TRACKS

tracks = {t.id: t for t in COMPILED_TRACKS}
for tid in ('australia', 'monaco', 'italy'):
    trk = tracks[tid]
    teams_list, drivers_list = clone_initial_roster()
    teams_by_id = {t['id']: t for t in teams_list}
    drivers = [d for d in drivers_list if d.get('team_id')]

    race = RaceSession(trk, teams_by_id, drivers, 0.0, 0.1, 'mercedes', is_sprint=False)
    dt = 0.05
    snaps = 0
    shunts = 0
    max_shunt = 0.0
    for tick in range(800):
        prev_s = {c.driver_id: c.s for c in race.cars}
        prev_d = {c.driver_id: c.d for c in race.cars}
        race.step(dt, lambda *_: None)
        if race.lights_out:
            for c in race.cars:
                if c.spin_timer <= 0 and not c.in_pits:
                    dd = c.d - prev_d[c.driver_id]
                    if abs(dd) > 0.15:
                        snaps += 1
                    ds = (c.s - prev_s[c.driver_id] + 0.5 * trk.length_m) % trk.length_m - 0.5 * trk.length_m
                    if ds < -0.10:
                        shunts += 1
                        if abs(ds) > max_shunt:
                            max_shunt = abs(ds)
    print(f"{tid.upper():10s} | Lateral snaps (|dd|>0.15): {snaps:4d} | Backward shunts (ds<-0.10): {shunts:3d} (max={max_shunt:.2f}m)")

