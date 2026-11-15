"""Tests for natural vehicle turning dynamics, velocity heading, body slip angle, and steer angles."""
import math
import random
import unittest

from sim.data import clone_initial_roster
from sim.physics import QualifyingSession, RaceSession
from sim.tracks import COMPILED_TRACKS


def ignore_event(*_):
    pass


class NaturalTurningTests(unittest.TestCase):
    def setUp(self):
        self.track = next(t for t in COMPILED_TRACKS if t.id == "italy")
        teams, drivers = clone_initial_roster()
        self.teams_dict = {t["id"]: t for t in teams}
        self.drivers = [d for d in drivers if d.get("team_id")][:4]

    def test_dynamic_body_slip_angle_computed_in_corners(self):
        race = RaceSession(self.track, self.teams_dict, self.drivers, 0, 0, "mclaren")
        race.lights_out = True
        race.lights_countdown = 0.0
        race.flag_state = "GREEN"

        corner_s = self.track.corners[0]["s_m"] if self.track.corners else 500.0
        car = race.cars[0]
        car.v = 45.0  # ~162 km/h
        car.lap = 2
        car.s = corner_s
        car.total_dist = self.track.length_m + corner_s

        race.step(0.05, ignore_event)
        smp = self.track.sample(car.s)

        if smp["curv"] > 0.005:
            self.assertNotEqual(car.body_slip_angle, 0.0)
            self.assertGreater(abs(car.g_lat), 0.5)
            # Body slip angle should have the same sign as inside_sign / lateral G
            self.assertEqual(math.copysign(1, car.body_slip_angle), math.copysign(1, smp["inside_sign"]))

    def test_heading_follows_actual_velocity_vector_during_lane_transition(self):
        race = RaceSession(self.track, self.teams_dict, self.drivers, 0, 0, "mclaren")
        car = race.cars[0]
        car.v = 30.0
        car.lap = 2
        car.s = 200.0
        car.total_dist = self.track.length_m + car.s
        car.d = 0.8
        car.target_d = -0.8
        car.lateral_velocity = -4.0  # aggressively diving toward apex

        smp = self.track.sample(car.s)
        track_heading = math.atan2(smp["ty"], smp["tx"])

        # Reset heading tick to trigger update
        car._heading_tick = -1
        car._has_initial_heading = False
        race.tick_count += 1
        race._update_xy(car)

        # The car's heading must be significantly angled inward toward the apex compared to centerline track_heading
        vx = smp["tx"] * car.v + smp["nx"] * car.lateral_velocity
        vy = smp["ty"] * car.v + smp["ny"] * car.lateral_velocity
        expected_vel_heading = math.atan2(vy, vx)

        # Diff between actual car heading and track centerline heading
        diff_from_track = (car.heading - track_heading + math.pi) % (2.0 * math.pi) - math.pi
        diff_from_vel = (car.heading - expected_vel_heading + math.pi) % (2.0 * math.pi) - math.pi

        # The car heading should be much closer to the true velocity heading than the centerline
        self.assertLess(abs(diff_from_vel), 0.15)
        self.assertGreater(abs(diff_from_track), 0.05)

    def test_front_wing_damage_reduces_turn_in_authority_understeer(self):
        race = RaceSession(self.track, self.teams_dict, self.drivers, 0, 0, "mclaren")
        race.lights_out = True
        race.lights_countdown = 0.0
        race.flag_state = "GREEN"

        car_clean = race.cars[0]
        car_damaged = race.cars[1]

        corner_s = self.track.corners[0]["s_m"] if self.track.corners else 500.0
        for car in (car_clean, car_damaged):
            car.v = 40.0
            car.lap = 2
            car.s = corner_s
            car.total_dist = self.track.length_m + corner_s
            car.lateral_velocity = 0.0

        car_damaged.wing_damage = 0.70  # heavy front wing damage

        race.step(0.05, ignore_event)

        smp = self.track.sample(corner_s)
        if smp["curv"] > 0.005:
            # Clean car has higher steering authority / angle than damaged car
            self.assertGreater(abs(car_clean.steer_angle), abs(car_damaged.steer_angle))

    def test_qualifying_session_computes_dynamic_body_slip_and_steer(self):
        quali = QualifyingSession(self.track, self.teams_dict, self.drivers, 0.0)
        car = quali.cars[0]
        car.v = 50.0

        corner_s = self.track.corners[0]["s_m"] if self.track.corners else 500.0
        car.s = corner_s
        car.total_dist = corner_s

        quali.step(0.05, ignore_event)
        smp = self.track.sample(car.s)

        if smp["curv"] > 0.005:
            self.assertNotEqual(car.body_slip_angle, 0.0)
            self.assertNotEqual(car.steer_angle, 0.0)
            self.assertIsNotNone(car.lateral_velocity)

    def test_steer_and_heading_smoothly_damp_instantaneous_lane_step(self):
        race = RaceSession(self.track, self.teams_dict, self.drivers[:1], 0, 0, "mclaren")
        race.lights_out = True
        race.lights_countdown = 0.0
        race.flag_state = "GREEN"
        car = race.cars[0]
        straight_s = min(range(self.track.NUM_STATIONS), key=lambda i: self.track.stations[i]["curv"]) * self.track.ds_m
        car.s = straight_s
        car.lap = 2
        car.total_dist = self.track.length_m + straight_s
        car.v = 65.0
        car.d = 0.0
        car.target_d = 0.0
        car._heading_tick = -1
        car._has_initial_heading = False
        race._update_xy(car)

        steers = []
        dh_steps = []
        prev_h = car.heading
        for _ in range(10):
            # Maintain a lane step command while stepping 50ms frames
            car.target_d = 0.80
            car.maneuver_pass_timer = 1.0
            car.maneuver_target_id = "other"
            race.step(0.05, ignore_event)
            steers.append(abs(car.steer_angle))
            dh = (car.heading - prev_h + math.pi) % (2.0 * math.pi) - math.pi
            dh_steps.append(abs(dh))
            prev_h = car.heading

        # Steer angle must build progressively rather than snapping straight to peak lock
        self.assertGreater(steers[1], steers[0])
        self.assertGreater(max(steers), steers[0])
        # Single-tick heading steps remain smoothly bounded through lateral turn-in
        self.assertLessEqual(max(dh_steps), 0.22)

    def test_smooth_racing_line_following_and_no_battle_swerving(self):
        race = RaceSession(self.track, self.teams_dict, self.drivers[:2], 0, 0, "mclaren")
        race.lights_out = True
        race.lights_countdown = 0.0
        race.flag_state = "GREEN"
        lead, trail = race.cars
        start_s = self.track.corners[0]["s_m"] if self.track.corners else 320.0
        for idx, c in enumerate((lead, trail)):
            c.s = (start_s - 45.0 - idx * 24.0) % self.track.length_m
            c.lap = 2
            c.total_dist = self.track.length_m + c.s
            c.v = 66.0
            c.free_air_target_v = 72.0
            c.d = self.track.sample(c.s)["racing_line_d"]
            c.target_d = c.d
            c._heading_tick = -1
            c._has_initial_heading = False
            race._update_xy(c)

        prev_td = trail.target_d
        max_td_step = 0.0
        for _ in range(70):
            race.step(0.05, ignore_event)
            if trail.maneuver_pass_timer <= 0.0 and trail.maneuver_timer <= 0.0:
                max_td_step = max(max_td_step, abs(trail.target_d - prev_td))
            prev_td = trail.target_d
            self.assertLessEqual(abs(trail.lateral_velocity), 4.2)

        self.assertLessEqual(max_td_step, 0.22, f"Unexpected target_d swerve step {max_td_step:.3f}")

    def test_six_driving_realism_mechanics(self):
        # 1. Path-curvature inside pinch slows target speed while inside radius shortens spline arc length
        corner_st = max(range(self.track.NUM_STATIONS), key=lambda i: self.track.stations[i]["curv"])
        corner_s = corner_st * self.track.ds_m
        smp_c = self.track.sample(corner_s)
        ins = float(smp_c["inside_sign"])

        def run_line_step(d_val: float, v_val: float = 34.0, g_lat_val: float = 0.2):
            race = RaceSession(self.track, self.teams_dict, self.drivers[:1], 0, 0, "mclaren")
            race.lights_out = True
            race.flag_state = "GREEN"
            c = race.cars[0]
            c.s = corner_s
            c.total_dist = self.track.length_m + corner_s
            c.lap = 2
            c.v = v_val
            c.d = c.target_d = d_val
            c.g_lat = g_lat_val
            c.lateral_velocity = 0.0
            race._step_car(c, None, None, False, 0.05, ignore_event)
            return c

        c_pinch = run_line_step(0.80 * ins, v_val=34.0)
        c_opt = run_line_step(smp_c["racing_line_d"], v_val=34.0)
        c_out = run_line_step(-0.78 * ins, v_val=34.0)
        self.assertLess(c_pinch.free_air_target_v, c_opt.free_air_target_v)
        self.assertGreater(c_pinch.total_dist, c_out.total_dist)

        # 2. Combined friction-circle limits corner-exit acceleration and trail braking under high lateral G
        c_low_g = run_line_step(smp_c["racing_line_d"], v_val=20.0, g_lat_val=0.2)
        c_high_g = run_line_step(smp_c["racing_line_d"], v_val=20.0, g_lat_val=4.5)
        self.assertLess(c_high_g.accel, c_low_g.accel)

        c_brake_low = run_line_step(smp_c["racing_line_d"], v_val=82.0, g_lat_val=0.2)
        c_brake_high = run_line_step(smp_c["racing_line_d"], v_val=82.0, g_lat_val=4.5)
        self.assertLess(abs(c_brake_high.accel), abs(c_brake_low.accel))

        # 3. Per-driver braking authority varies with risk & pace mode in braking zones
        ref_race = RaceSession(self.track, self.teams_dict, self.drivers[:1], 0, 0, "mclaren")
        braking_st = max(
            (i for i, b in enumerate(ref_race.is_braking) if b),
            key=lambda i: 88.0 - ref_race.v_env[i],
        )
        brake_s = braking_st * self.track.ds_m

        def run_brake_step(risk_val: int, mode: str):
            race = RaceSession(self.track, self.teams_dict, self.drivers[:1], 0, 0, "mclaren")
            race.lights_out = True
            race.flag_state = "GREEN"
            c = race.cars[0]
            c.s = brake_s
            c.total_dist = self.track.length_m + brake_s
            c.lap = 2
            c.v = ref_race.v_env[braking_st] + 15.0
            c.skills["risk"] = risk_val
            c.pace_mode = mode
            c.g_lat = 0.0
            race._step_car(c, None, None, False, 0.05, ignore_event)
            return c

        c_late = run_brake_step(95, "ATTACK")
        c_early = run_brake_step(45, "CONSERVE")
        self.assertGreater(c_late._last_driver_brake_auth, c_early._last_driver_brake_auth)
        self.assertGreater(abs(c_late.accel), abs(c_early.accel))
        self.assertGreater(c_late.free_air_target_v, c_early.free_air_target_v)

        # 4. Asymmetric late-apex racing line places inside apex slightly downstream of corner peak
        peak_offset = max(range(-1, 5), key=lambda off: self.track.stations[(corner_st + off) % self.track.NUM_STATIONS]["racing_line_d"] * ins)
        self.assertGreaterEqual(peak_offset, 0)

        # 5. Lateral wake cone sharply reduces dirty-air downforce loss when stepping out of the wake
        def run_wake_step(offset_d: float) -> float:
            race = RaceSession(self.track, self.teams_dict, self.drivers[:2], 0, 0, "mclaren")
            race.lights_out = True
            race.flag_state = "GREEN"
            lead, trail = race.cars
            lead.s = corner_s + 22.0
            lead.total_dist = self.track.length_m + lead.s
            lead.lap = 2
            lead.d = 0.0
            lead.v = 45.0
            trail.s = corner_s
            trail.total_dist = self.track.length_m + trail.s
            trail.lap = 2
            trail.d = offset_d
            trail.target_d = offset_d
            trail.v = 45.0
            race._step_car(trail, lead, lead, False, 0.05, ignore_event)
            return trail._last_dirty_air_loss

        self.assertGreater(run_wake_step(0.0), run_wake_step(0.65) * 2.0)

    def test_steering_and_heading_transitions_are_smooth(self):
        random.seed(21)
        race = RaceSession(self.track, self.teams_dict, self.drivers[:1], 0, 0, "mclaren")
        race.lights_out = True
        race.flag_state = "GREEN"
        c = race.cars[0]
        dt = 0.05
        # Start approaching Turn 1 of Bahrain with an abrupt lane target switch mid-run.
        corner_st = max(range(self.track.NUM_STATIONS), key=lambda i: self.track.stations[i]["curv"])
        c.s = ((corner_st - 15) % self.track.NUM_STATIONS) * self.track.ds_m
        c.total_dist = self.track.length_m + c.s
        c.lap = 2
        c.v = 60.0
        c.d = c.target_d = -0.6
        ignore = lambda *a, **kw: None
        prev_steer = None
        prev_h = None
        max_steer_rate = 0.0
        max_h_rate = 0.0
        for step_idx in range(100):
            if step_idx == 25:
                c.target_d = 0.6
            elif step_idx == 60:
                c.target_d = -0.4
            race.race_clock += dt
            race._step_car(c, None, None, False, dt, ignore)
            if prev_steer is not None:
                max_steer_rate = max(max_steer_rate, abs(c.steer_angle - prev_steer) / dt)
            if prev_h is not None:
                dh = (c.heading - prev_h + math.pi) % (2.0 * math.pi) - math.pi
                max_h_rate = max(max_h_rate, abs(dh) / dt)
            prev_steer = c.steer_angle
            prev_h = c.heading
        self.assertLessEqual(max_steer_rate, 2.25)
        self.assertLessEqual(max_h_rate, 4.0)


if __name__ == "__main__":
    unittest.main()
