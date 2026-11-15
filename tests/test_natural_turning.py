"""Tests for natural vehicle turning dynamics, velocity heading, body slip angle, and steer angles."""
import math
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


if __name__ == "__main__":
    unittest.main()
