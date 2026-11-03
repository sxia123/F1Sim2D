import sys, pathlib
ROOT = pathlib.Path(r'c:\Coding\F1Sim2D')
sys.path.insert(0, str(ROOT))
from sim.data import clone_initial_roster
from sim.physics import RaceSession
from sim.tracks import COMPILED_TRACKS

tracks = {t.id: t for t in COMPILED_TRACKS}
trk = tracks['monaco']
teams_list, drivers_list = clone_initial_roster()
teams_by_id = {t['id']: t for t in teams_list}
drivers = [d for d in drivers_list if d.get('team_id')]

race = RaceSession(trk, teams_by_id, drivers, 0.0, 0.1, 'mercedes', is_sprint=False)
alb = next(c for c in race.cars if c.code == 'ALB')
dt = 0.05

for tick in range(220):
    d_start = alb.d
    race.step(dt, lambda *_: None)
    if 3.7 <= race.race_clock <= 4.3:
        # Find who is closest to ALB
        other = sorted([c for c in race.cars if c.code != 'ALB'], key=lambda c: abs((c.s - alb.s + trk.length_m*0.5)%trk.length_m - trk.length_m*0.5))[0]
        ds = (other.s - alb.s + trk.length_m*0.5)%trk.length_m - trk.length_m*0.5
        print(f"t={race.race_clock:.2f}s | ALB d={alb.d:+.3f} (target={alb.target_d:+.3f}, diff={alb.d - d_start:+.3f}) | Near {other.code} ds={ds:+.2f}m d={other.d:+.3f} (target={other.target_d:+.3f})")

