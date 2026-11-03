"""A tow builds a passing run; it must not trap a genuinely faster car."""
import random
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from sim.car_geometry import CAR_LEN_PX, CAR_WID_PX
from sim.championship import ChampionshipWorld
from sim.data import clone_initial_roster
from sim.physics import RaceSession, _sat_obb_penetration
from sim.tracks import COMPILED_TRACKS


def ignore_event(*_):
    pass


class TowBalanceTests(unittest.TestCase):
    def setUp(self):
        state = random.getstate()
        self.addCleanup(random.setstate, state)
        random.seed(42)
        self.configure_race()

    def configure_race(self):
        teams, drivers = clone_initial_roster()
        ids = ("russell", "sainz", "norris", "leclerc")
        roster = [next(d for d in drivers if d["id"] == key) for key in ids]
        track = next(t for t in COMPILED_TRACKS if t.id == "italy")
        self.race = RaceSession(track, {t["id"]: t for t in teams}, roster, 0, 0, "mercedes")
        self.attacker, self.defender, self.left, self.right = self.race.cars
        self.race.cars = [self.defender, self.attacker]
        self.race.standings = self.race.cars[:]
        self.race.flag_state = "GREEN"
        self.race.lights_out = True
        self.race.race_clock = 80
        # A real 1 km Monza straight, rather than an artificially infinite road.
        self.start = track.ds_m * 903 + 50
        self.place(self.attacker, self.start, 0, 80, 94)
        self.place(self.defender, self.start + 14, 0, 80, 89)
        self.attacker.pos, self.defender.pos = 2, 1
        self.sample = track.sample(self.attacker.s)
        self.assertLess(self.sample["curv"], .0038)
        self.assertFalse(self.race.is_braking[self.sample["station"]])

    def place(self, car, s, d, speed, available_pace):
        car.total_dist = self.race.track.length_m + s
        car.s = car.total_dist % self.race.track.length_m
        car.lap = 2
        car.laps_completed = 1
        car.crossed_start_line = True
        car.current_sector_times = [25.0, 25.0, None]
        car.sector_start_time = 50
        car.lap_start_time = 0
        car.d = car.target_d = d
        car.v = speed
        car.free_air_target_v = available_pace
        car.auto_strategy = False
        car.ers_mode = "HARVEST"
        car.tire_wear = .1
        car.driver_line_bias = 0
        car._heading_tick = -1
        car._has_initial_heading = False
        self.race._update_xy(car)

    def test_clear_faster_car_pulls_out_even_if_random_roll_would_fail(self):
        self.assertEqual(self.attacker.v, self.defender.v)
        with patch("sim.physics.random.random", return_value=.999):
            self.race._resolve_battles_and_incidents(.05, ignore_event)
        self.assertEqual(self.attacker.maneuver, "SLIPSTREAM")
        self.assertEqual(self.attacker.maneuver_target_id, self.defender.driver_id)
        self.assertGreater(self.attacker.maneuver_pass_timer, 0)
        clearance = abs(self.race.track.lateral_to_px(self.attacker.target_d, self.attacker.s)
                        - self.race.track.lateral_to_px(self.defender.target_d, self.defender.s))
        self.assertGreaterEqual(clearance, CAR_WID_PX * 1.15 - .001)

    def test_tow_disappears_immediately_on_pullout_without_cancelling_the_pass(self):
        self.race._resolve_battles_and_incidents(.05, ignore_event)
        self.assertEqual(self.race.display_maneuver(self.attacker), "SLIPSTREAM")
        timer = self.attacker.maneuver_pass_timer
        self.attacker.d = self.attacker.target_d
        self.assertEqual(self.race.display_maneuver(self.attacker), "")
        self.assertEqual(self.attacker.maneuver_pass_timer, timer)
        self.assertEqual(self.attacker.maneuver_target_id, self.defender.driver_id)
        sample = self.race.track.sample(self.attacker.s)
        self.assertEqual(self.race._tow_strength(self.attacker, self.defender, sample), 0)

    def test_tow_requires_a_close_live_car_directly_ahead(self):
        cases = ({"distance": 60}, {"distance": -10}, {"distance": 0}, {"lane": .5},
                 {"dnf": True}, {"in_pits": True}, {"finished": True}, {"spin_timer": 1})
        for case in cases:
            with self.subTest(case=case):
                self.configure_race()
                self.attacker.maneuver = "SLIPSTREAM"
                self.defender.s = (self.attacker.s + case.get("distance", 14)) % self.race.track.length_m
                self.defender.d = case.get("lane", 0)
                for field in ("dnf", "in_pits", "finished", "spin_timer"):
                    if field in case:
                        setattr(self.defender, field, case[field])
                self.assertEqual(self.race.display_maneuver(self.attacker), "")
                sample = self.race.track.sample(self.attacker.s)
                self.assertEqual(self.race._tow_strength(self.attacker, self.defender, sample), 0)

    def test_tow_does_not_linger_in_clear_air_or_after_a_pass(self):
        self.attacker.maneuver = "SLIPSTREAM"
        self.attacker.maneuver_timer = self.attacker.maneuver_pass_timer = 8
        self.race.cars = [self.attacker]
        self.assertEqual(self.race.display_maneuver(self.attacker), "")
        self.race.cars.append(self.defender)
        self.defender.s = (self.attacker.s - 1) % self.race.track.length_m
        self.assertEqual(self.race.display_maneuver(self.attacker), "")

    def test_tow_detects_the_actual_car_ahead_across_the_timing_line(self):
        self.attacker.maneuver = "SLIPSTREAM"
        self.attacker.s = self.race.track.length_m - 5
        self.defender.s = 5
        self.defender.lap = 1
        self.assertEqual(self.race.display_maneuver(self.attacker), "SLIPSTREAM")

    def test_live_payload_clears_tow_for_race_and_sprint_without_waiting_for_timer(self):
        self.attacker.maneuver = "SLIPSTREAM"
        self.attacker.maneuver_timer = 8
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1] / "scratch") as temp:
            world = ChampionshipWorld(save_path=Path(temp) / "career.json")
            world.race_session = self.race
            for phase in ("RACE", "SPRINT_RACE"):
                world.phase = phase
                for distance, lane, expected in ((14, 0, "SLIPSTREAM"), (14, .6, ""),
                                                 (-1, 0, ""), (80, 0, "")):
                    self.defender.s = (self.attacker.s + distance) % self.race.track.length_m
                    self.defender.d = lane
                    row = next(c for c in world.build_live_tick_payload()["cars"]
                               if c["id"] == self.attacker.driver_id)
                    self.assertEqual(row["man"], expected)
            self.assertEqual(self.attacker.maneuver_timer, 8)

    def test_pass_planning_does_not_change_either_cars_speed_or_announce_a_result(self):
        messages = []
        self.race._resolve_battles_and_incidents(.05, lambda *args: messages.append(args))
        self.assertEqual((self.attacker.v, self.defender.v), (80, 80))
        self.assertFalse(messages, "A selected lane is not yet a completed pass")
        self.attacker.d = self.attacker.target_d
        self.race._resolve_battles_and_incidents(.05, ignore_event)
        self.assertEqual((self.attacker.v, self.defender.v), (80, 80))

    def test_driver_gathers_tow_at_a_distance_then_commits(self):
        self.place(self.defender, self.start + 35, 0, 80, 89)
        self.race._resolve_battles_and_incidents(.05, ignore_event)
        self.assertEqual(self.attacker.tow_target_id, self.defender.driver_id)
        self.assertEqual(self.attacker.maneuver_pass_timer, 0)
        self.assertIsNone(self.attacker.battle_with)
        self.place(self.defender, self.start + 12, 0, 80, 89)
        self.race._resolve_battles_and_incidents(.05, ignore_event)
        self.assertGreater(self.attacker.maneuver_pass_timer, 0)

    def test_occupied_side_is_rejected_and_free_side_is_used(self):
        self.place(self.left, self.start + 5, -.65, 80, 89)
        self.race.cars.append(self.left)
        self.race._plan_tow_pass(self.attacker, self.defender, 14)
        self.assertGreater(self.attacker.maneuver_pass_timer, 0)
        self.assertGreater(self.attacker.target_d, self.defender.target_d)

    def test_both_sides_blocked_does_not_force_a_pass(self):
        self.place(self.left, self.start + 5, -.65, 80, 89)
        self.place(self.right, self.start + 5, .65, 80, 89)
        self.race.cars.extend((self.left, self.right))
        self.race._plan_tow_pass(self.attacker, self.defender, 14)
        self.assertEqual(self.attacker.maneuver_pass_timer, 0)
        self.assertIsNone(self.attacker.tow_target_id)
        self.assertEqual(self.attacker.target_d, self.defender.d)

    def test_matched_cars_without_a_run_do_not_get_a_free_overtake(self):
        self.attacker.free_air_target_v = self.defender.free_air_target_v
        self.race._resolve_battles_and_incidents(.05, ignore_event)
        self.assertEqual(self.attacker.maneuver_pass_timer, 0)
        self.assertEqual(self.attacker.v, self.defender.v)

    def test_actual_closing_run_can_trigger_pass_without_a_rating_advantage(self):
        self.attacker.free_air_target_v = self.defender.free_air_target_v
        self.attacker.v = self.defender.v + 4
        self.race._resolve_battles_and_incidents(.05, ignore_event)
        self.assertGreater(self.attacker.maneuver_pass_timer, 0)

    def test_flag_restrictions_and_teammate_hold_are_respected(self):
        for flag in ("SC", "VSC", "LIGHTS", "YELLOW"):
            self.race.flag_state = flag
            self.race.yellow_sector = self.sample["sector"]
            self.race._resolve_battles_and_incidents(.05, ignore_event)
            self.assertEqual(self.attacker.maneuver_pass_timer, 0, flag)
        self.race.flag_state = "GREEN"
        self.attacker.team_id = self.defender.team_id
        self.attacker.team_order = "HOLD"
        self.race._resolve_battles_and_incidents(.05, ignore_event)
        self.assertEqual(self.attacker.maneuver_pass_timer, 0)

    def test_passing_side_is_not_rechosen_when_cars_trade_positions_by_a_nose(self):
        self.race._resolve_battles_and_incidents(.05, ignore_event)
        lane = self.attacker.target_d
        self.attacker.total_dist = self.defender.total_dist + .5
        self.attacker.s = self.attacker.total_dist % self.race.track.length_m
        self.race.standings.reverse()
        self.race._resolve_battles_and_incidents(.05, ignore_event)
        self.assertEqual(self.attacker.target_d, lane)
        self.assertEqual(self.defender.maneuver_pass_timer, 0)

    def test_hold_order_cancels_a_teammate_tow_attack_already_in_progress(self):
        self.attacker.team_id = self.defender.team_id
        self.race._resolve_battles_and_incidents(.05, ignore_event)
        self.assertGreater(self.attacker.maneuver_pass_timer, 0)
        self.attacker.team_order = "HOLD"
        self.race._resolve_battles_and_incidents(.05, ignore_event)
        self.assertEqual(self.attacker.maneuver_pass_timer, 0)
        self.assertIsNone(self.attacker.maneuver_target_id)

    def test_following_controller_does_not_trap_a_stock_faster_car_in_tow_preparation(self):
        self.place(self.defender, self.start + 26, 0, 80, 89)
        gathered = committed = False
        for _ in range(180):
            self.race.step(.05, ignore_event)
            gathered |= self.attacker.tow_target_id == self.defender.driver_id
            committed |= self.attacker.maneuver_pass_timer > 0
            self.assertIsNone(_sat_obb_penetration(self.attacker, self.defender))
            if committed:
                break
        self.assertTrue(gathered)
        self.assertTrue(committed, "Cruising headway erased the faster car's passing run")

    def test_previous_defensive_move_does_not_lock_a_faster_car_in_the_tow(self):
        self.attacker.defense_moves = 1
        self.attacker.defending_side = 0
        self.attacker.defense_timer = 4.5
        self.race._resolve_battles_and_incidents(.05, ignore_event)
        lane = self.attacker.target_d
        self.assertNotEqual(lane, 0)
        self.race._step_car(self.attacker, self.defender, self.defender, False, .05, ignore_event)
        self.assertEqual(self.attacker.target_d, lane)

    def test_faster_car_completes_a_pass_on_a_real_straight_across_multiple_seeds(self):
        for seed in (2, 7, 19, 42):
            with self.subTest(seed=seed):
                random.seed(seed)
                self.configure_race()
                self.place(self.attacker, self.start, 0, 84, 94)
                self.place(self.defender, self.start + 18, 0, 80, 89)
                self.attacker.upgrades.update(power_unit=10, active_aero=10)
                self.defender.upgrades.update(power_unit=1, active_aero=1)
                committed = False
                complete = False
                for _ in range(200):
                    self.race.step(.05, ignore_event)
                    committed |= self.attacker.maneuver_pass_timer > 0
                    self.assertIsNone(_sat_obb_penetration(self.attacker, self.defender))
                    if self.attacker.total_dist > self.defender.total_dist + CAR_LEN_PX / self.race.track.px_per_m * 1.35:
                        complete = True
                        break
                self.assertTrue(committed, "Faster car never pulled out")
                self.assertTrue(complete, "Faster car remained trapped in the tow")


if __name__ == "__main__":
    unittest.main()
