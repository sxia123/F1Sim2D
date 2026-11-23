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
            w.phase = "RACE"
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
            w.phase = "RACE"
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
            w.phase = "RACE"
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

    def test_create_constructor_start_of_season(self):
        with tempfile.TemporaryDirectory() as td:
            w = self._new_world(td)
            # 1) Create a 2026 12th custom constructor with Koenigsegg icon (no teams replaced, 0 drivers initially)
            res = w.create_custom_season({
                "name": "Koenigsegg F1",
                "short": "Koenigsegg",
                "code": "KOE",
                "color": "#00e5ff",
                "secondary": "#101820",
                "engine": "Honda RBPT",
                "icon": "koenigsegg",
                "year": 2026,
                "tier": "midfield",
            })
            self.assertTrue(res["ok"])
            self.assertEqual(w.season_year, 2026)
            self.assertEqual(w.current_round, 1)
            self.assertEqual(w.phase, "PRE_WEEKEND")
            self.assertEqual(w.player_team_id, "custom")
            self.assertEqual(len(w.teams), 12)

            pt = w._teams_by_id()["custom"]
            self.assertEqual(pt["name"], "Koenigsegg F1")
            self.assertEqual(pt["code"], "KOE")
            self.assertEqual(pt["icon"], "koenigsegg")
            self.assertEqual(pt["engine"], "Honda RBPT")
            self.assertEqual(pt["budget_m"], 390.0)
            full_payload = w.build_full_state_payload()
            self.assertEqual(full_payload["player_team_id"], "custom")
            self.assertIn("finances", full_payload)
            tick_payload = w.build_live_tick_payload()
            self.assertEqual(tick_payload["custom_team_meta"]["icon"], "koenigsegg")

            # Cannot start Qualifying until 2 drivers are signed
            blocked = w.skip_session()
            self.assertFalse(blocked["ok"])

            # Sign 2 drivers after team creation (1 free agent + 1 contract negotiation)
            fa1 = next(d for d in w.drivers if d["team_id"] is None and not d.get("legend"))
            s1 = w.sign_free_agent(None, fa1["id"])
            self.assertTrue(s1["ok"])

            neg = w.execute_contract_negotiation("leclerc", 35.0, 2, release_driver_id=None)
            self.assertTrue(neg["ok"])

            # All 12 constructors now have exactly 2 active drivers (24 total)
            active = [d for d in w.drivers if d.get("team_id") is not None]
            self.assertEqual(len(active), 24)
            for t in w.teams:
                t_drvs = [d for d in active if d["team_id"] == t["id"]]
                self.assertEqual(len(t_drvs), 2, f"Team {t['id']} should have 2 drivers")

            # Qualifying & Race grid support 24 cars (P23/P24 staggered behind P22 + 12th pit box)
            q_res = w.skip_session()
            self.assertTrue(q_res.get("ok", True))
            self.assertIsNotNone(w.quali_session)
            self.assertEqual(len(w.quali_session.cars), 24)
            w._prepare_race_grid()
            self.assertIsNotNone(w.race_session)
            self.assertEqual(len(w.race_session.cars), 24)

            # 2) Start a 2028 12th custom constructor with Toyota icon
            res28 = w.create_custom_season({
                "name": "Toyota Gazoo F1",
                "short": "Toyota",
                "code": "TOY",
                "color": "#ff2255",
                "secondary": "#ffffff",
                "engine": "Ferrari",
                "icon": "toyota",
                "year": 2028,
                "tier": "contender",
            })
            self.assertTrue(res28["ok"])
            self.assertEqual(w.season_year, 2028)
            self.assertEqual(w.player_team_id, "custom")
            self.assertEqual(len(w.teams), 12)
            self.assertEqual(w._teams_by_id()["custom"]["budget_m"], 550.0)
            self.assertEqual(w._teams_by_id()["custom"]["icon"], "toyota")

    def test_driver_coordination_and_teamwork(self):
        with tempfile.TemporaryDirectory() as td:
            w = self._new_world(td)
            p_drvs = [d["id"] for d in w.drivers if d.get("team_id") == w.player_team_id]
            d1, d2 = p_drvs[0], p_drvs[1]

            # 1) Practice Telemetry Sharing boosts teammate setup confidence & chemistry
            w.driver_setup_confidence[d1] = 75.0
            w.driver_setup_confidence[d2] = 55.0
            w.weekend_setup_target[d1] = int(w.driver_setups.get(d1, 0))
            chem_before = w.team_chemistry[w.player_team_id]
            fp = w.run_practice_program(d1, "QUALI_SIM")
            self.assertTrue(fp["ok"])
            self.assertGreater(w.driver_setup_confidence[d2], 55.0)
            self.assertGreater(w.team_chemistry[w.player_team_id], chem_before)

            # 2) Paired Pit Wall Tactics & Swap Compliance Dilemma
            w._prepare_race_grid()
            w.phase = "RACE"
            rs = w.race_session
            assert rs is not None
            rs.lights_out = True
            rs.flag_state = "GREEN"
            c1 = rs.cars_by_id[d1]
            c2 = rs.cars_by_id[d2]
            c1.pos, c2.pos = 1, 2
            c1.total_dist, c2.total_dist = 1500.0, 1465.0

            esc = w.pit_wall_command(d1, {"team_tactic": "DRS_ESCORT"})
            self.assertTrue(esc["ok"])
            self.assertEqual(rs.team_tactics[w.player_team_id], "DRS_ESCORT")
            self.assertEqual(c2.team_order, "HOLD")

            sp = w.pit_wall_command(d1, {"team_tactic": "SPLIT_STRATEGY"})
            self.assertTrue(sp["ok"])
            self.assertEqual(c1.pace_mode, "PUSH")
            self.assertEqual(c2.pace_mode, "CONSERVE")

            # Low-morale podium leader triggers TEAM_ORDER_PUSHBACK dilemma on SWAP
            c1.morale = 50
            sw = w.pit_wall_command(d1, {"team_tactic": "SWAP"})
            self.assertTrue(sw.get("pushback"))
            self.assertIsNotNone(rs.active_dilemma)
            self.assertEqual(rs.active_dilemma["kind"], "TEAM_ORDER_PUSHBACK")

            # Insist (Option A) forces YIELD & applies -8 chemistry delta
            res_dil = w.resolve_dilemma("A")
            self.assertTrue(res_dil["ok"])
            self.assertEqual(c1.team_order, "YIELD")
            self.assertEqual(rs.chemistry_deltas[w.player_team_id], -8)

            # Yield completion auto-clears SWAP back to FREE and awards +2 chemistry
            c2.total_dist = c1.total_dist + 5.0
            rs._complete_team_yield(c1, c2, w._push_event)
            self.assertEqual(c1.team_order, "FREE")
            self.assertEqual(rs.team_tactics[w.player_team_id], "FREE")
            self.assertEqual(rs.chemistry_deltas[w.player_team_id], -6)

            # Live tick exposes teamwork telemetry fields
            tick = w.build_live_tick_payload()
            self.assertEqual(tick["team_tactic"], "FREE")
            self.assertIsInstance(tick["team_chemistry"], int)
            self.assertIsNotNone(tick["teammate_gap_s"])

    def test_lapped_cars_cannot_steal_p2_p3_behind_leader(self):
        brk = TRACK_BY_ID["brazil"]
        teams, drivers = clone_initial_roster()
        tmap = {t["id"]: t for t in teams}
        active = [d for d in drivers if d.get("team_id")]
        rs = RaceSession(brk, tmap, active, 0.0, 0.0, "williams")
        rs.total_laps = 5
        rs.lights_out = True
        rs.flag_state = "GREEN"
        rs.race_clock = 400.0
        L = brk.length_m

        c_p1, c_p2, c_p3, c_l1, c_l2 = rs.standings[:5]
        # P1 finishes all 5 laps
        c_p1.laps_completed = 5
        c_p1.total_dist = 5.02 * L  # includes cooldown distance
        c_p1.s = 0.02 * L
        c_p1.finished = True
        c_p1.finish_prog = 5.0
        c_p1.finish_time = 400.0

        # P2 and P3 are on the lead lap, still approaching finish line (4.85 and 4.70 laps)
        c_p2.laps_completed = 4
        c_p2.total_dist = 4.85 * L
        c_p2.s = 0.85 * L
        c_p3.laps_completed = 4
        c_p3.total_dist = 4.70 * L
        c_p3.s = 0.70 * L

        # L1 and L2 were 1 lap down and crossed start/finish right after P1!
        # Give L1/L2 larger total_dist from cooldown to ensure cooldown doesn't inflate order
        for idx_l, cl in enumerate((c_l1, c_l2)):
            cl.laps_completed = 4
            cl.total_dist = (4.05 + idx_l * 0.01) * L
            cl.s = (0.05 + idx_l * 0.01) * L
            cl.finished = True
            cl.finish_prog = 4.0
            cl.finish_time = 400.4 + idx_l * 0.5

        # Push remaining cars behind so top 5 order is deterministic
        for k, c in enumerate(rs.standings[5:]):
            c.laps_completed = 3
            c.total_dist = (3.5 - k * 0.05) * L
            c.s = (0.5 - (k * 0.05) % 0.5) * L

        rs._update_standings(0.1, lambda *a, **kw: None)
        top5 = [c.driver_id for c in rs.standings[:5]]
        self.assertEqual(top5, [c_p1.driver_id, c_p2.driver_id, c_p3.driver_id, c_l1.driver_id, c_l2.driver_id])
        self.assertGreater(c_l1.gap_to_leader, 50.0)

        # Also check lead-lap finisher P2 crossing slightly later beats lapped finishers
        c_p2.laps_completed = 5
        c_p2.total_dist = 5.01 * L
        c_p2.finished = True
        c_p2.finish_prog = 5.0
        c_p2.finish_time = 412.0
        rs._update_standings(0.1, lambda *a, **kw: None)
        self.assertEqual([c.driver_id for c in rs.standings[:5]], [c_p1.driver_id, c_p2.driver_id, c_p3.driver_id, c_l1.driver_id, c_l2.driver_id])
        self.assertAlmostEqual(c_p2.gap_to_leader, 12.0, places=2)

    def test_custom_team_survives_custom_scenario_and_state_payload(self):
        with tempfile.TemporaryDirectory() as td:
            w = self._new_world(td)
            res = w.create_custom_season({
                "name": "YangWang",
                "short": "YangWang",
                "code": "YWG",
                "color": "#10b981",
                "secondary": "#34d399",
                "engine": "Honda RBPT",
                "icon": "shield",
                "year": 2026,
                "tier": "midfield",
            })
            self.assertTrue(res["ok"])
            self.assertEqual(w.player_team_id, "custom")

            fa1 = next(d for d in w.drivers if d["team_id"] is None and not d.get("legend"))
            self.assertTrue(w.sign_free_agent(None, fa1["id"])["ok"])
            self.assertTrue(w.execute_contract_negotiation("leclerc", 35.0, 2, release_driver_id=None)["ok"])

            # Custom scenario should keep 'custom' alive without KeyError on state/tick payloads
            cs = w.start_custom_scenario({"track_id": "brazil", "lap": 5, "weather": "DRY", "position": 3})
            self.assertTrue(cs["ok"])
            state_cs = w.build_full_state_payload()
            tick_cs = w.build_live_tick_payload()
            self.assertEqual(state_cs["player_team_id"], "custom")
            self.assertEqual(tick_cs["player_team_id"], "custom")
            for tid in {t["id"] for t in w.teams}:
                self.assertEqual(sum(1 for d in w.drivers if d.get("team_id") == tid), 2)

            # Prebuilt scenario must fall back cleanly without KeyError and restore 'custom' on exit
            ps = w.start_scenario("interlagos_storm")
            self.assertTrue(ps["ok"])
            state_ps = w.build_full_state_payload()
            self.assertIn(state_ps["player_team_id"], {t["id"] for t in w.teams})
            w.exit_scenario()
            self.assertEqual(w.player_team_id, "custom")

    def test_sao_paulo_pit_lane_exit_accelerates_and_avoids_excessive_loss(self):
        from sim.pitwall import RivalPitWall
        from sim.physics import QualifyingSession

        brk = TRACK_BY_ID["brazil"]
        teams, drivers = clone_initial_roster()
        tmap = {t["id"]: t for t in teams}
        active = [d for d in drivers if d.get("team_id")]

        rs = RaceSession(brk, tmap, active, 0.0, 0.0, "williams")
        pw = RivalPitWall(rs)
        rs.lights_out = True
        rs.flag_state = "GREEN"
        c = rs.cars[0]
        for _ in range(300):
            rs.step(0.05, lambda *_: None)
        t_enter = None
        for _ in range(2500):
            if t_enter is None:
                c.box_this_lap = True
                c.next_compound = "HARD"
            rs.step(0.05, lambda *_: None)
            if c.in_pits and t_enter is None:
                t_enter = rs.race_clock
            elif t_enter is not None and not c.in_pits:
                transit = rs.race_clock - t_enter
                net_loss = transit - pw.mainline_pit_s
                self.assertLess(transit, 41.0, f"brazil pit transit {transit:.1f}s too slow")
                self.assertLess(net_loss, 23.0, f"brazil pit net loss {net_loss:.1f}s too high")
                self.assertGreater(c.v, 50.0, f"brazil pit exit speed {c.v*3.6:.1f} kph too slow")
                break
        else:
            self.fail("Brazil pit stop did not complete")

        # Qualifying outlap must also accelerate past the Turn 1 exit speed-limit line
        qs = QualifyingSession(brk, tmap, active, 0.0, False, player_team_id="williams")
        q0 = qs.cars[0]
        q0.quali_release_requested = True
        v_ex_quali = 0.0
        for _ in range(2000):
            was = q0.in_pits
            qs.step(0.05, lambda *_: None)
            if was and not q0.in_pits:
                v_ex_quali = q0.v
                break
        self.assertGreater(v_ex_quali, 50.0)


if __name__ == "__main__":
    unittest.main()
