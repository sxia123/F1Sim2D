"""Close racing must retain contact corrections and avoid abrupt lane reversals."""
import math
import random
import unittest
from unittest.mock import patch

from sim.car_geometry import CAR_LEN_PX, CAR_WID_PX
from sim.data import clone_initial_roster
from sim.physics import RaceSession, _sat_obb_penetration, enforce_2d_car_separation
from sim.tracks import COMPILED_TRACKS


def ignore_event(*_):
    pass


class WheelToWheelTests(unittest.TestCase):
    def setUp(self):
        state = random.getstate()
        self.addCleanup(random.setstate, state)
        random.seed(87)

    def race(self, track_id="italy", count=2):
        teams, drivers = clone_initial_roster()
        drivers = [d for d in drivers if d.get("team_id")][:count]
        track = next(t for t in COMPILED_TRACKS if t.id == track_id)
        return RaceSession(track, {t["id"]: t for t in teams}, drivers, 0, 0, "mclaren")

    def place(self, race, car, s, d=0):
        car.s = s % race.track.length_m
        car.total_dist = race.track.length_m + s
        car.lap = 2
        car.d = car.target_d = d
        car.v = 20
        car.auto_strategy = False
        car._heading_tick = -1
        car._has_initial_heading = False
        race._update_xy(car)

    def straight(self, track):
        return min(range(track.NUM_STATIONS), key=lambda i: track.stations[i]["curv"]) * track.ds_m

    def test_emergency_contact_correction_survives_next_position_sync(self):
        for track_id in ("australia", "monaco", "italy"):
            with self.subTest(track=track_id):
                race = self.race(track_id)
                a, b = race.cars
                s = self.straight(race.track)
                self.place(race, a, s, -.04)
                self.place(race, b, s, .04)
                a.maneuver_pass_timer = b.maneuver_pass_timer = 2
                self.assertIsNotNone(_sat_obb_penetration(a, b))
                # Tiny time step exhausts the soft-correction budgets, forcing
                # the exact fallback that previously only changed x/y.
                enforce_2d_car_separation(race.track, race.cars, True, race._update_xy, dt=.005)
                self.assertIsNone(_sat_obb_penetration(a, b))
                resolved = [(c.x, c.y) for c in race.cars]
                for c in race.cars:
                    race._update_xy(c)
                self.assertEqual(resolved, [(c.x, c.y) for c in race.cars])
                self.assertIsNone(_sat_obb_penetration(a, b))

    def test_contact_does_not_cancel_planned_passing_lanes(self):
        race = self.race()
        race.lights_out = True
        race.flag_state = "GREEN"
        a, b = race.cars
        s = self.straight(race.track)
        self.place(race, a, s, -.1)
        self.place(race, b, s, .1)
        a.target_d, b.target_d = -.8, .8
        a.maneuver_pass_timer = b.maneuver_pass_timer = 2
        enforce_2d_car_separation(race.track, race.cars, True, race._update_xy)
        self.assertLessEqual(a.target_d, -.8)
        self.assertGreaterEqual(b.target_d, .8)

    def test_lane_change_and_reversal_have_bounded_acceleration(self):
        race = self.race(count=1)
        c = race.cars[0]
        self.place(race, c, self.straight(race.track))
        c.target_d = .85
        for _ in range(12):
            old = c.lateral_velocity
            race._move_laterally(c, .05)
            self.assertLessEqual(abs(c.lateral_velocity - old), .500001)
            self.assertLessEqual(abs(c.lateral_velocity), 4.500001)
        self.assertGreater(c.lateral_velocity, 0)
        c.target_d = -.85
        old = c.lateral_velocity
        race._move_laterally(c, .025)
        self.assertGreater(c.lateral_velocity, 0, "A lane reversal must first brake lateral motion")
        self.assertLessEqual(abs(c.lateral_velocity - old), .250001)

    def test_car_cannot_steer_across_an_occupied_lane_at_the_timing_line(self):
        race = self.race()
        race.lights_out = True
        race.flag_state = "GREEN"
        a, b = race.cars
        self.place(race, a, race.track.length_m - 1, .3)
        self.place(race, b, 1, -.3)
        a.target_d = -.85
        for _ in range(50):
            race._move_laterally(a, .05)
            self.assertGreater(a.d, b.d)
            separation = (race.track.lateral_to_px(a.d, a.s)
                          - race.track.lateral_to_px(b.d, b.s))
            self.assertGreaterEqual(separation, CAR_WID_PX * 1.06 - .00001)

    def test_heading_follows_actual_motion_instead_of_a_changed_lane_request(self):
        race = self.race(count=1)
        c = race.cars[0]
        self.place(race, c, self.straight(race.track))
        c.v, c.lateral_velocity, c.target_d = 50, 1.5, .8
        c._heading_tick = -1
        c._has_initial_heading = False
        race._update_xy(c)
        before = c.heading
        c.target_d = -.8
        race.tick_count += 1
        race._update_xy(c)
        self.assertAlmostEqual(c.heading, before, places=4)

    def test_passing_lane_is_retained_if_timer_expires_while_alongside(self):
        race = self.race()
        race.lights_out = True
        race.flag_state = "GREEN"
        a, b = race.cars
        s = self.straight(race.track)
        self.place(race, a, s, -.5)
        self.place(race, b, s + 1, .5)
        a.maneuver_pass_timer = .01
        a.maneuver_target_id = b.driver_id
        race.flag_state = "GREEN"
        with patch.object(race, "_check_solo_incidents"):
            race._step_car(a, b, b, False, .05, ignore_event)
        self.assertEqual(a.maneuver_target_id, b.driver_id)
        self.assertGreater(a.maneuver_pass_timer, 0)
        self.assertLess(a.target_d, 0)

    def test_queue_correction_uses_the_actual_substep_duration(self):
        race = self.race()
        race.lights_out = True
        race.flag_state = "GREEN"
        a, b = race.cars
        s = self.straight(race.track)
        self.place(race, a, s)
        self.place(race, b, s + CAR_LEN_PX / race.track.px_per_m * 1.2)
        before = a.total_dist
        enforce_2d_car_separation(race.track, race.cars, False, race._update_xy, dt=.005)
        self.assertLessEqual(before - a.total_dist, 20 * .005 * .60 + .000001)

    def test_packed_race_positions_stay_consistent_after_contact_resolution(self):
        for track_id in ("australia", "monaco", "italy"):
            random.seed(87)
            race = self.race(track_id, 22)
            for _ in range(400):
                race.step(.05, ignore_event)
                if not race.lights_out:
                    continue
                for c in race.cars:
                    if c.in_pits or c.dnf or c.spin_timer > 0:
                        continue
                    sample = race.track.sample(c.s)
                    lateral = race.track.lateral_to_px(c.d, c.s)
                    expected_x = sample["x"] + sample["nx"] * lateral
                    expected_y = sample["y"] + sample["ny"] * lateral
                    self.assertLess(math.hypot(c.x - expected_x, c.y - expected_y), .015,
                                    (track_id, c.code, "contact correction would reset next tick"))


    def test_side_by_side_battle_resolves_without_infinite_multicorner_stalemate(self):
        """Side-by-side battle must decisively resolve within ~3.5 seconds rather than locking cars parallel forever."""
        race = self.race()
        race.lights_out = True
        race.flag_state = "GREEN"
        a, b = race.cars
        s = self.straight(race.track)
        self.place(race, a, s, -.5)
        self.place(race, b, s + 1, .5)
        a.maneuver_pass_timer = 2.0
        a.maneuver_target_id = b.driver_id
        race.flag_state = "GREEN"

        with patch.object(race, "_check_solo_incidents"):
            for _ in range(80):  # 80 * 0.05 = 4.0 seconds of racing
                race._step_car(a, b, b, False, .05, ignore_event)
                race._step_car(b, a, a, False, .05, ignore_event)

        # After 4 seconds through corners, battle must have concluded
        self.assertEqual(a.maneuver_pass_timer, 0.0)
        self.assertIsNone(a.maneuver_target_id)

    def test_wheel_to_wheel_contact_causes_damage_and_incidents(self):
        """Wheel-banging contact in wheel-to-wheel racing applies bodywork damage, sparks, and stewards inquiry."""
        race = self.race()
        race.lights_out = True
        race.flag_state = "GREEN"
        a, b = race.cars
        events = []
        turn = 4

        # Initial damage is 0
        self.assertEqual(a.wing_damage, 0.0)
        self.assertEqual(b.wing_damage, 0.0)

        race._trigger_side_by_side_contact(a, b, turn, lambda k, msg: events.append((k, msg)))

        # Both cars take realistic sidepod / front wing endplate damage
        self.assertGreater(a.wing_damage, 0.0)
        self.assertGreater(b.wing_damage, 0.0)
        self.assertIn(a.wing_damage_side, ("LEFT", "RIGHT"))
        self.assertIn(b.wing_damage_side, ("LEFT", "RIGHT"))
        self.assertTrue(a.sparks)
        self.assertTrue(b.sparks)
        self.assertGreater(a.contact_cooldown, 0.0)
        self.assertGreater(b.contact_cooldown, 0.0)

        # Incident broadcast and stewards queue updated
        self.assertTrue(any(ev[0] == "INCIDENT" and "WHEEL BANGING" in ev[1] for ev in events))
        self.assertTrue(any(st["reason"] == "Wheel-to-wheel contact" for st in race.stewards_queue))

    def test_ai_declines_going_three_wide_when_two_cars_ahead_are_side_by_side(self):
        """AI trailing a 2-wide battle stays tucked in rather than fanning out 3-wide on straights or corners."""
        race = self.race("bahrain", count=3)
        race.lights_out = True
        race.flag_state = "GREEN"
        race.race_clock = 90.0
        c1, c2, c3 = race.cars
        s = self.straight(race.track)
        self.place(race, c1, s + 12.0, -0.52)
        self.place(race, c2, s + 11.0, 0.52)
        self.place(race, c3, s, 0.45)
        c1.v = c2.v = 80.0
        c1.free_air_target_v = c2.free_air_target_v = 88.0
        c3.v = 84.0
        c3.free_air_target_v = 94.0
        c3.pace_mode = "PUSH"
        race.standings = [c1, c2, c3]

        self.assertTrue(race._is_zone_already_two_wide(c3, c2, lookahead_m=12.0))
        race._plan_tow_pass(c3, c2, 11.0)
        self.assertEqual(c3.maneuver_pass_timer, 0.0)
        self.assertEqual(c3.target_d, c2.d)

        # Also verify corner battle resolution refuses 3-wide lunges
        corner_s = race.track.corners[0]["s_m"]
        self.place(race, c1, corner_s + 8.5, -0.52)
        self.place(race, c2, corner_s + 7.5, 0.52)
        self.place(race, c3, corner_s, 0.40)
        c1.v = c2.v = 36.0
        c3.v = 38.0
        race.standings = [c1, c2, c3]
        race._resolve_battles_and_incidents(0.05, ignore_event)
        self.assertEqual(c3.maneuver_pass_timer, 0.0)
        self.assertAlmostEqual(c3.target_d, c2.d, places=4)

    def test_trailing_car_brakes_for_same_lane_blocker_behind_two_wide_pair(self):
        """A 3rd car behind a 2-wide battle must brake for the car in its own lane even if P(i-1) is in the other lane."""
        race = self.race("italy", count=3)
        race.lights_out = True
        race.flag_state = "GREEN"
        p1, p2, p3 = race.cars
        braking_st = next(i for i, b in enumerate(race.is_braking) if b)
        s_brake = braking_st * race.track.ds_m

        # p1 is ahead in the RIGHT lane braking hard; p2 is directly ahead in standings in the LEFT lane still fast
        self.place(race, p1, s_brake, 0.55)
        self.place(race, p2, s_brake - 2.0, -0.60)
        self.place(race, p3, s_brake - 22.0, 0.55)
        p1.v = 30.0
        p2.v = 76.0
        p3.v = 78.0
        p1.pos, p2.pos, p3.pos = 1, 2, 3
        race.standings = [p1, p2, p3]

        with patch.object(race, "_check_solo_incidents"):
            race._step_car(p3, p2, p1, False, 0.05, ignore_event)

        self.assertLess(p3.v, 78.0)
        self.assertLess(p3.accel, -5.0)

    def test_longitudinally_separated_pass_does_not_trigger_phantom_wheel_banging(self):
        """Corner pass preparation from >1 car length back must never roll side-by-side wheel-banging damage."""
        race = self.race("australia", count=2)
        race.lights_out = True
        race.flag_state = "GREEN"
        race.race_clock = 120.0
        defender, attacker = race.cars
        corner_st = max(range(race.track.NUM_STATIONS), key=lambda i: race.track.stations[i]["curv"])
        corner_s = corner_st * race.track.ds_m

        self.place(race, defender, corner_s + 12.0, 0.10)
        self.place(race, attacker, corner_s, -0.32)
        attacker.maneuver = "DIVEBOMB"
        attacker.maneuver_pass_timer = 3.0
        attacker.maneuver_target_id = defender.driver_id
        race.standings = [defender, attacker]
        events = []

        with patch("sim.physics.random.random", return_value=0.0):
            race._resolve_battles_and_incidents(0.05, lambda k, m: events.append((k, m)))

        self.assertEqual(attacker.wing_damage, 0.0)
        self.assertEqual(defender.wing_damage, 0.0)
        self.assertFalse(any(k == "INCIDENT" for k, _ in events))


if __name__ == "__main__":
    unittest.main()
