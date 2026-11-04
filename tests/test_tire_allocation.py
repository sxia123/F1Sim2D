import unittest
import copy
from sim.data import DEFAULT_WEEKEND_TIRE_SETS, clone_initial_roster
from sim.tracks import COMPILED_TRACKS
from sim.physics import QualifyingSession, RaceSession, CarState
from sim.championship import ChampionshipWorld


class TestTireAllocation(unittest.TestCase):
    def setUp(self):
        self.track = COMPILED_TRACKS[0]
        self.teams, self.drivers = clone_initial_roster()
        self.teams_by_id = {t["id"]: t for t in self.teams}
        self.active_drivers = [d for d in self.drivers if d["team_id"] is not None]

    def test_default_weekend_allocation_counts(self):
        """Authentic FIA 20-set allocation: 8 Soft, 3 Medium, 2 Hard, 4 Inter, 3 Wet."""
        self.assertEqual(DEFAULT_WEEKEND_TIRE_SETS["SOFT"], 8)
        self.assertEqual(DEFAULT_WEEKEND_TIRE_SETS["MEDIUM"], 3)
        self.assertEqual(DEFAULT_WEEKEND_TIRE_SETS["HARD"], 2)
        self.assertEqual(DEFAULT_WEEKEND_TIRE_SETS["INTER"], 4)
        self.assertEqual(DEFAULT_WEEKEND_TIRE_SETS["WET"], 3)
        self.assertEqual(sum(DEFAULT_WEEKEND_TIRE_SETS.values()), 20)

    def test_qualifying_deducts_tire_sets(self):
        """Qualifying Q1 start burns 1 set of tires per driver."""
        allocations = {d["id"]: dict(DEFAULT_WEEKEND_TIRE_SETS) for d in self.active_drivers}
        first_driver_id = self.active_drivers[0]["id"]
        initial_softs = allocations[first_driver_id]["SOFT"]

        qs = QualifyingSession(
            track=self.track,
            teams_by_id=self.teams_by_id,
            active_drivers=self.active_drivers,
            wetness=0.0,
            is_sprint_quali=False,
            tire_allocations=allocations,
        )

        # In dry Q1, all drivers head out on Soft tyres, deducting 1 Soft set
        self.assertEqual(allocations[first_driver_id]["SOFT"], initial_softs - 1)
        self.assertIs(qs.tire_allocations, allocations)

    def test_qualifying_stage_advancement_deducts_sets(self):
        """Advancing from Q1 to Q2 burns an additional set for advancing drivers."""
        allocations = {d["id"]: dict(DEFAULT_WEEKEND_TIRE_SETS) for d in self.active_drivers}
        qs = QualifyingSession(
            track=self.track,
            teams_by_id=self.teams_by_id,
            active_drivers=self.active_drivers,
            wetness=0.0,
            is_sprint_quali=False,
            tire_allocations=allocations,
        )

        events = []
        # Advance Q1 to completion
        qs.advance_stage(lambda kind, msg: events.append((kind, msg)))
        self.assertEqual(qs.stage_idx, 1)  # Now in Q2

        # Top 16 cars advanced and consumed another Soft set (total 2 used, 6 left)
        advancing_ids = [c.driver_id for c in qs.standings if not c.eliminated]
        self.assertEqual(len(advancing_ids), 16)
        for drv_id in advancing_ids:
            self.assertEqual(allocations[drv_id]["SOFT"], DEFAULT_WEEKEND_TIRE_SETS["SOFT"] - 2)

        # Eliminated cars in Q1 did not consume a second set (kept 7 Softs)
        eliminated_ids = [c.driver_id for c in qs.standings if c.eliminated]
        self.assertEqual(len(eliminated_ids), 6)
        for drv_id in eliminated_ids:
            self.assertEqual(allocations[drv_id]["SOFT"], DEFAULT_WEEKEND_TIRE_SETS["SOFT"] - 1)

    def test_race_session_starting_grid_deducts_allocation(self):
        """Race start deducts 1 set of the starting compound from the driver's allocation."""
        allocations = {d["id"]: dict(DEFAULT_WEEKEND_TIRE_SETS) for d in self.active_drivers}
        p_drv = self.active_drivers[0]["id"]
        start_comps = {p_drv: "SOFT"}

        rs = RaceSession(
            track=self.track,
            teams_by_id=self.teams_by_id,
            grid_drivers=self.active_drivers,
            wetness=0.0,
            rain_forecast=0.0,
            player_team_id=self.active_drivers[0]["team_id"],
            starting_compounds=start_comps,
            tire_allocations=allocations,
        )

        car = rs.cars_by_id[p_drv]
        self.assertEqual(car.compound, "SOFT")
        self.assertEqual(allocations[p_drv]["SOFT"], DEFAULT_WEEKEND_TIRE_SETS["SOFT"] - 1)

    def test_race_session_set_starting_compound_refund_and_limit(self):
        """Switching starting compound refunds previous compound and deducts new one; fails if 0 sets left."""
        allocations = {d["id"]: dict(DEFAULT_WEEKEND_TIRE_SETS) for d in self.active_drivers}
        p_drv = self.active_drivers[0]["id"]
        allocations[p_drv]["HARD"] = 0  # Artificially deplete Hard sets

        rs = RaceSession(
            track=self.track,
            teams_by_id=self.teams_by_id,
            grid_drivers=self.active_drivers,
            wetness=0.0,
            rain_forecast=0.0,
            player_team_id=self.active_drivers[0]["team_id"],
            starting_compounds={p_drv: "MEDIUM"},
            tire_allocations=allocations,
        )

        # Medium was deducted at init: 3 - 1 = 2 left
        self.assertEqual(allocations[p_drv]["MEDIUM"], 2)

        # Cannot switch to HARD because 0 sets remain
        ok_hard = rs.set_starting_compound(p_drv, "HARD")
        self.assertFalse(ok_hard)
        self.assertEqual(rs.cars_by_id[p_drv].compound, "MEDIUM")
        self.assertEqual(allocations[p_drv]["MEDIUM"], 2)

        # Can switch to SOFT: refunds 1 Medium (back to 3) and deducts 1 Soft (8 -> 7)
        ok_soft = rs.set_starting_compound(p_drv, "SOFT")
        self.assertTrue(ok_soft)
        self.assertEqual(rs.cars_by_id[p_drv].compound, "SOFT")
        self.assertEqual(allocations[p_drv]["MEDIUM"], 3)
        self.assertEqual(allocations[p_drv]["SOFT"], 7)

    def test_race_session_cannot_change_starting_compound_after_start(self):
        """Once race starts (lights out / crossed line), set_starting_compound returns False."""
        allocations = {d["id"]: dict(DEFAULT_WEEKEND_TIRE_SETS) for d in self.active_drivers}
        p_drv = self.active_drivers[0]["id"]

        rs = RaceSession(
            track=self.track,
            teams_by_id=self.teams_by_id,
            grid_drivers=self.active_drivers,
            wetness=0.0,
            rain_forecast=0.0,
            player_team_id=self.active_drivers[0]["team_id"],
            tire_allocations=allocations,
        )

        rs.lights_out = True
        ok = rs.set_starting_compound(p_drv, "HARD")
        self.assertFalse(ok)

    def test_best_compound_skips_depleted_compounds(self):
        """_best_compound_for_conditions never picks a compound with 0 sets remaining."""
        allocations = {d["id"]: dict(DEFAULT_WEEKEND_TIRE_SETS) for d in self.active_drivers}
        p_drv = self.active_drivers[0]["id"]
        # Deplete Soft and Medium
        allocations[p_drv]["SOFT"] = 0
        allocations[p_drv]["MEDIUM"] = 0

        rs = RaceSession(
            track=self.track,
            teams_by_id=self.teams_by_id,
            grid_drivers=self.active_drivers,
            wetness=0.0,
            rain_forecast=0.0,
            player_team_id=self.active_drivers[0]["team_id"],
            tire_allocations=allocations,
        )

        car = rs.cars_by_id[p_drv]
        # Even with 4 laps left (normally preferring Soft), must pick Hard since Soft/Medium are 0
        best_comp = rs._best_compound_for_conditions(car, laps_left=4)
        self.assertEqual(best_comp, "HARD")

    def test_pit_stop_deducts_allocation_and_falls_back_when_depleted(self):
        """Pit stop deducts 1 set of next_compound, or falls back to available compound if 0 left."""
        allocations = {d["id"]: dict(DEFAULT_WEEKEND_TIRE_SETS) for d in self.active_drivers}
        p_drv = self.active_drivers[0]["id"]
        # Only 1 Medium set available, 0 Softs
        allocations[p_drv]["SOFT"] = 0
        allocations[p_drv]["MEDIUM"] = 1
        allocations[p_drv]["HARD"] = 2

        rs = RaceSession(
            track=self.track,
            teams_by_id=self.teams_by_id,
            grid_drivers=self.active_drivers,
            wetness=0.0,
            rain_forecast=0.0,
            player_team_id=self.active_drivers[0]["team_id"],
            starting_compounds={p_drv: "MEDIUM"},
            tire_allocations=allocations,
        )

        # Starting on Medium uses the last Medium: 1 - 1 = 0 left
        self.assertEqual(allocations[p_drv]["MEDIUM"], 0)

        car = rs.cars_by_id[p_drv]
        # Target compound requested was SOFT (which is 0)
        car.next_compound = "SOFT"
        car.in_pits = True
        car.pit_phase = "STOPPED"
        car.pit_stop_timer = 0.0  # Finished pit work

        events = []
        rs._step_pit_lane(car, leader_finished=False, dt=0.05, event_cb=lambda k, m: events.append((k, m)))

        # Soft was 0, so it must fall back to HARD (2 -> 1 left)
        self.assertEqual(car.compound, "HARD")
        self.assertEqual(allocations[p_drv]["HARD"], 1)
        self.assertTrue(any("out of SOFT tyres" in m for _, m in events))

    def test_championship_coordinator_reset_and_tick(self):
        """Championship weekend resets allocations and live tick exposes remaining tire sets."""
        coord = ChampionshipWorld()
        coord._begin_weekend()

        self.assertIn(coord.player_team_id, [t["id"] for t in coord.teams])
        my_drv = [d["id"] for d in coord.drivers if d["team_id"] == coord.player_team_id][0]
        self.assertIn(my_drv, coord.tire_allocations)
        self.assertEqual(coord.tire_allocations[my_drv]["SOFT"], 8)
        self.assertEqual(coord.tire_allocations[my_drv]["MEDIUM"], 3)

        # Test set_starting_compound validation
        res_fail = coord.set_starting_compound(my_drv, "UNKNOWN_COMP")
        self.assertFalse(res_fail["ok"])

        # Deplete intermediate sets
        coord.tire_allocations[my_drv]["INTER"] = 0
        res_no_inter = coord.set_starting_compound(my_drv, "INTER")
        self.assertFalse(res_no_inter["ok"])
        self.assertIn("No INTER tyre sets", res_no_inter["error"])

        # Valid selection works
        res_ok = coord.set_starting_compound(my_drv, "MEDIUM")
        self.assertTrue(res_ok["ok"])

        # Test live tick includes 'tsets'
        tick = coord.build_live_tick_payload()
        self.assertIn("cars", tick)
        if tick["cars"]:
            car_payload = tick["cars"][0]
            self.assertIn("tsets", car_payload)
            self.assertIn("SOFT", car_payload["tsets"])
            self.assertIn("MEDIUM", car_payload["tsets"])
            self.assertIn("HARD", car_payload["tsets"])

    def test_set_starting_compound_on_positive_progress_track(self):
        """Grid compound changes must succeed on tracks where grid box progress_m > 0 (e.g. Portugal)."""
        portugal_track = next((t for t in COMPILED_TRACKS if t.id == "portugal"), None)
        self.assertIsNotNone(portugal_track)
        self.assertGreater(portugal_track.grid_boxes[0]["progress_m"], 0.0)

        allocations = {d["id"]: dict(DEFAULT_WEEKEND_TIRE_SETS) for d in self.active_drivers}
        p_drv = self.active_drivers[0]["id"]
        rs = RaceSession(
            track=portugal_track,
            teams_by_id=self.teams_by_id,
            grid_drivers=self.active_drivers,
            wetness=0.0,
            rain_forecast=0.0,
            player_team_id=self.active_drivers[0]["team_id"],
            starting_compounds={p_drv: "MEDIUM"},
            tire_allocations=allocations,
        )

        # Car total_dist is positive on Portugal's grid, but lights are NOT out
        self.assertGreater(rs.cars_by_id[p_drv].total_dist, 0.0)
        self.assertFalse(rs.lights_out)
        self.assertEqual(rs.flag_state, "LIGHTS")

        # Switching to SOFT must succeed
        ok = rs.set_starting_compound(p_drv, "SOFT")
        self.assertTrue(ok)
        self.assertEqual(rs.cars_by_id[p_drv].compound, "SOFT")
        self.assertEqual(allocations[p_drv]["MEDIUM"], 3)
        self.assertEqual(allocations[p_drv]["SOFT"], 7)

    def test_championship_pit_wall_ncomp_queue(self):
        """Pit wall command during race queues car.next_compound and respects weekend allocation."""
        coord = ChampionshipWorld()
        coord._init_fresh_career("williams")
        coord._prepare_race_grid()
        coord.phase = "RACE"
        coord.race_session.lights_out = True
        coord.race_session.flag_state = "GREEN"

        my_drv = [d["id"] for d in coord.drivers if d["team_id"] == coord.player_team_id][0]
        car = coord.race_session.cars_by_id[my_drv]

        # Queue HARD
        res = coord.pit_wall_command(my_drv, {"next_compound": "HARD"})
        self.assertTrue(res.get("ok"))
        self.assertEqual(car.next_compound, "HARD")

        # Deplete INTER and attempt to queue INTER
        coord.tire_allocations[my_drv]["INTER"] = 0
        res_fail = coord.pit_wall_command(my_drv, {"next_compound": "INTER"})
        self.assertFalse(res_fail.get("ok"))
        self.assertIn("No INTER tyre sets", res_fail.get("error", ""))
        self.assertEqual(car.next_compound, "HARD")


if __name__ == "__main__":
    unittest.main()
