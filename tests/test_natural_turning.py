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


if __name__ == "__main__":
    unittest.main()
