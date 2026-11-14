"""Rival decisions must respond to race conditions and preserve player control."""
import copy
import random
import unittest
from unittest.mock import patch

from sim.data import clone_initial_roster, TIRE_COMPOUNDS
from sim.physics import RaceSession
from sim.pitwall import PitCall
from sim.tracks import COMPILED_TRACKS


class RivalPitWallTests(unittest.TestCase):
    def setUp(self):
        state = random.getstate()
        self.addCleanup(random.setstate, state)
        random.seed(42)
        teams, drivers = clone_initial_roster()
        track = next(t for t in COMPILED_TRACKS if t.id == "bahrain")
        active = [d for d in drivers if d.get("team_id")]
        self.race = RaceSession(track, {t["id"]: t for t in teams}, active,
                                0.0, 0.0, "williams", rain_scheduled=False)
        self.wall = self.race.pitwall
        self.car = self.race.cars_by_id["russell"]
        self.mate = self.race.cars_by_id["antonelli"]
        self.rival = self.race.cars_by_id["leclerc"]
        self.player = self.race.cars_by_id["sainz"]
        self.race.cars = [self.car]
        self.race.lights_out = True
        self.race.flag_state = "GREEN"
        self.race.race_clock = 700.0
        self.events = []
        self.configure(self.car)

    def emit(self, kind, message):
        self.events.append((kind, message))

    def configure(self, car, lap=10, wear=0.4, age=8, compound="MEDIUM"):
        car.compound = compound
        car.compounds_used = {compound}
        car.tire_wear = wear
        car.tire_age_laps = age
        car.tire_temp = TIRE_COMPOUNDS[compound]["ideal_temp"]
        car.pit_stops = 0
        car.lap = lap
        car.laps_completed = lap - 1
        car.s = self.race.track.length_m * 0.75
        car.total_dist = car.laps_completed * self.race.track.length_m + car.s
        car.box_this_lap = False
        car.in_pits = False
        car.wing_damage = 0.0
        car.pace_mode = "BALANCED"
        car.ers_mode = "AUTO"

    def test_wear_forecast_uses_abrasion_skill_and_observed_degradation(self):
        baseline = self.wall.wear_per_lap(self.car, "MEDIUM")
        self.car.skills["tire_mgmt"] = 72
        self.car.upgrades["chassis"] = 2
        self.assertGreater(self.wall.wear_per_lap(self.car, "MEDIUM"), baseline)
        self.car.tire_wear = 0.65
        self.car.tire_age_laps = 5
        self.assertGreater(self.wall.wear_per_lap(self.car, "MEDIUM", observed=True), baseline)

    def test_healthy_early_stint_is_extended_but_worn_tyres_are_replaced(self):
        self.configure(self.car, lap=3, age=2, wear=0.1)
        self.assertIsNone(self.wall.plan(self.car))
        self.configure(self.car, wear=0.65)
        call = self.wall.plan(self.car)
        self.assertIsNotNone(call)
        self.assertNotEqual(call.compound, "MEDIUM")

    def test_safety_car_can_open_a_window_that_is_not_worth_taking_under_green(self):
        self.configure(self.car, lap=11, wear=0.35, age=10)
        self.assertIsNone(self.wall.plan(self.car))
        green_loss = self.wall.pit_loss(self.car)
        self.race.flag_state = "SC"
        self.assertLess(self.wall.pit_loss(self.car), green_loss)
        call = self.wall.plan(self.car)
        self.assertIsNotNone(call)
        self.assertIn("neutralisation", call.reason)

    def test_rejoin_traffic_can_make_an_overcut_better_than_an_immediate_stop(self):
        self.configure(self.car, lap=13, wear=0.35, age=12)
        self.assertIsNotNone(self.wall.plan(self.car))
        rejoin = self.car.total_dist - self.wall.pit_loss(self.car) * self.wall.mean_speed
        self.configure(self.rival)
        self.rival.total_dist = rejoin + self.wall.mean_speed * 0.4
        self.rival.s = self.rival.total_dist % self.race.track.length_m
        self.rival.car_perf_index = 70
        self.rival.tire_age_laps = 0
        self.race.cars.append(self.rival)
        self.assertIsNone(self.wall.plan(self.car))
        self.assertIn("traffic", self.car.strategy_status)

    def test_nearby_rivals_create_undercut_and_cover_incentives(self):
        self.car.tire_wear = 0.6
        self.configure(self.rival, age=9)
        self.race.cars.append(self.rival)
        self.rival.total_dist = self.car.total_dist + self.wall.mean_speed
        gain, reason = self.wall._battle_incentive(self.car, "SOFT", 0.0, 25.0)
        self.assertGreater(gain, 0)
        self.assertIn("undercut", reason)
        self.rival.total_dist = self.car.total_dist - 15.0 * self.wall.mean_speed
        self.rival.pit_stops = 1
        self.rival.tire_age_laps = 0
        gain, reason = self.wall._battle_incentive(self.car, "SOFT", 0.0, 25.0)
        self.assertGreater(gain, 0)
        self.assertIn("cover", reason)

    def test_dry_compound_deadline_and_no_unnecessary_last_lap_stop(self):
        self.configure(self.car, lap=21, age=19)
        call = self.wall.plan(self.car)
        self.assertIn("second dry", call.reason)
        self.assertNotIn(call.compound, self.car.compounds_used)
        self.configure(self.car, lap=22, wear=0.45)
        self.car.compounds_used.add("HARD")
        self.assertIsNone(self.wall.plan(self.car))

    def test_sprint_does_not_invent_a_compulsory_stop(self):
        self.race.is_sprint = True
        self.race.total_laps = 8
        self.configure(self.car, lap=5, age=4, wear=0.15)
        self.assertIsNone(self.wall.plan(self.car))
        self.race.wetness, self.race.rain_intensity = 0.4, 0.8
        self.race.wet_declared = True
        call = self.wall.plan(self.car)
        self.assertIsNotNone(call)
        self.assertEqual(call.compound, "INTER")

    def test_weather_changes_select_available_tyres_without_using_hidden_forecast(self):
        self.race.wetness, self.race.rain_intensity = 0.35, 0.8
        self.race.wet_declared = True
        before = self.wall.plan(self.car)
        self.assertEqual(before.compound, "INTER")
        self.assertTrue(before.urgent)
        self.race.rain_start_clock = 1e9
        self.race.rain_duration = 0
        self.race.rain_scheduled = False
        after = self.wall.plan(self.car)
        self.assertEqual((after.compound, after.reason), (before.compound, before.reason))
        self.race.tire_allocations[self.car.driver_id]["INTER"] = 0
        self.assertEqual(self.wall.plan(self.car).compound, "WET")

    def test_damp_track_does_not_trigger_an_unnecessary_weather_stop(self):
        self.race.wetness, self.race.rain_intensity = 0.12, 0.18
        self.assertIsNone(self.wall.plan(self.car))

    def test_heavy_rain_and_drying_surface_change_the_recommended_tyre(self):
        self.configure(self.car, compound="INTER")
        self.race.wet_declared = True
        self.race.wetness, self.race.rain_intensity = 0.85, 0.9
        self.assertEqual(self.wall.plan(self.car).compound, "WET")
        self.race.wetness, self.race.rain_intensity = 0.02, 0.0
        self.assertIn(self.wall.plan(self.car).compound, ("SOFT", "MEDIUM", "HARD"))

    def test_severe_damage_is_repaired_but_small_late_damage_can_be_carried(self):
        self.car.wing_damage = 0.8
        call = self.wall.plan(self.car)
        self.assertTrue(call.urgent)
        self.assertIn("damage", call.reason)
        self.configure(self.car, lap=21, wear=0.1)
        self.car.compounds_used.add("HARD")
        self.car.wing_damage = 0.21
        self.assertIsNone(self.wall.plan(self.car))

    def test_optional_teammate_stops_are_staggered_but_safe_spacing_is_allowed(self):
        self.configure(self.mate)
        self.mate.total_dist = self.car.total_dist - self.wall.mean_speed
        self.mate.s = self.mate.total_dist % self.race.track.length_m
        self.race.cars = [self.mate, self.car]  # Opposite input order must not change priority.
        with patch.object(self.wall, "plan", side_effect=lambda car: PitCall(car, "HARD", "planned tyre stop", 3.0)):
            self.wall.step(self.emit)
        self.assertTrue(self.car.box_this_lap)
        self.assertFalse(self.mate.box_this_lap)
        self.assertIn("stacking", self.mate.strategy_status)
        self.car.box_this_lap = self.mate.box_this_lap = False
        self.mate.total_dist = self.car.total_dist - 12.0 * self.wall.mean_speed
        self.mate.s = self.mate.total_dist % self.race.track.length_m
        self.wall.next_review = 0
        with patch.object(self.wall, "plan", side_effect=lambda car: PitCall(car, "HARD", "planned tyre stop", 3.0)):
            self.wall.step(self.emit)
        self.assertTrue(self.car.box_this_lap and self.mate.box_this_lap)

    def test_unsafe_weather_allows_both_cars_to_stop_even_when_they_must_stack(self):
        self.configure(self.mate)
        self.mate.total_dist = self.car.total_dist - self.wall.mean_speed
        self.mate.s = self.mate.total_dist % self.race.track.length_m
        self.race.cars.append(self.mate)
        self.race.wetness, self.race.rain_intensity = 0.4, 0.8
        self.race.wet_declared = True
        self.wall.step(self.emit)
        self.assertTrue(self.car.box_this_lap and self.mate.box_this_lap)

    def test_player_and_disabled_autopilot_are_not_overridden(self):
        self.configure(self.player, wear=0.9)
        self.player.box_this_lap = True
        self.player.next_compound = "WET"
        self.player.pace_mode, self.player.ers_mode, self.player.team_order = "PUSH", "HARVEST", "HOLD"
        self.car.auto_strategy = False
        self.car.wing_damage = 0.9
        self.race.cars = [self.car, self.player]
        player_before = copy.deepcopy(vars(self.player))
        car_before = copy.deepcopy(vars(self.car))
        self.wall.step(self.emit)
        self.assertEqual(vars(self.player), player_before)
        self.assertEqual(vars(self.car), car_before)

    def test_pace_and_energy_recover_from_heat_and_neutralisation(self):
        self.car.tire_temp = 130
        self.wall.manage_pace(self.car, self.emit)
        self.assertEqual(self.car.pace_mode, "CONSERVE")
        self.car.tire_temp = 104
        self.race.flag_state = "SC"
        self.wall.manage_pace(self.car, self.emit)
        self.assertEqual((self.car.pace_mode, self.car.ers_mode), ("CONSERVE", "HARVEST"))
        self.race.flag_state = "GREEN"
        self.car.battery_mj = 0.8
        self.wall.manage_pace(self.car, self.emit)
        self.assertEqual(self.car.ers_mode, "HARVEST")
        self.car.battery_mj = 1.8  # Continue charging across the low threshold.
        self.wall.manage_pace(self.car, self.emit)
        self.assertEqual(self.car.ers_mode, "HARVEST")
        self.car.battery_mj = 3.0
        self.wall.manage_pace(self.car, self.emit)
        self.assertEqual((self.car.pace_mode, self.car.ers_mode), ("BALANCED", "AUTO"))

    def test_real_battle_uses_energy_and_yield_orders_expire_without_teleporting(self):
        self.configure(self.mate)
        self.mate.total_dist = self.car.total_dist - 0.5 * self.wall.mean_speed
        self.mate.free_air_target_v, self.car.free_air_target_v = 90.0, 87.0
        self.race.cars.append(self.mate)
        positions = [(car.total_dist, car.s, car.v) for car in self.race.cars]
        self.wall._team_orders(self.emit)
        self.assertEqual(self.car.team_order, "YIELD")
        self.wall.manage_pace(self.mate, self.emit)
        self.assertEqual((self.mate.pace_mode, self.mate.ers_mode), ("PUSH", "BOOST"))
        self.assertEqual([(car.total_dist, car.s, car.v) for car in self.race.cars], positions)
        self.race.race_clock += 13
        self.race.flag_state = "YELLOW"
        self.wall._team_orders(self.emit)
        self.assertEqual(self.car.team_order, "FREE")

    def test_weather_call_can_be_cancelled_before_entry_when_conditions_reverse(self):
        self.configure(self.car, lap=3, age=2, wear=0.1)
        self.race.wetness, self.race.rain_intensity = 0.4, 0.8
        self.race.wet_declared = True
        self.wall.step(self.emit)
        self.assertTrue(self.car.box_this_lap)
        self.race.wetness, self.race.rain_intensity = 0.0, 0.0
        self.race.race_clock += 2.1
        self.wall.step(self.emit)
        self.assertFalse(self.car.box_this_lap)
        self.assertTrue(any("Stay out" in message for _, message in self.events))

    def test_no_available_sets_do_not_create_tyres_and_penalty_is_still_served(self):
        self.race.tire_allocations[self.car.driver_id] = dict.fromkeys(TIRE_COMPOUNDS, 0)
        self.assertIsNone(self.wall.plan(self.car))
        self.car.drive_through_pending = True
        self.car.drive_through_laps_left = 1
        self.assertIn("drive-through", self.wall.plan(self.car).reason)

    def test_small_window_changes_do_not_cancel_a_valid_weather_call(self):
        self.configure(self.car, compound="INTER")
        self.race.wetness = self.race.rain_intensity = 0.0
        self.race.wet_declared = True
        self.car.box_this_lap = True
        self.car.next_compound = "SOFT"
        self.car.strategy_status = "Box: switch tyres for changing track conditions"
        with patch.object(self.wall, "plan", return_value=None):
            self.wall._review_queued_stop(self.car, self.emit)
        self.assertTrue(self.car.box_this_lap)
        self.assertTrue(self.car.strategy_status.startswith("Box:"))
        self.assertEqual(self.events, [])


if __name__ == "__main__":
    unittest.main()
