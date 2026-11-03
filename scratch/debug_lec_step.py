import sys, pathlib, random
ROOT = pathlib.Path(r'c:\Coding\F1Sim2D')
sys.path.insert(0, str(ROOT))
from sim.data import clone_initial_roster
from sim.physics import RaceSession, compute_lateral_screen_px
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

for tick in range(165):
    t_clock = race.race_clock
    lights = race.lights_out
    
    # We want to inspect tick when race_clock reaches ~2.35
    if lights and 2.30 <= race.race_clock <= 2.45:
        print(f"\n--- TICK START: t={race.race_clock:.3f} LEC d={lec.d:.3f} s={lec.s:.1f} v={lec.v:.1f} target={lec.target_d:.3f} ---")
        for other in race.cars:
            if other.code != 'LEC':
                ds = (other.s - lec.s + trk.length_m*0.5)%trk.length_m - trk.length_m*0.5
                if abs(ds) < 8.0:
                    print(f"   Nearby {other.code}: ds={ds:+.2f}m d={other.d:.3f} target={other.target_d:.3f} v={other.v:.1f}")

    race.step(dt, lambda *_: None)

    if lights and 2.30 <= t_clock <= 2.45:
        print(f"--- TICK END: LEC d={lec.d:.3f} (delta={lec.d - lec.target_d:+.3f}) ---")

