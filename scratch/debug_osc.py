import math, sys
sys.path.insert(0, ".")
from sim.tracks import COMPILED_TRACKS
from sim.data import clone_initial_roster
from sim.physics import RaceSession

trk = {t.id: t for t in COMPILED_TRACKS}['japan']
t_list, d_list = clone_initial_roster()
race = RaceSession(trk, {t['id']: t for t in t_list}, [d for d in d_list if d.get('team_id')], 0.0, 0.1, 'mercedes')

prev = {}
accel_hist = {}
samples = []
for tick in range(1800):
    race.step(0.05, lambda c, m: None)
    for c in race.cars:
        if c.driver_id in prev:
            pv = prev[c.driver_id][2]
            accel = (c.v - pv) / 0.05
            h = accel_hist.setdefault(c.driver_id, [])
            h.append((tick, round(race.race_clock, 2), round(accel, 1), round(c.v, 1), round(c.s, 1)))
            if len(h) > 5:
                h.pop(0)
                accs = [x[2] for x in h]
                for k in range(len(accs) - 2):
                    if (accs[k] > 8.0 and accs[k+1] < -25.0 and accs[k+2] > 8.0) or \
                       (accs[k] < -25.0 and accs[k+1] > 8.0 and accs[k+2] < -25.0):
                        if not c.dnf and c.spin_timer <= 0.0:
                            samples.append((c.code, list(h)))
                            break
        prev[c.driver_id] = (c.s, c.d, c.v, c.heading, c.x, c.y)

print(f"Found {len(samples)} oscillation samples.")
for s in samples[:5]:
    print(f"Car {s[0]}:")
    for row in s[1]:
        print(f"   tick={row[0]} t={row[1]}s: accel={row[2]:+6.1f} m/s^2, v={row[3]:5.1f} m/s, s={row[4]:6.1f} m")

