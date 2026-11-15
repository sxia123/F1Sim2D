"""Regression and functional unit tests covering all 12 simulator enhancements."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from sim.championship import ChampionshipWorld
from sim.data import (
    PU_COMPONENT_SPECS,
    circuit_car_rating,
    create_weekend_tire_sets,
    effective_track_upgrades,
    summarize_tire_sets,
    track_upgrade_profile,
)
from sim.hall_of_fame import generate_default_season_archives
from sim.tracks import get_season_tracks


def _track_by_id(tid: str):
    return next((t for t in get_season_tracks(2026) if t.id == tid), None)


class SimulatorEnhancementsTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.save_path = Path(self._tmp.name) / "career.json"
        self.world = ChampionshipWorld(self.save_path)
        self.player_drivers = [d for d in self.world.drivers if d.get("team_id") == self.world.player_team_id]
        self.drv_id = self.player_drivers[0]["id"]

    def test_01_and_02_pit_rejoin_ghost_and_strategy_advice(self):
        self.world._start_qualifying()
        self.world._finish_qualifying_to_grid()
        self.world._start_race()
        rs = self.world.race_session
        self.assertIsNotNone(rs)
        rs.lights_out = True
        rs.flag_state = "GREEN"
        rs.lights_countdown = 0.0
        for _ in range(30):
            rs.step(0.1, lambda k, m: None)

        car = rs.cars_by_id[self.drv_id]
        proj = rs.pitwall.project_rejoin(car)
        self.assertGreaterEqual(proj["pos"], 1)
        self.assertLessEqual(proj["pos"], len(rs.cars))
        self.assertGreaterEqual(proj["traffic_s"], 0.0)
        self.assertTrue(isinstance(proj["x"], float) and isinstance(proj["y"], float))

        rs.pitwall.advise(car)
        self.assertIsNotNone(car.strategy_advice)
        self.assertIn(car.strategy_advice["action"], ("BOX", "STAY_OUT"))

        tick = self.world.build_live_tick_payload()
        pcar = next(c for c in tick["cars"] if c["id"] == self.drv_id)
        self.assertIn("rejoin_pos", pcar)
        self.assertIn("rejoin_traffic_s", pcar)
        self.assertIn("rejoin_x", pcar)
        self.assertIn("rejoin_y", pcar)
        self.assertIn("advice", pcar)

    def test_03_scrubbed_vs_fresh_tyre_inventory(self):
        self.world._start_qualifying()
        self.world._finish_qualifying_to_grid()
        # Inject one scrubbed MEDIUM set alongside fresh MEDIUM sets (3 MEDIUM allocated total)
        tsets = create_weekend_tire_sets()
        self.world.tire_sets[self.drv_id] = tsets
        self.world._prepare_race_grid()
        rs = self.world.race_session
        rs._refund_tire_set_record(self.drv_id, rs.cars_by_id[self.drv_id].compound, 0.0, False)
        rs.tire_sets[self.drv_id]["MEDIUM"][0]["in_use"] = False
        rs.tire_sets[self.drv_id]["MEDIUM"][0]["scrubbed"] = True
        rs.tire_sets[self.drv_id]["MEDIUM"][0]["wear"] = 0.06
        for idx in (1, 2):
            rs.tire_sets[self.drv_id]["MEDIUM"][idx]["in_use"] = False
            rs.tire_sets[self.drv_id]["MEDIUM"][idx]["scrubbed"] = False
            rs.tire_sets[self.drv_id]["MEDIUM"][idx]["wear"] = 0.0
        car = rs.cars_by_id[self.drv_id]

        car.prefer_fresh_tyre = False
        wear_scrub, is_scrub = rs._draw_tire_set_record(self.drv_id, "MEDIUM", prefer_fresh=False)
        self.assertTrue(is_scrub)
        self.assertAlmostEqual(wear_scrub, 0.06, places=2)

        wear_fresh, is_scrub2 = rs._draw_tire_set_record(self.drv_id, "MEDIUM", prefer_fresh=True)
        self.assertFalse(is_scrub2)
        self.assertAlmostEqual(wear_fresh, 0.0, places=2)

        summ = summarize_tire_sets(rs.tire_sets[self.drv_id])
        self.assertEqual(summ["MEDIUM"]["fresh"], 1)
        self.assertEqual(summ["MEDIUM"]["scrubbed"], 0)

    def test_04_circuit_specific_upgrade_scaling(self):
        monza = _track_by_id("italy")
        monaco = _track_by_id("monaco")
        self.assertIsNotNone(monza)
        self.assertIsNotNone(monaco)

        monza_prof = track_upgrade_profile(monza)
        monaco_prof = track_upgrade_profile(monaco)
        self.assertGreater(monza_prof["weights"]["power_unit"], 1.2)
        self.assertGreater(monaco_prof["weights"]["chassis"], 1.2)

        pu_heavy_team = {
            "id": "pu_team",
            "upgrades": {"power_unit": 9, "active_aero": 9, "chassis": 4, "suspension": 4, "reliability": 6, "pit_crew": 6},
        }
        df_heavy_team = {
            "id": "df_team",
            "upgrades": {"power_unit": 4, "active_aero": 6, "chassis": 9, "suspension": 9, "reliability": 6, "pit_crew": 6},
        }
        self.assertGreater(circuit_car_rating(pu_heavy_team, monza), circuit_car_rating(df_heavy_team, monza))
        self.assertGreater(circuit_car_rating(df_heavy_team, monaco), circuit_car_rating(pu_heavy_team, monaco))

        eff = effective_track_upgrades(pu_heavy_team["upgrades"], monza)
        self.assertGreater(eff["power_unit"], 9.0)

    def test_05_drying_racing_groove_and_offline_wetness(self):
        self.world._start_qualifying()
        self.world._finish_qualifying_to_grid()
        self.world._start_race()
        rs = self.world.race_session
        rs.lights_out = True
        rs.flag_state = "GREEN"
        rs.lights_countdown = 0.0
        rs.wetness = 0.35
        rs.groove_wetness = 0.35
        rs.offline_wetness = 0.35
        rs.rain_active = False
        rs.wet_peak = 0.0

        for _ in range(80):
            rs.step(0.2, lambda k, m: None)

        self.assertLess(rs.groove_wetness, rs.offline_wetness)
        tick = self.world.build_live_tick_payload()
        self.assertLessEqual(tick["groove_wetness"], tick["offline_wetness"])

    def test_06_fuel_load_burn_and_lift_coast(self):
        self.world._start_qualifying()
        self.world._finish_qualifying_to_grid()
        self.world._start_race()
        rs = self.world.race_session
        rs.lights_out = True
        rs.flag_state = "GREEN"
        rs.lights_countdown = 0.0
        rs.step(0.1, lambda k, m: None)

        car_norm = rs.cars_by_id[self.player_drivers[0]["id"]]
        car_lc = rs.cars_by_id[self.player_drivers[1]["id"]]
        car_norm.setup_df = 0
        car_lc.setup_df = 0
        car_norm.pace_mode = "BALANCED"
        car_lc.pace_mode = "BALANCED"
        start_fuel_a = car_norm.fuel_kg
        start_fuel_b = car_lc.fuel_kg
        start_dist_a = car_norm.total_dist
        start_dist_b = car_lc.total_dist

        res = self.world.pit_wall_command(car_lc.driver_id, {"lift_coast": True})
        self.assertTrue(res["ok"])
        self.assertTrue(car_lc.lift_coast)

        car_norm.v = 65.0
        car_lc.v = 65.0
        for _ in range(50):
            rs.step(0.1, lambda k, m: None)

        burn_per_m_norm = (start_fuel_a - car_norm.fuel_kg) / max(1.0, car_norm.total_dist - start_dist_a)
        burn_per_m_lc = (start_fuel_b - car_lc.fuel_kg) / max(1.0, car_lc.total_dist - start_dist_b)
        self.assertGreater(burn_per_m_norm, 0.0)
        self.assertGreater(burn_per_m_lc, 0.0)
        self.assertLess(burn_per_m_lc, burn_per_m_norm * 0.85)

    def test_06b_lift_coast_balanced_for_push_and_attack(self):
        self.world._start_qualifying()
        self.world._finish_qualifying_to_grid()
        self.world._start_race()
        rs = self.world.race_session
        rs.lights_out = True
        rs.flag_state = "GREEN"
        rs.lights_countdown = 0.0

        def run_mode(pace_mode: str, lift_coast: bool):
            car = rs.cars_by_id[self.player_drivers[0]["id"]]
            ref = rs.cars_by_id[self.player_drivers[1]["id"]]
            car.upgrades = dict(ref.upgrades)
            car.skills = dict(ref.skills)
            car.setup_df = 0
            car.compound = "SOFT"
            car.pace_mode = pace_mode
            car.lift_coast = lift_coast
            car.lift_coast_manual = True
            car.auto_strategy = False
            car.tire_wear = 0.05
            car.tire_temp = 95.0
            car.fuel_kg = 100.0
            car.lap = 2
            corner_s = rs.track.corners[0]["s_m"] if rs.track.corners else 300.0
            car.s = (corner_s - 45.0) % rs.track.length_m
            car.total_dist = rs.track.length_m + car.s
            car.v = 68.0
            car.g_lat = 0.0
            start_dist = car.total_dist
            for _ in range(80):
                rs._step_car(car, None, None, False, 0.1, lambda k, m: None)
            burn_per_m = (100.0 - car.fuel_kg) / max(1.0, car.total_dist - start_dist)
            return car.tire_temp, car.tire_wear - 0.05, burn_per_m

        bal_temp, _bal_wear, _bal_fuel = run_mode("BALANCED", False)
        blc_temp, blc_wear, blc_fuel = run_mode("BALANCED", True)
        atk_temp, atk_wear, atk_fuel = run_mode("ATTACK", True)

        self.assertLess(blc_temp, bal_temp)
        self.assertGreater(atk_temp, bal_temp)
        self.assertGreater(atk_wear, blc_wear)
        self.assertGreater(atk_fuel, blc_fuel)

    def test_07_garage_based_qualifying_runs(self):
        self.world._start_qualifying()
        qs = self.world.quali_session
        phases_seen = {c.quali_run_phase for c in qs.cars}
        self.assertIn("GARAGE", phases_seen | {c.quali_run_phase for c in qs.cars})

        seen_push_or_outlap = set()
        for _ in range(250):
            qs.step(0.2, lambda k, m: None)
            for c in qs.cars:
                seen_push_or_outlap.add(c.quali_run_phase)
        self.assertTrue("OUTLAP" in seen_push_or_outlap or "PUSH" in seen_push_or_outlap)

    def test_08_pu_pool_usage_and_fia_grid_penalty(self):
        limit = PU_COMPONENT_SPECS["ice"]["limit"]
        # Consume quota without penalty
        for _ in range(limit - 1):
            r = self.world.replace_pu_component(self.drv_id, "ice")
            self.assertTrue(r["ok"])
            self.assertEqual(r["penalty_added"], 0)

        # Next swap exceeds seasonal limit -> triggers FIA grid drop
        over = self.world.replace_pu_component(self.drv_id, "ice")
        self.assertTrue(over["ok"])
        self.assertEqual(over["penalty_added"], PU_COMPONENT_SPECS["ice"]["first_penalty"])

        self.world.grid_order_ids = [d["id"] for d in self.world._active_drivers()]
        orig_idx = self.world.grid_order_ids.index(self.drv_id)
        if orig_idx > 12:
            # Put player driver on pole first to guarantee room to drop
            self.world.grid_order_ids.remove(self.drv_id)
            self.world.grid_order_ids.insert(0, self.drv_id)
            orig_idx = 0

        self.world._prepare_race_grid()
        new_idx = self.world.grid_order_ids.index(self.drv_id)
        self.assertGreater(new_idx, orig_idx)
        self.assertEqual(self.world.pu_pools[self.drv_id]["pending_penalty"], 0)

    def test_09_multi_year_contract_negotiations(self):
        # Test lowball decline vs accepted own renewal
        low = self.world.evaluate_contract_negotiation(self.drv_id, 0.5, 4)
        self.assertTrue(low["ok"])
        self.assertFalse(low["accepted"])

        fair = self.world.evaluate_contract_negotiation(self.drv_id, 55.0, 3)
        self.assertTrue(fair["ok"])
        self.assertTrue(fair["accepted"])

        exec_res = self.world.execute_contract_negotiation(self.drv_id, 55.0, 3)
        self.assertTrue(exec_res["ok"])
        updated = self.world._drivers_by_id()[self.drv_id]
        self.assertEqual(updated["contract_years"], 3)
        self.assertAlmostEqual(updated["salary_m"], 55.0, places=1)

    def test_10_pre_weekend_setup_and_parc_ferme_lock(self):
        res = self.world.set_driver_setup(self.drv_id, 2)
        self.assertTrue(res["ok"])
        self.assertEqual(self.world.driver_setups[self.drv_id], 2)

        self.world._start_qualifying()
        self.assertTrue(self.world.is_parc_ferme_locked())
        locked = self.world.set_driver_setup(self.drv_id, -2)
        self.assertFalse(locked["ok"])
        self.assertIn("Parc Ferme", locked["error"])

    def test_11_and_12_lap_chart_stints_and_payloads(self):
        self.world._start_qualifying()
        self.world._finish_qualifying_to_grid()
        self.world._start_race()
        rs = self.world.race_session
        rs.lights_out = True
        rs.flag_state = "GREEN"
        rs.lights_countdown = 0.0
        # Simulate crossing lap 1 and 2 manually cleanly via lap_cross_times + stints check
        for idx, c in enumerate(rs.cars):
            c.lap = 3
            c.laps_completed = 2
            c.lap_cross_times = {1: 82.0 + idx * 0.4, 2: 164.0 + idx * 0.6}
        self.world._conclude_race()

        pod = self.world.last_podium_summary
        self.assertIsNotNone(pod)
        self.assertGreaterEqual(len(pod["lap_chart"]), 2)
        self.assertIn(self.drv_id, pod["stints"])

        # Synthetic archives also expose lap_chart & stints
        archives = generate_default_season_archives()
        r1 = archives["2026"]["races"][0]
        self.assertIn("lap_chart", r1)
        self.assertIn("stints", r1)
        self.assertGreaterEqual(len(r1["lap_chart"]), 5)

        full_state = self.world.build_full_state_payload()
        for key in ("track_profile", "parc_ferme", "pu_pools", "driver_setups", "tire_sets_summary"):
            self.assertIn(key, full_state)

    def test_13_http_api_routes_roundtrip(self):
        import json
        import threading
        import urllib.request
        from server import F1HTTPServer, F1RequestHandler

        prev_world = getattr(F1RequestHandler, "world", None)
        F1RequestHandler.world = self.world
        srv = F1HTTPServer(("127.0.0.1", 0), F1RequestHandler)
        port = srv.server_address[1]
        th = threading.Thread(target=srv.serve_forever, daemon=True)
        th.start()
        try:
            def post(path: str, payload: dict) -> dict:
                req = urllib.request.Request(
                    f"http://127.0.0.1:{port}{path}",
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=3) as resp:
                    return json.loads(resp.read().decode("utf-8"))

            s_res = post("/api/set_setup", {"driver_id": self.drv_id, "setup_df": -1})
            self.assertTrue(s_res["ok"])
            self.assertEqual(s_res["setup_df"], -1)

            pu_res = post("/api/replace_pu_component", {"driver_id": self.drv_id, "component": "turbo"})
            self.assertTrue(pu_res["ok"])
            self.assertEqual(pu_res["used"], 2)

            neg_eval = post("/api/negotiate_contract", {"action": "evaluate", "driver_id": self.drv_id, "salary_m": 45.0, "years": 2})
            self.assertTrue(neg_eval["ok"] and neg_eval["accepted"])

            neg_exec = post("/api/negotiate_contract", {"driver_id": self.drv_id, "salary_m": 45.0, "years": 2})
            self.assertTrue(neg_exec["ok"])

            self.world._start_qualifying()
            self.world._finish_qualifying_to_grid()
            self.world._start_race()
            pw_res = post("/api/pit_wall", {"driver_id": self.drv_id, "lift_coast": True, "prefer_fresh": False})
            self.assertTrue(pw_res["ok"])
            car = self.world.race_session.cars_by_id[self.drv_id]
            self.assertTrue(car.lift_coast)
            self.assertFalse(car.prefer_fresh_tyre)
        finally:
            srv.shutdown()
            srv.server_close()
            F1RequestHandler.world = prev_world


if __name__ == "__main__":
    unittest.main()
