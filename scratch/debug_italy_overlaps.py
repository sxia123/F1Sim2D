import sys, pathlib
ROOT = pathlib.Path(r'c:\Coding\F1Sim2D')
sys.path.insert(0, str(ROOT))
from sim.data import clone_initial_roster
from sim.physics import (
    RaceSession,
    _sat_obb_penetration,
)
from sim.tracks import COMPILED_TRACKS

DRAWN_HALF_L = 11.866 * 0.5
DRAWN_HALF_W = 5.712 * 0.5

tracks = {t.id: t for t in COMPILED_TRACKS}
trk = tracks['italy']
teams_list, drivers_list = clone_initial_roster()
teams_by_id = {t['id']: t for t in teams_list}
drivers = [d for d in drivers_list if d.get('team_id')]

race = RaceSession(trk, teams_by_id, drivers, 0.0, 0.1, 'mercedes', is_sprint=False)
dt = 0.05

count = 0
for tick in range(800):
    race.step(dt, lambda *_: None)
    if race.lights_out:
        vis = [c for c in race.cars if not c.dnf and not c.in_pits]
        for i in range(len(vis)):
            for j in range(i + 1, len(vis)):
                c1, c2 = vis[i], vis[j]
                if (c1.x - c2.x)**2 + (c1.y - c2.y)**2 < 225.0:
                    sat = _sat_obb_penetration(c1, c2, half_l=DRAWN_HALF_L, half_w=DRAWN_HALF_W)
                    if sat is not None and min(sat) > 0.05:
                        count += 1
                        if count <= 15:
                            print(f"t={race.race_clock:.2f}s | {c1.code} (s={c1.s:.1f},d={c1.d:.2f},v={c1.v:.1f}) vs {c2.code} (s={c2.s:.1f},d={c2.d:.2f},v={c2.v:.1f}) sat={tuple(round(x,2) for x in sat)}")
print(f"Total: {count}")

