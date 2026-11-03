import sys, pathlib, math
from collections import Counter
ROOT = pathlib.Path(r'c:\Coding\F1Sim2D')
sys.path.insert(0, str(ROOT))
from sim.data import clone_initial_roster
from sim.physics import RaceSession, _sat_obb_penetration
from sim.tracks import COMPILED_TRACKS

# Let's test the proposed improvements by subclassing or patching RaceSession
class PatchedRaceSession(RaceSession):
    def _update_xy(self, car):
        if car.in_pits:
            super()._update_xy(car)
            return
        smp = self.track.sample(car.s)
        from sim.physics import compute_lateral_screen_px
        lat_px = compute_lateral_screen_px(self.track, car.d)
        car.x = round(smp["x"] + smp["nx"] * lat_px, 2)
        car.y = round(smp["y"] + smp["ny"] * lat_px, 2)

        if car.spin_timer > 0.0:
            omega = getattr(car, "spin_omega", 5.8)
            car.heading = round((math.atan2(smp["ty"], smp["tx"]) + car.spin_timer * omega) % (2.0 * math.pi) - math.pi, 4)
            return

        # Smooth, physics-bounded heading angle
        tx, ty = smp["tx"], smp["ty"]
        nx, ny = smp["nx"], smp["ny"]
        half_usable = self.track.track_width_px * 0.39
        v_forward_px = max(6.0, car.v * self.track.px_per_m)
        steer_rate = 4.2 if (car.maneuver_pass_timer > 0.0 or car.maneuver_timer > 0.0) else 2.4
        
        # Physical lateral velocity angle bounded to maximum realistic F1 slip/lane change angle (+- 4.2 deg)
        lat_vel_px = (car.target_d - car.d) * steer_rate * half_usable * 0.14
        lat_angle = math.atan2(lat_vel_px, v_forward_px)
        clamped_lat_angle = max(-0.075, min(0.075, lat_angle))

        track_heading = math.atan2(ty, tx)
        steer = getattr(car, "steer_angle", 0.0)
        yaw_attitude = max(-0.09, min(0.09, steer * 0.20))
        target_heading = track_heading + clamped_lat_angle + yaw_attitude

        # Smooth heading transition to eliminate single-tick 35-degree snaps
        if car.heading == 0.0:
            car.heading = round(target_heading, 4)
        else:
            dh = (target_heading - car.heading + math.pi) % (2.0 * math.pi) - math.pi
            max_dh = 7.5 * 0.05 # max ~21 deg/sec
            car.heading = round(car.heading + max(-max_dh, min(max_dh, dh)), 4)

for tid in ('australia', 'monaco', 'italy'):
    trk = {t.id: t for t in COMPILED_TRACKS}[tid]
    teams_list, drivers_list = clone_initial_roster()
    teams_by_id = {t['id']: t for t in teams_list}
    drivers = [d for d in drivers_list if d.get('team_id')]
    race = PatchedRaceSession(trk, teams_by_id, drivers, 0.0, 0.1, 'mercedes', is_sprint=False)

    counts = Counter()
    prev = {}
    dt = 0.05
    for tick in range(800):
        race.step(dt, lambda *_: None)
        if not race.lights_out:
            continue
        vis = [c for c in race.cars if not c.dnf and not c.in_pits]
        for c in vis:
            if c.driver_id in prev:
                ps, pd, pv, ph, px, py = prev[c.driver_id]
                ds = (c.s - ps + 0.5 * trk.length_m) % trk.length_m - 0.5 * trk.length_m
                dd = c.d - pd
                dv = c.v - pv
                dh = (c.heading - ph + math.pi) % (2.0 * math.pi) - math.pi
                if ds < -0.05 and c.pit_phase != 'STOPPED':
                    counts['BACKWARD_JUMP'] += 1
                if abs(dd) > 0.15 and c.spin_timer <= 0.0:
                    counts['LATERAL_SNAP'] += 1
                if abs(dh) > 0.25 and c.spin_timer <= 0.0:
                    counts['HEADING_SNAP'] += 1
                accel = dv / dt
                if abs(accel) > 60.0 and c.pit_phase != 'STOPPED' and c.spin_timer <= 0.0:
                    counts['ACCEL_JERK'] += 1
            prev[c.driver_id] = (c.s, c.d, c.v, c.heading, c.x, c.y)
    print(f'PATCHED {tid.upper()}: {dict(counts)}')

