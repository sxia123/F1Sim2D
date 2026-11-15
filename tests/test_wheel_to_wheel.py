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

    def test_stale_defense_moves_clears_after_battle_and_timer_expire(self):
        """Once a battle ends and defense_timer expires, defense_moves must reset so the car resumes racing line."""
        race = self.race("italy", count=2)
        race.lights_out = True
        race.flag_state = "GREEN"
        car, other = race.cars
        s = self.straight(race.track)
        self.place(race, car, s, 0.75)
        self.place(race, other, s + 250.0, 0.0)
        smp_before = race.track.sample(car.s)
        expected_line = max(-0.88, min(0.88, smp_before["racing_line_d"]))
        car.defense_moves = 1
        car.defending_side = 0.75
        car.defense_timer = 0.0
        car.battle_with = None

        with patch.object(race, "_check_solo_incidents"):
            race._step_car(car, other, other, False, 0.05, ignore_event)

        self.assertEqual(car.defense_moves, 0)
        self.assertLess(car.target_d, 0.0)
        self.assertLess(abs(car.target_d - expected_line), 0.12)

    def test_side_by_side_cars_hold_steady_lanes_without_target_pingpong(self):
        """Side-by-side battling cars hold steady lateral lanes without ping-pong reversals or overlap."""
        race = self.race("bahrain", count=2)
        race.lights_out = True
        race.flag_state = "GREEN"
        a, b = race.cars
        s = self.straight(race.track)
        self.place(race, a, s + 2.0, 0.36)
        self.place(race, b, s + 0.5, -0.36)
        a.v = b.v = 72.0
        a.free_air_target_v = b.free_air_target_v = 74.0
        race.standings = [a, b]

        reversals = {a.driver_id: 0, b.driver_id: 0}
        prev_tgt = {a.driver_id: a.target_d, b.driver_id: b.target_d}
        prev_dt = {a.driver_id: 0.0, b.driver_id: 0.0}
        prev_h = {a.driver_id: a.heading, b.driver_id: b.heading}
        max_dh = 0.0

        with patch.object(race, "_check_solo_incidents"):
            for _ in range(40):
                race.step(0.05, ignore_event)
                self.assertIsNone(_sat_obb_penetration(a, b))
                for c in (a, b):
                    dtgt = c.target_d - prev_tgt[c.driver_id]
                    if abs(dtgt) > 0.20 and abs(prev_dt[c.driver_id]) > 0.20 and dtgt * prev_dt[c.driver_id] < 0.0:
                        reversals[c.driver_id] += 1
                    if abs(dtgt) > 0.02:
                        prev_dt[c.driver_id] = dtgt
                    prev_tgt[c.driver_id] = c.target_d
                    dh = abs((c.heading - prev_h[c.driver_id] + math.pi) % (2.0 * math.pi) - math.pi)
                    max_dh = max(max_dh, dh)
                    prev_h[c.driver_id] = c.heading

        self.assertLessEqual(reversals[a.driver_id], 1)
        self.assertLessEqual(reversals[b.driver_id], 1)
        self.assertLessEqual(max_dh, 0.28)

    def test_all_physical_contacts_deal_damage_without_zero_damage_gaps(self):
        """Lap 1 post-launch hits, multi-car chain collisions, and spin collisions always inflict real damage."""
        race = self.race("bahrain", count=3)
        race.lights_out = True
        race.flag_state = "GREEN"
        race.race_clock = 18.0
        a, b, c = race.cars
        s = self.straight(race.track)
        events = []

        # 1. Lap 1 racing (post-launch) rear-end hit damages both cars proportionally
        self.place(race, a, s + 6.0, 0.0)
        self.place(race, b, s, 0.0)
        a.lap = b.lap = 1
        a.v, b.v = 60.0, 66.5
        race._on_physical_contact(a, b, (2.2, 1.8, 2.2, 1.8), lambda k, m: events.append((k, m)))
        self.assertGreater(b.wing_damage, 0.0)
        self.assertGreater(a.wing_damage, 0.0)

        # 2. Immediate secondary contact against a 3rd car 2s later still inflicts damage on c
        race.race_clock = 20.0
        self.place(race, c, s + 10.0, 0.45)
        b.lap = c.lap = 2
        b_dmg_before = b.wing_damage
        race._on_physical_contact(b, c, (1.4, 1.3, 1.4, 1.3), lambda k, m: events.append((k, m)))
        self.assertGreater(b.wing_damage, b_dmg_before)
        self.assertGreater(c.wing_damage, 0.0)

        # 3. Spin collision branch in _handle_collision damages both culprit and spinning victim
        race2 = self.race("bahrain", count=2)
        race2.lights_out = True
        race2.flag_state = "GREEN"
        x, y = race2.cars
        self.place(race2, x, s + 5.0, 0.1)
        self.place(race2, y, s, 0.2)
        rolls = iter([0.1, 0.85])
        with patch("sim.physics.random.random", side_effect=lambda: next(rolls, 0.5)):
            race2._handle_collision(x, y, 1, ignore_event)
        self.assertGreater(x.wing_damage, 0.0)
        self.assertGreater(y.wing_damage, 0.0)

    def test_high_risk_driver_attempts_daring_divebombs_more_than_cautious_driver(self):
        race = self.race("bahrain", count=2)
        race.lights_out = True
        race.flag_state = "GREEN"
        atk, dfn = race.cars
        hairpin_c = max(
            race.track.corners,
            key=lambda c: race.track.stations[c["station"]]["curv"],
        )
        s = hairpin_c["s_m"] - 15.0
        smp = race.track.sample(s)
        ins = float(smp.get("inside_sign", 1))
        self.place(race, dfn, s + 8.0, 0.35 * ins)
        self.place(race, atk, s, 0.0)
        atk.car_perf_index = dfn.car_perf_index = 90.0
        atk.skills.update({"pace": 88, "racecraft": 88, "consistency": 88, "defense": 82})
        dfn.skills.update({"pace": 88, "racecraft": 88, "consistency": 88, "defense": 82})
        atk.pace_mode = "PUSH"

        def count_divebombs(risk_val: int) -> int:
            atk.skills["risk"] = risk_val
            rng = random.Random(123)
            with patch("sim.physics.random.random", side_effect=rng.random):
                return sum(
                    1
                    for _ in range(300)
                    if race.select_and_evaluate_maneuver(atk, dfn, smp, True)[0] == "DIVEBOMB"
                )

        cautious_dives = count_divebombs(52)
        daring_dives = count_divebombs(92)
        self.assertGreater(daring_dives, cautious_dives * 2)

    def test_risk_increases_solo_crash_exposure_and_collision_can_retire_on_street_walls(self):
        # 1. Higher risk scales solo corner incident probability strictly upward across uniform threshold draws
        def run_solo_trials(risk_val: int) -> int:
            race = self.race("monaco", count=2)
            race.lights_out = True
            race.flag_state = "GREEN"
            car = race.cars[0]
            car.skills.update({"consistency": 84, "risk": risk_val})
            car.pace_mode = "ATTACK"
            corner = max(
                race.track.corners,
                key=lambda c: race.track.stations[c["station"]]["curv"],
            )
            smp = race.track.sample(corner["s_m"])
            events = []
            # Step threshold evenly through [0.00002 .. 0.00120]; inside _check_solo_incidents,
            # the 2nd random.random() call evaluates solo_err_prob (1st evaluates track limits).
            for idx in range(60):
                thresh = 0.00002 * (idx + 1)
                race.flag_state = "GREEN"
                car.dnf = False
                car.spin_timer = 0.0
                car.tire_wear = 0.85
                self.place(race, car, corner["s_m"], 0.0)
                seq = iter([0.5, thresh, 0.99, 0.99, 0.99, 0.99])
                with patch("sim.physics.random.random", side_effect=lambda: next(seq, 0.99)):
                    race._check_solo_incidents(car, smp, 1.0, lambda k, m: events.append(k))
            return sum(1 for k in events if k in ("CRASH", "YELLOW"))

        cautious_events = run_solo_trials(52)
        aggressive_events = run_solo_trials(94)
        self.assertGreater(aggressive_events, 15)
        self.assertGreater(aggressive_events, cautious_events * 2)

        # 2. Street-circuit crash DNF threshold retires victim on high-severity collision
        street_race = self.race("monaco", count=2)
        street_race.lights_out = True
        street_race.flag_state = "GREEN"
        street_race.race_clock = 40.0
        a, b = street_race.cars
        s = self.straight(street_race.track)
        self.place(street_race, a, s + 4.0, 0.1)
        self.place(street_race, b, s, 0.2)
        rolls = iter([0.1, 0.78, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5])
        with patch("sim.physics.random.random", side_effect=lambda: next(rolls, 0.5)):
            street_race._handle_collision(a, b, 1, ignore_event)
        self.assertTrue(b.dnf)

    def test_runoff_allows_outside_room_and_saves_failed_lunge_from_crash(self):
        race = self.race("bahrain", count=2)
        race.lights_out = True
        race.lights_countdown = 0.0
        race.flag_state = "GREEN"
        race.race_clock = 45.0
        dfn, atk = race.cars
        corner = max(
            (c for c in race.track.corners if race.track.sample(c["s_m"])["curv"] > 0.0082),
            key=lambda c: race.track.sample(c["s_m"]).get("runoff_width_m", 0.0),
        )
        s = corner["s_m"]
        smp = race.track.sample(s)
        self.assertGreater(smp["curv"], 0.0078)
        self.assertGreaterEqual(smp["runoff_width_m"], 4.0)
        rside = smp["runoff_side"]
        self.assertNotEqual(rside, 0)
        race.standings = [dfn, atk]

        # Outside neighbor alongside inside car gains extra runoff margin beyond 0.88
        self.place(race, dfn, s, rside * 0.48)
        self.place(race, atk, s, rside * 0.96)
        atk.maneuver_pass_timer = 1.0
        atk.maneuver_target_id = dfn.driver_id
        clamped = race._clamp_lane_for_alongside(atk, rside * 0.98, smp)
        self.assertGreater(abs(clamped), 0.88)

        # Failed lunge into a runoff corner uses runoff escape instead of barrier contact
        self.place(race, dfn, s + 6.0, -rside * 0.25)
        self.place(race, atk, s, rside * 0.20)
        dfn.v = 32.0
        atk.v = 36.0
        atk.maneuver_pass_timer = 0.0
        atk.maneuver_attempt_cooldown = 0.0
        atk.contact_cooldown = 0.0
        dfn.contact_cooldown = 0.0
        events = []
        with patch("sim.physics.random.random", return_value=0.001):
            with patch.object(race, "select_and_evaluate_maneuver", return_value=("DIVEBOMB", 0.0, -rside * 0.65)):
                race._resolve_battles_and_incidents(0.05, lambda k, m: events.append((k, m)))

        self.assertFalse(atk.dnf)
        self.assertFalse(dfn.dnf)
        self.assertGreater(atk.target_d * rside, 0.90)
        self.assertGreater(getattr(atk, "_sep_lane_timer", 0.0), 0.5)
        self.assertFalse(any(k == "INCIDENT" for k, _ in events))


if __name__ == "__main__":
    unittest.main()
