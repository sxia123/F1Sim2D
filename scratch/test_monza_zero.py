import math
import sys, pathlib, random
ROOT = pathlib.Path(r'c:\Coding\F1Sim2D')
sys.path.insert(0, str(ROOT))
from sim.data import clone_initial_roster
from sim.physics import (
    CAR_LEN_PX,
    CAR_WID_PX,
    CarState,
    RaceSession,
    _sat_obb_penetration,
    compute_lateral_screen_px,
)
import sim.physics as phys
from sim.tracks import COMPILED_TRACKS

DRAWN_HALF_L = 11.866 * 0.5
DRAWN_HALF_W = 5.712 * 0.5

# Test across Australia, Monaco, and Italy
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
    sat_overlaps = 0

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

            vis = [c for c in race.cars if not c.dnf and not c.in_pits]
            for i in range(len(vis)):
                for j in range(i + 1, len(vis)):
                    c1, c2 = vis[i], vis[j]
                    if (c1.x - c2.x)**2 + (c1.y - c2.y)**2 < 225.0:
                        sat = _sat_obb_penetration(c1, c2, half_l=DRAWN_HALF_L, half_w=DRAWN_HALF_W)
                        if sat is not None and min(sat) > 0.05:
                            sat_overlaps += 1

    print(f"TRACK: {tid.upper():10s} | Overlaps: {sat_overlaps:2d} | Lateral snaps: {snaps:4d} | Backward shunts: {shunts:3d} (max={max_shunt:.2f}m)")

