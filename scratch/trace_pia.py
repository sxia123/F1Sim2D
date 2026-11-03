import sys, pathlib
ROOT = pathlib.Path(r'c:\Coding\F1Sim2D')
sys.path.insert(0, str(ROOT))
from sim.data import clone_initial_roster
from sim.physics import RaceSession, enforce_2d_car_separation
from sim.tracks import COMPILED_TRACKS

tracks = {t.id: t for t in COMPILED_TRACKS}
trk = tracks['monaco']
teams_list, drivers_list = clone_initial_roster()
teams_by_id = {t['id']: t for t in teams_list}
drivers = [d for d in drivers_list if d.get('team_id')]

race = RaceSession(trk, teams_by_id, drivers, 0.0, 0.1, 'mercedes', is_sprint=False)
pia = next(c for c in race.cars if c.code == 'PIA')
dt = 0.05

for tick in range(215):
    # Monkey-patch or observe pia.d at each phase of race.step
    race.step(dt, lambda *_: None)
    if 4.80 <= race.race_clock <= 5.00:
        print(f"t={race.race_clock:.2f}s | PIA d={pia.d:.3f} target_d={pia.target_d:.3f} battle={pia.battle_with} man_pass={pia.maneuver_pass_timer:.2f}")
        for other in race.cars:
            if other.code != 'PIA':
                ds = (other.s - pia.s + trk.length_m*0.5)%trk.length_m - trk.length_m*0.5
                if abs(ds) < 15.0:
                    print(f"    Nearby: {other.code} ds={ds:+.2f}m d={other.d:+.3f} target_d={other.target_d:+.3f}")

