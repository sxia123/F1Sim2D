"""Shared Grand Prix development allowance, pricing, and persistence."""
import copy
import random
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from sim.championship import ChampionshipWorld
from sim.data import UPGRADE_DEPARTMENTS, upgrade_cost_m


class UpgradeLimitTests(unittest.TestCase):
    def setUp(self):
        state = random.getstate()
        self.addCleanup(random.setstate, state)
        random.seed(42)
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.path = Path(temp.name) / "career.json"
        with patch.object(ChampionshipWorld, "_begin_weekend"):
            self.world = ChampionshipWorld(self.path)
        for team in self.world.teams:
            team["budget_m"] = 5000.0
            team["upgrades"] = dict.fromkeys(UPGRADE_DEPARTMENTS, 1)

    def test_player_can_buy_three_levels_and_fourth_does_not_charge(self):
        world = self.world
        player = world._teams_by_id()[world.player_team_id]
        # Three consecutive levels in one department each use a delivery slot.
        for remaining in (2, 1, 0):
            result = world.buy_upgrade("chassis")
            self.assertTrue(result["ok"])
            self.assertEqual(result["upgrade_allowance"]["remaining"], remaining)
        before = copy.deepcopy(player)
        rejected = world.buy_upgrade("active_aero")
        self.assertFalse(rejected["ok"])
        self.assertIn("limit reached (3/3)", rejected["error"])
        self.assertEqual(player, before)
        self.assertEqual(world.build_full_state_payload()["upgrade_allowance"]["used"], 3)

    def test_concurrent_requests_cannot_exceed_three(self):
        with ThreadPoolExecutor(max_workers=6) as pool:
            results = list(pool.map(self.world.buy_upgrade, UPGRADE_DEPARTMENTS))
        self.assertEqual(sum(result["ok"] for result in results), 3)

    def test_failed_purchases_do_not_use_allowance(self):
        world = self.world
        player = world._teams_by_id()[world.player_team_id]
        self.assertFalse(world.buy_upgrade("invalid")["ok"])
        player["upgrades"]["chassis"] = 10
        self.assertFalse(world.buy_upgrade("chassis")["ok"])
        player["budget_m"] = 0
        self.assertFalse(world.buy_upgrade("power_unit")["ok"])
        self.assertEqual(world._upgrade_allowance(player["id"])["used"], 0)

    def test_team_switch_and_session_changes_do_not_reset_allowance(self):
        world = self.world
        original_id = world.player_team_id
        other_id = next(t["id"] for t in world.teams if t["id"] != original_id)
        for _ in range(3):
            self.assertTrue(world.buy_upgrade("chassis")["ok"])
        world.select_team(other_id)
        self.assertTrue(world.buy_upgrade("chassis")["ok"])
        world.select_team(original_id)
        for phase in ("SPRINT_QUALIFYING", "SPRINT_RACE", "QUALIFYING", "GRID_WALK", "RACE", "PODIUM"):
            world.phase = phase
            self.assertFalse(world.buy_upgrade("chassis")["ok"], phase)
        world.current_round += 1
        self.assertTrue(world.buy_upgrade("chassis")["ok"])
        world.season_year += 1
        self.assertEqual(world._upgrade_allowance(original_id)["remaining"], 3)

    def test_restarting_same_weekend_does_not_buy_additional_ai_upgrades(self):
        world = self.world
        world.current_round = 2
        for _ in range(3):
            self.assertTrue(world.buy_upgrade("chassis")["ok"])
        with patch("sim.championship.random.random", return_value=0.0):
            world._begin_weekend()
            before = copy.deepcopy(world.teams)
            resumed = ChampionshipWorld(self.path)
        self.assertEqual(resumed.teams, before)
        self.assertFalse(resumed.buy_upgrade("chassis")["ok"])
        self.assertTrue(all(resumed._upgrade_allowance(t["id"])["used"] == 3 for t in resumed.teams))
        resumed.current_round += 1
        self.assertEqual(resumed._upgrade_allowance(resumed.player_team_id)["remaining"], 3)

    def test_ai_winter_and_weekend_development_share_three_slots(self):
        world = self.world
        player_before = copy.deepcopy(world._teams_by_id()[world.player_team_id])
        before = {t["id"]: sum(t["upgrades"].values()) for t in world.teams}
        with patch("sim.championship.random.random", return_value=0.0):
            world._run_ai_offseason_development()
            world._run_ai_offseason_development()
            world._run_ai_rd_upgrades()
            world._run_ai_rd_upgrades()
        for team in world.teams:
            if team["id"] == world.player_team_id:
                self.assertEqual(team, player_before)
            else:
                self.assertEqual(sum(team["upgrades"].values()) - before[team["id"]], 3)
        # Taking over an AI team also retains its winter usage.
        ai_id = next(t["id"] for t in world.teams if t["id"] != world.player_team_id)
        world.select_team(ai_id)
        self.assertFalse(world.buy_upgrade("chassis")["ok"])

    def test_prices_are_ten_percent_higher_and_maxed_departments_cost_zero(self):
        self.assertEqual(upgrade_cost_m("power_unit", 1), 9.35)
        self.assertEqual(upgrade_cost_m("pit_crew", 1), 5.28)
        for dept, spec in UPGRADE_DEPARTMENTS.items():
            for level in range(1, 10):
                previous = spec["base_cost_m"] * spec["cost_scale"] ** (level - 1)
                self.assertAlmostEqual(upgrade_cost_m(dept, level) / previous, 1.1, delta=0.001)
            self.assertEqual(upgrade_cost_m(dept, spec["max_level"]), 0.0)

    def test_winter_rollover_uses_new_seasons_opening_allowance(self):
        world = self.world
        world.current_round = len(world.calendar)
        world._sync_upgrade_allowance()
        world.upgrades_this_round = {team["id"]: 3 for team in world.teams}
        with patch.object(world, "_adjust_driver_scores_from_performance"):
            world._start_next_season()
        self.assertEqual(world.upgrade_round_key, "2027:1")
        for team in world.teams:
            used = world._upgrade_allowance(team["id"])["used"]
            self.assertEqual(used, 0 if team["id"] == world.player_team_id else 3)


if __name__ == "__main__":
    unittest.main()
