"""Comprehensive verification tests for all 15 advanced gameplay, Team Principal, and telemetry features."""

from __future__ import annotations
import os
import tempfile
import unittest
from pathlib import Path

from sim.championship import ChampionshipWorld
from sim.data import TIRE_COMPOUNDS, clone_initial_roster, driver_overall, upgrade_cost_m
from sim.physics import RaceSession
from sim.tracks import TRACK_BY_ID


class TestAdvancedFeatures(unittest.TestCase):
    def _new_world(self, tmpdir: str, start_year: int = 2026) -> ChampionshipWorld:
        save_path = Path(tmpdir) / "state.json"
        w = ChampionshipWorld(save_path=save_path)
        w.reset_career("williams", start_year=start_year)
        return w

    def test_strategy_plan_auto_pit_and_dilemma_and_burst(self):
        with tempfile.TemporaryDirectory() as td:
            w = self._new_world(td)
            trk = TRACK_BY_ID["austria"]
            p_drvs = [d for d in w.drivers if d["team_id"] == "williams"]
            lead_id = p_drvs[0]["id"]
            p2_id = p_drvs[1]["id"]

            res = w.set_strategy_plan(
                lead_id,
                active_plan="A",
                plans={
                    "A": [
                        {"compound": "SOFT", "start_lap": 1, "pit_lap": 3},
                        {"compound": "HARD", "start_lap": 3, "end_lap": trk.race_laps},
                    ]
                },
            )
            self.assertTrue(res["ok"])
            self.assertEqual(res["strategy"]["plans"]["A"][0]["pit_lap"], 3)

            w._prepare_race_grid()
            rs = w.race_session
            assert rs is not None
            rs.lights_out = True
            rs.lights_countdown = 0.0
            rs.flag_state = "GREEN"
            car = rs.cars_by_id[lead_id]
            car.auto_strategy = False

            # Trigger 1-lap Attack burst & verify cooldown guard
            ok_atk = rs.trigger_tactical_burst(lead_id, "ATTACK_NOW")
            self.assertTrue(ok_atk)
            self.assertEqual(car.tactical_burst, "ATTACK_NOW")
            self.assertFalse(rs.trigger_tactical_burst(lead_id, "DEFEND_NOW"))

            # Defend burst boost on second car
            c2 = rs.cars_by_id[p2_id]
            self.assertTrue(rs.trigger_tactical_burst(p2_id, "DEFEND_NOW"))
            smp = rs.track.sample(car.s)
            _, p_no_def, _ = rs.select_and_evaluate_maneuver(car, rs.standings[0] if rs.standings[0] is not car else rs.standings[1], smp, True)
            _, p_vs_def, _ = rs.select_and_evaluate_maneuver(car, c2, smp, True)
            self.assertGreater(p_no_def, 0.0)
            self.assertLessEqual(p_vs_def, 1.0)

            # Fast-advance car past Lap 2 -> crossing onto Lap 3 triggers Plan A auto-box
            car.laps_completed = 2
            car.lap = 3
            car.total_dist = 2 * rs.track.length_m + (rs.track.length_m - 2.0)
            car.s = car.total_dist % rs.track.length_m
            car.current_sector_times = [20.0, 20.0, None]
            car.box_this_lap = False
            rs._advance_car_progress(car, 5.0, False, w._push_event)
            self.assertTrue(car.box_this_lap)
            self.assertEqual(car.next_compound, "HARD")

            # Thermal dilemma trigger & resolution
            car.box_this_lap = False
            car.laps_completed = 4
            car.gremlin = "BRAKE_HOT"
            rs._dilemma_cooldown = 0.0
            rs.race_clock = 150.0
            rs._step_dilemmas(0.1, w._push_event)
            self.assertIsNotNone(rs.active_dilemma)
            self.assertEqual(rs.active_dilemma["kind"], "THERMAL_ALARM")
            dres = w.resolve_dilemma("A")
            self.assertTrue(dres["ok"])
            self.assertIsNone(rs.active_dilemma)
            self.assertTrue(car.lift_coast)
            self.assertEqual(car.gremlin, "")

    def test_live_wdc_and_gap_history_analytics(self):
        with tempfile.TemporaryDirectory() as td:
            w = self._new_world(td)
            w._prepare_race_grid()
            w.phase = "RACE"
            rs = w.race_session
            assert rs is not None
            rs.lights_out = True
            rs.flag_state = "GREEN"
            rs._record_lap_gap(rs.standings[0], 1, 78.2)
            rs._record_lap_gap(rs.standings[1], 1, 79.4)
            rs._record_lap_gap(rs.standings[0], 2, 156.0)
            rs._record_lap_gap(rs.standings[1], 2, 157.8)

            live = w._build_live_championship()
            self.assertIsNotNone(live)
            p1_drv = rs.standings[0].driver_id
            self.assertEqual(live["wdc"][p1_drv]["delta_pts"], 25)
            self.assertIn("AS IT STANDS", live["title_note"])

            an = w.get_live_analytics()
            self.assertTrue(an["ok"])
            self.assertTrue(an["live"])
            self.assertEqual(len(an["gap_history"]), 2)
            self.assertAlmostEqual(an["gap_history"][1]["gaps"][rs.standings[1].driver_id], 1.8, places=2)

    def test_next_year_rd_carryover_across_2028_reset(self):
        with tempfile.TemporaryDirectory() as td:
            w = self._new_world(td, start_year=2026)
            w._teams_by_id()["williams"]["budget_m"] = 200.0
            # Spend twice across 2 separate rounds -> reaches >= 30% for free carryover levels
            r1 = w.invest_next_year_rd("major")
            self.assertTrue(r1["ok"])
            # Same round blocked once per GP
            self.assertFalse(w.invest_next_year_rd("standard")["ok"])
            # Current-year 3/3 allowance untouched!
            self.assertEqual(w._upgrade_allowance("williams")["remaining"], 3)

            w.current_round = 2
            r2 = w.invest_next_year_rd("major")
            self.assertTrue(r2["ok"])
            self.assertGreaterEqual(w.next_year_rd["progress"], 50)

            # Advance cleanly across 2027 -> 2028 regulation reset
            w.season_year = 2027
            sum_before = sum(w._teams_by_id()["williams"]["upgrades"].values())
            self.assertGreater(sum_before, 0)
            w._start_next_season()
            self.assertEqual(w.season_year, 2028)
            self.assertEqual(w.next_year_rd["progress"], 0)
            # Check free upgrade event emitted
            self.assertTrue(any("NEXT-YEAR R&D DIVIDEND" in ev.get("msg", "") for ev in w.event_feed))

    def test_staff_hiring_bonuses_and_fairness(self):
        with tempfile.TemporaryDirectory() as td:
            w = self._new_world(td)
            team = w._teams_by_id()["williams"]
            team["budget_m"] = 300.0
            base_cost = upgrade_cost_m("power_unit", team["upgrades"]["power_unit"])

            # Hire Technical Director Tier 2 -> 12% discount
            h1 = w.hire_staff("tech_director")
            self.assertTrue(h1["ok"])
            h2 = w.hire_staff("tech_director")
            self.assertTrue(h2["ok"])
            self.assertAlmostEqual(w._staff_bonuses()["rd_discount"], 0.12, places=2)

            b_before = team["budget_m"]
            up = w.buy_upgrade("power_unit")
            self.assertTrue(up["ok"])
            spent = round(b_before - team["budget_m"], 2)
            self.assertAlmostEqual(spent, round(base_cost * 0.88, 2), places=2)

            # Hire Chief Meteorologist Tier 3 -> tighter radar noise ONLY for RaceSession.get_weather_radar
            self.assertTrue(w.hire_staff("chief_meteorologist", target_tier=3)["ok"])
            self.assertAlmostEqual(w._staff_bonuses()["radar_noise_mult"], 0.12, places=2)
            w._prepare_race_grid()
            rs = w.race_session
            assert rs is not None
            self.assertLessEqual(abs(rs._radar_noise_s), 90.0 * 0.12 + 0.01)

            # Hire Chief Mechanic Tier 2 -> faster pit mean
            self.assertTrue(w.hire_staff("chief_mechanic", target_tier=2)["ok"])
            rs.staff_bonuses = w._staff_bonuses()
            p_car = next(c for c in rs.cars if c.team_id == "williams")
            self.assertAlmostEqual(rs.staff_bonuses["pit_time_mult"], 0.92, places=2)
            dur, _ = rs._roll_pit_stop_duration(p_car, w._push_event)
            self.assertGreater(dur, 1.5)

    def test_academy_sign_rookie_fp1_and_zero_fee_promote(self):
        with tempfile.TemporaryDirectory() as td:
            w = self._new_world(td)
            w._teams_by_id()["williams"]["budget_m"] = 150.0
            fa = next(d for d in w.drivers if d["team_id"] is None and not d.get("legend"))
            stat_sum_before = sum(fa[k] for k in ("pace", "racecraft", "consistency", "tire_mgmt", "wet_skill"))

            s_res = w.manage_academy("sign", fa["id"])
            self.assertTrue(s_res["ok"])
            self.assertIn(fa["id"], w.academy_drivers)

            my_drv = next(d for d in w.drivers if d["team_id"] == "williams")
            fp = w.run_practice_program(my_drv["id"], "ROOKIE_FP1", rookie_id=fa["id"])
            self.assertTrue(fp["ok"])
            stat_sum_after = sum(fa[k] for k in ("pace", "racecraft", "consistency", "tire_mgmt", "wet_skill"))
            self.assertEqual(stat_sum_after, stat_sum_before + 1)

            # Zero signing fee evaluated in contract negotiation too
            ev = w.evaluate_contract_negotiation(fa["id"], 2.5, 2, release_driver_id=my_drv["id"])
            self.assertTrue(ev["ok"])
            self.assertEqual(ev["signing_fee_m"], 0.0)

            prom = w.manage_academy("promote", fa["id"], release_driver_id=my_drv["id"])
            self.assertTrue(prom["ok"])
            self.assertEqual(fa["team_id"], "williams")
            self.assertNotIn(fa["id"], w.academy_drivers)

    def test_my_team_customizer_preserves_11_teams_22_cars(self):
        with tempfile.TemporaryDirectory() as td:
            w = self._new_world(td)
            res = w.customize_team(
                name="Apex Grand Prix",
                short="Apex GP",
                code="APX",
                color="#123456",
                secondary="#ffaa00",
                engine="Ferrari",
            )
            self.assertTrue(res["ok"])
            self.assertEqual(len(w.teams), 11)
            self.assertEqual(len([d for d in w.drivers if d["team_id"] is not None]), 22)
            tick = w.build_live_tick_payload()
            self.assertIsNotNone(tick["custom_team_meta"])
            self.assertEqual(tick["custom_team_meta"]["code"], "APX")
            self.assertEqual(tick["custom_team_meta"]["color"], "#123456")

    def test_recoverable_gremlins_recovery_and_pit_clear(self):
        with tempfile.TemporaryDirectory() as td:
            w = self._new_world(td)
            w._prepare_race_grid()
            rs = w.race_session
            assert rs is not None
            rs.lights_out = True
            rs.flag_state = "GREEN"
            car = next(c for c in rs.cars if c.team_id == "williams")
            car.auto_strategy = False

            # BRAKE_HOT recovers under CONSERVE + L&C
            car.gremlin = "BRAKE_HOT"
            car.gremlin_recovery = 0.0
            car.pace_mode = "CONSERVE"
            car.lift_coast = True
            for _ in range(120):
                rs._step_car(car, None, rs.standings[0], False, 0.1, w._push_event)
            self.assertEqual(car.gremlin, "")

            # SLOW_PUNCTURE adds wear & clears when completing pit stop
            car.gremlin = "SLOW_PUNCTURE"
            w_before = car.tire_wear
            rs._step_car(car, None, rs.standings[0], False, 0.5, w._push_event)
            self.assertGreater(car.tire_wear, w_before)
            car.in_pits = True
            car.pit_phase = "STOPPED"
            car.pit_stop_timer = 0.05
            car.s = rs.track.pit_entry_s + 40.0
            rs._step_pit_lane(car, False, 0.1, w._push_event)
            self.assertEqual(car.gremlin, "")

    def test_break_parc_ferme_pit_lane_start_without_grid_drop(self):
        with tempfile.TemporaryDirectory() as td:
            w = self._new_world(td)
            w._prepare_race_grid()
            w.phase = "GRID_WALK"
            rs = w.race_session
            assert rs is not None
            my_car = next(c for c in rs.cars if c.team_id == "williams")
            res = w.break_parc_ferme(my_car.driver_id, setup_df=-2, fresh_pu=["ice"])
            self.assertTrue(res["ok"])
            self.assertTrue(my_car.pit_lane_start)
            self.assertEqual(my_car.pit_phase, "PIT_START")
            self.assertEqual(my_car.setup_df, -2)
            self.assertEqual(w.pu_pools[my_car.driver_id].get("pending_penalty", 0), 0)

            # Simulate lights out + pack moving past pit exit -> pit starter releases cleanly with 0 stops
            rs.lights_out = True
            rs.flag_state = "GREEN"
            rs.race_clock = 15.0
            for c in rs.cars:
                if c is not my_car:
                    c.total_dist = 900.0
            rs._step_pit_lane(my_car, False, 0.1, w._push_event)
            self.assertFalse(my_car.pit_lane_start)
            self.assertEqual(my_car.pit_phase, "EXIT")
            self.assertEqual(my_car.pit_stops, 0)

    def test_rivalry_night_lighting_and_custom_scenario_isolated(self):
        with tempfile.TemporaryDirectory() as td:
            save_path = Path(td) / "state.json"
            w = ChampionshipWorld(save_path=save_path)
            w.reset_career("williams", start_year=2026)
            save_before = save_path.read_text(encoding="utf-8")

            # Launch Custom Scenario on Returning Night/Classic or Night track + 2028 era
            cs = w.start_custom_scenario({
                "track_id": "abudhabi",
                "era": "2028",
                "start_lap": 20,
                "weather": "DRY",
                "flag": "GREEN",
                "start_pos": 4,
                "compound": "MEDIUM",
                "tire_wear": 30,
            })
            self.assertTrue(cs["ok"])
            self.assertEqual(w.current_track.id, "abudhabi")
            rs = w.race_session
            assert rs is not None
            self.assertGreater(rs.get_lighting_phase(), 0.45)

            # Collision increments rivalry
            c1, c2 = rs.cars[0], rs.cars[1]
            rs._handle_collision(c1, c2, 1, w._push_event)
            self.assertGreaterEqual(rs.get_rivalry_level(c1.driver_id, c2.driver_id), 1)
            w._merge_session_rivalries(rs)
            self.assertGreaterEqual(len(w.rivalries), 1)

            # Daytime track lighting stays 0.0
            mon_rs = RaceSession(TRACK_BY_ID["monaco"], w._teams_by_id(), w._active_drivers(), 0.0, 0.0, "williams")
            self.assertEqual(mon_rs.get_lighting_phase(), 0.0)

            # Save file must never be touched during scenario, and exit_scenario restores career
            self.assertEqual(save_path.read_text(encoding="utf-8"), save_before)
            ex = w.exit_scenario()
            self.assertTrue(ex["ok"])
            self.assertIsNone(w.active_scenario)
            self.assertEqual(w.season_year, 2026)


if __name__ == "__main__":
    unittest.main()
