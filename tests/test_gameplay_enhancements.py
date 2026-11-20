"""Functional tests for interactive qualifying, weather radar, practice confidence, red flags, morale, board goals & scenarios."""

from __future__ import annotations

import random
import tempfile
import unittest
from pathlib import Path

from sim.championship import ChampionshipWorld, PITWALL_SCENARIOS
from sim.data import MAX_UPGRADES_PER_RACE, SETUP_LEVELS, clone_initial_roster
from sim.physics import QualifyingSession, RaceSession
from sim.tracks import COMPILED_TRACKS


class GameplayEnhancementsTests(unittest.TestCase):
    def setUp(self):
        state = random.getstate()
        self.addCleanup(random.setstate, state)
        random.seed(12345)
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.save_path = Path(self._tmp.name) / "career.json"
        self.world = ChampionshipWorld(self.save_path)
        self.player_drivers = [d for d in self.world.drivers if d.get("team_id") == self.world.player_team_id]
        self.drv_a = self.player_drivers[0]["id"]
        self.drv_b = self.player_drivers[1]["id"]

    def test_interactive_qualifying_hold_release_tow_and_traffic(self):
        self.world._start_qualifying()
        qs = self.world.quali_session
        self.assertIsNotNone(qs)
        car_a = next(c for c in qs.cars if c.driver_id == self.drv_a)
        car_b = next(c for c in qs.cars if c.driver_id == self.drv_b)
        self.assertEqual(car_a.quali_run_phase, "GARAGE")

        # Hold car A, advance past auto release timer -> stays in GARAGE
        res_hold = self.world.pit_wall_command(self.drv_a, {"quali_hold": True})
        self.assertTrue(res_hold["ok"])
        for _ in range(40):
            qs.step(0.2, lambda k, m: None)
        self.assertEqual(car_a.quali_run_phase, "GARAGE")

        # Swap garage compound and send car A now -> leaves garage cleanly
        swap_res = self.world.pit_wall_command(self.drv_a, {"next_compound": "MEDIUM"})
        self.assertTrue(swap_res["ok"])
        self.assertEqual(car_a.compound, "MEDIUM")

        send_res = self.world.pit_wall_command(self.drv_a, {"quali_send_now": True})
        self.assertTrue(send_res["ok"])
        qs.step(0.1, lambda k, m: None)
        self.assertEqual(car_a.quali_run_phase, "OUTLAP")

        # Verify traffic summary & track evolution increment
        for _ in range(15):
            qs.step(0.2, lambda k, m: None)
        traffic = qs.get_traffic_summary()
        self.assertGreaterEqual(traffic["on_track"], 1)
        self.assertEqual(len(traffic["sectors"]), 3)
        self.assertIn(traffic["density"], ("CLEAN", "MODERATE", "HEAVY"))
        self.assertGreater(qs.track_evolution, 0.0)

        # Tow release on remaining garage car(s)
        car_b.quali_run_phase = "GARAGE"
        car_b.quali_hold_in_garage = True
        tow_res = self.world.pit_wall_command(self.drv_b, {"quali_tow_pair": True})
        self.assertTrue(tow_res["ok"])
        self.assertFalse(car_b.quali_hold_in_garage)

    def test_weather_radar_cone_and_pitwall_invariance(self):
        teams, drivers = clone_initial_roster()
        tmap = {t["id"]: t for t in teams}
        active = [d for d in drivers if d.get("team_id")]
        track = next(t for t in COMPILED_TRACKS if t.id == "britain")

        dry_race = RaceSession(track, tmap, active, 0.0, 0.05, "williams", rain_scheduled=False)
        dry_radar = dry_race.get_weather_radar()
        self.assertIn(dry_radar["trend"], ("CLEAR", "CLOUDY"))
        self.assertEqual(len(dry_radar["bands"]), 3)
        self.assertTrue(all(0 <= b["pct"] <= 40 for b in dry_radar["bands"]))

        wet_race = RaceSession(track, tmap, active, 0.0, 0.50, "williams", rain_scheduled=True)
        wet_race.rain_start_clock = 95.0
        wet_race._radar_noise_s = 0.0
        wet_race.race_clock = 10.0
        wet_radar = wet_race.get_weather_radar()
        self.assertIn(wet_radar["trend"], ("APPROACHING", "CLOUDY", "CLEAR"))
        self.assertGreater(max(b["pct"] for b in wet_radar["bands"]), 45)

        # RivalPitWall must stay oblivious to hidden rain clock
        rival_car = wet_race.cars_by_id["verstappen"]
        rival_car.lap = 6
        rival_car.laps_completed = 5
        rival_car.tire_wear = 0.12
        plan_with_storm = wet_race.pitwall.plan(rival_car)
        wet_race.rain_scheduled = False
        wet_race.rain_start_clock = 999999.0
        plan_no_storm = wet_race.pitwall.plan(rival_car)
        self.assertEqual(plan_with_storm, plan_no_storm)

    def test_in_pit_wing_flap_adjust_and_double_stack_flag(self):
        self.world._start_qualifying()
        self.world._finish_qualifying_to_grid()
        self.world._start_race()
        rs = self.world.race_session
        rs.lights_out = True
        rs.flag_state = "GREEN"
        rs.lights_countdown = 0.0

        car = rs.cars_by_id[self.drv_a]
        mate = rs.cars_by_id[self.drv_b]
        car.setup_df = 0
        wing_res = self.world.pit_wall_command(self.drv_a, {"wing_adjust": 1})
        self.assertTrue(wing_res["ok"])
        self.assertEqual(car.next_wing_adjust, 1)

        # Put mate STOPPED in box while trailing car enters pit -> double_stack_held toggles
        box_s = rs._team_pit_box_s(car)
        mate.in_pits = True
        mate.pit_phase = "STOPPED"
        mate.pit_stop_timer = 2.0
        mate.s = box_s

        car.in_pits = True
        car.pit_phase = "ENTRY"
        car.s = (box_s - 4.0) % rs.track.length_m
        car.total_dist = car.s
        car.v = 22.0
        rs._step_pit_lane(car, False, 0.25, lambda k, m: None)
        self.assertTrue(car.double_stack_held)

        # Release mate and let car arrive at pit box -> +0.75s wing flap adjust executes
        mate.in_pits = False
        mate.pit_phase = "NONE"
        car.s = (box_s - 0.5) % rs.track.length_m
        car.total_dist = car.s
        car.v = 22.0
        rs._step_pit_lane(car, False, 0.1, lambda k, m: None)
        self.assertEqual(car.pit_phase, "STOPPED")
        self.assertEqual(car.setup_df, 1)
        self.assertEqual(car.next_wing_adjust, 0)
        self.assertFalse(car.double_stack_held)

    def test_pre_weekend_practice_programs_and_confidence_reward(self):
        self.assertEqual(self.world.phase, "PRE_WEEKEND")
        conf0 = self.world.driver_setup_confidence[self.drv_a]
        self.assertEqual(conf0, 55.0)

        r1 = self.world.run_practice_program(self.drv_a, "QUALI_SIM")
        self.assertTrue(r1["ok"])
        self.assertEqual(r1["runs_left"], 2)
        self.assertGreater(r1["confidence"], conf0)
        self.assertTrue(r1["bonuses"]["quali_prep"])

        r2 = self.world.run_practice_program(self.drv_a, "LONG_RUN")
        self.assertTrue(r2["ok"])
        self.assertEqual(r2["runs_left"], 1)
        self.assertTrue(r2["bonuses"]["long_run_prep"])

        # Setting matching setup bumps confidence after practice
        target = self.world.weekend_setup_target[self.drv_a]
        set_res = self.world.set_driver_setup(self.drv_a, target)
        self.assertTrue(set_res["ok"])
        self.assertGreaterEqual(set_res["confidence"], 88.0)

        # Qualifying locks practice programs under Parc Ferme
        self.world._start_qualifying()
        locked_res = self.world.run_practice_program(self.drv_a, "WET_PREP")
        self.assertFalse(locked_res["ok"])

    def test_red_flag_free_tyre_and_standing_restart(self):
        self.world._start_qualifying()
        self.world._finish_qualifying_to_grid()
        self.world._start_race()
        rs = self.world.race_session
        rs.lights_out = True
        rs.flag_state = "GREEN"
        rs.lights_countdown = 0.0

        L = rs.track.length_m
        for c in rs.cars:
            c.lap = 4
            c.laps_completed = 3
            c.total_dist = 3.2 * L + c.grid_pos * -10.0
            c.s = c.total_dist % L
        rs._update_standings(0.05, lambda k, m: None)

        pcar = rs.cars_by_id[self.drv_a]
        pcar.wing_damage = 0.50
        pcar.wing_damage_side = "LEFT"
        pcar.tire_wear = 0.45

        events = []
        triggered = rs.trigger_red_flag("Barrier test", lambda k, m: events.append((k, m)))
        self.assertTrue(triggered)
        self.assertEqual(rs.flag_state, "RED_FLAG")
        self.assertTrue(pcar.in_pits)
        self.assertEqual(pcar.wing_damage, 0.0)

        # Free tyre change via Pit Wall command
        rf_res = self.world.pit_wall_command(self.drv_a, {"red_flag_compound": "SOFT"})
        self.assertTrue(rf_res["ok"])
        self.assertEqual(pcar.compound, "SOFT")
        self.assertLess(pcar.tire_wear, 0.05)

        # Standing Restart resumes cleanly to 5 red lights while preserving lap progress
        res_resume = self.world.pit_wall_command(self.drv_a, {"resume_red_flag": True})
        self.assertTrue(res_resume["ok"])
        self.assertEqual(rs.flag_state, "LIGHTS")
        self.assertFalse(rs.lights_out)
        self.assertFalse(pcar.in_pits)
        self.assertEqual(pcar.laps_completed, 3)

    def test_morale_and_board_objectives_season_reward(self):
        base_eval = self.world.evaluate_contract_negotiation(self.drv_a, 20.0, 2)
        self.assertTrue(base_eval["ok"])
        base_ask = base_eval["asked_salary_m"]

        dmap = self.world._drivers_by_id()
        dmap[self.drv_a]["morale"] = 30
        unhappy_eval = self.world.evaluate_contract_negotiation(self.drv_a, 20.0, 2)
        self.assertGreater(unhappy_eval["asked_salary_m"], base_ask)

        dmap[self.drv_a]["morale"] = 96
        happy_eval = self.world.evaluate_contract_negotiation(self.drv_a, 20.0, 2)
        self.assertLess(happy_eval["asked_salary_m"], base_ask)

        # Verify board bonus payout + extra R&D upgrade slot next season
        self.world.board_state["target_wcc"] = 1
        self.world.team_points[self.world.player_team_id] = 999
        self.world.team_wins[self.world.player_team_id] = 20
        budget_before = self.world._teams_by_id()[self.world.player_team_id]["budget_m"]
        self.world._enter_off_season()
        self.assertEqual(self.world.board_state["extra_upgrade_slots"], 1)
        self.world._start_next_season()
        self.assertEqual(self.world.current_round, 1)
        allowance = self.world._upgrade_allowance(self.world.player_team_id)
        self.assertEqual(allowance["limit"], MAX_UPGRADES_PER_RACE + 1)
        self.assertGreater(self.world._teams_by_id()[self.world.player_team_id]["budget_m"], budget_before)

    def test_quick_play_scenarios_isolate_career_save(self):
        self.world.current_round = 5
        self.world._save_state()
        saved_before = self.save_path.read_text(encoding="utf-8")

        for sc in PITWALL_SCENARIOS:
            res = self.world.start_scenario(sc["id"])
            self.assertTrue(res["ok"], f"Failed scenario {sc['id']}: {res}")
            self.assertEqual(self.world.phase, "RACE")
            self.assertEqual(self.world.current_track.id, sc["track_id"])
            # Save file must stay completely untouched during scenario
            self.assertEqual(self.save_path.read_text(encoding="utf-8"), saved_before)

        exit_res = self.world.exit_scenario()
        self.assertTrue(exit_res["ok"])
        self.assertTrue(exit_res["restored"])
        self.assertIsNone(self.world.active_scenario)
        self.assertEqual(self.world.current_round, 5)

    def test_battle_forecast_predicts_catch_and_defend(self):
        self.world._start_qualifying()
        self.world._finish_qualifying_to_grid()
        self.world._start_race()
        rs = self.world.race_session
        rs.lights_out = True
        rs.flag_state = "GREEN"
        rs.lights_countdown = 0.0

        lead = rs.standings[0]
        chase = rs.standings[1]
        chase.interval_ahead = 3.2
        chase.recent_lap_times = [78.0, 77.9]
        lead.recent_lap_times = [79.0, 79.1]
        fcst = rs.pitwall.battle_forecast(chase)
        self.assertIsNotNone(fcst)
        self.assertEqual(fcst["type"], "CATCH")
        self.assertEqual(fcst["target"], lead.code)
        self.assertGreaterEqual(fcst["laps"], 1)


if __name__ == "__main__":
    unittest.main()
