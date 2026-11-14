"""Opening balance, real-world pay, seasonal cash flow, and saved-career migration."""
import copy
import json
import random
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from sim.championship import ChampionshipWorld
from sim.data import INITIAL_TEAMS, INITIAL_DRIVERS, SPONSORS, team_car_rating
from sim.economy import (BALANCE_VERSION, LEGACY_TEAMS, LEGACY_SALARIES,
                         migrate_legacy_balance, team_finances, season_allocation_m)
from sim.tracks import get_season_tracks


class EconomyTests(unittest.TestCase):
    def setUp(self):
        state = random.getstate()
        self.addCleanup(random.setstate, state)
        random.seed(42)
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path = Path(tmp.name) / "career.json"
        # Isolate economic behavior from random weekend development and weather.
        with patch.object(ChampionshipWorld, "_begin_weekend"):
            self.world = ChampionshipWorld(self.path)

    def test_opening_field_has_close_ratings_and_distinct_strengths(self):
        ratings = [team_car_rating(t) for t in INITIAL_TEAMS]
        self.assertLessEqual(max(ratings) - min(ratings), 7.0)
        self.assertEqual(ratings, sorted(ratings, reverse=True))
        self.assertEqual(sum(t["budget_m"] for t in INITIAL_TEAMS) / len(INITIAL_TEAMS), 400.0)
        self.assertGreater(len({tuple(t["upgrades"].values()) for t in INITIAL_TEAMS}), 8)
        for _ in range(10):
            self.world._init_fresh_career(start_year=2028)
            ratings = [team_car_rating(t) for t in self.world.teams]
            self.assertLessEqual(max(ratings) - min(ratings), 9.0)
            self.assertTrue(all(5 <= lvl <= 7 for t in self.world.teams for lvl in t["upgrades"].values()))

    def test_reported_salary_range_and_full_calendar_payroll(self):
        drivers = {d["id"]: d for d in INITIAL_DRIVERS}
        self.assertEqual(drivers["verstappen"]["salary_m"], 70.0)
        self.assertEqual(drivers["hamilton"]["salary_m"], 60.0)
        self.assertEqual(drivers["lindblad"]["salary_m"], 0.75)
        for year in range(2026, 2031):
            races = len(get_season_tracks(year))
            for team in INITIAL_TEAMS:
                info = team_finances(team, INITIAL_DRIVERS, races)
                self.assertAlmostEqual(info["payroll_per_race_m"] * races, info["annual_payroll_m"])
                self.assertAlmostEqual(info["operations_per_race_m"] * races, team["annual_budget_m"] * 0.6)
        team = INITIAL_TEAMS[0]
        before = team_finances(team, INITIAL_DRIVERS, 23)
        swapped = copy.deepcopy(INITIAL_DRIVERS)
        next(d for d in swapped if d["id"] == "verstappen")["team_id"] = team["id"]
        after = team_finances(team, swapped, 23)
        self.assertAlmostEqual(after["annual_payroll_m"] - before["annual_payroll_m"], 70.0)

    def test_annual_funding_counts_guaranteed_income_once_and_carries_cash(self):
        for team in INITIAL_TEAMS:
            sponsor = next(s for s in SPONSORS if s["id"] == team["sponsor_id"])
            for races in (23, 24, 25):
                prize = 50.0
                allocation = season_allocation_m(team, races, prize)
                self.assertAlmostEqual(allocation + sponsor["base_per_race_m"] * races + prize, team["annual_budget_m"])
        player = self.world._teams_by_id()[self.world.player_team_id]
        player["budget_m"] = 123.45
        before_year = self.world.season_year
        before_prize = next(i for i, t in enumerate(self.world.get_wcc_table()) if t["id"] == player["id"])
        from sim.data import WCC_PRIZE_POOL_M
        prize = WCC_PRIZE_POOL_M[before_prize] * 0.42
        expected = 123.45 + season_allocation_m(player, len(get_season_tracks(before_year + 1)), prize)
        with patch.object(self.world, "_adjust_driver_scores_from_performance"), \
             patch.object(self.world, "_run_ai_offseason_development"), \
             patch.object(self.world, "_begin_weekend"):
            self.world._start_next_season()
        self.assertAlmostEqual(player["budget_m"], expected)

    def test_migration_preserves_development_cash_spent_and_custom_contracts(self):
        teams, drivers = copy.deepcopy(INITIAL_TEAMS), copy.deepcopy(INITIAL_DRIVERS)
        for team in teams:
            cash, levels = LEGACY_TEAMS[team["id"]]
            team["budget_m"] = cash - 20.0
            team["upgrades"] = dict(zip(team["upgrades"], levels))
            team["upgrades"]["chassis"] += 1
        for driver in drivers:
            if driver["id"] in LEGACY_SALARIES:
                driver["salary_m"] = LEGACY_SALARIES[driver["id"]]
        next(d for d in drivers if d["id"] == "russell")["salary_m"] = 42.0
        migrate_legacy_balance(teams, drivers, 2026, True)
        for team, base in zip(teams, INITIAL_TEAMS):
            self.assertEqual(team["budget_m"], base["budget_m"] - 20.0)
            self.assertEqual(team["upgrades"]["chassis"], base["upgrades"]["chassis"] + 1)
        self.assertEqual(next(d for d in drivers if d["id"] == "russell")["salary_m"], 42.0)
        self.assertEqual(next(d for d in drivers if d["id"] == "verstappen")["salary_m"], 70.0)

    def test_race_settlement_charges_actual_payroll_and_running_costs(self):
        player = self.world._teams_by_id()[self.world.player_team_id]
        before = player["budget_m"]
        self.world._prepare_race_grid()
        info = self.world._team_finances(player)
        self.world._conclude_race()
        salary = next(row for row in self.world.ledger if row["category"] == "SALARY")
        operations = next(row for row in self.world.ledger if row["category"] == "OPERATIONS")
        self.assertAlmostEqual(salary["amount_m"], -info["annual_payroll_m"] / len(self.world.calendar), places=2)
        self.assertAlmostEqual(operations["amount_m"], -info["annual_operations_m"] / len(self.world.calendar), places=2)
        delta = sum(row["amount_m"] for row in self.world.ledger if row["category"] != "CAREER")
        self.assertAlmostEqual(player["budget_m"] - before, delta, places=2)

    def test_launch_weekend_does_not_buy_upgrades_before_racing(self):
        before = copy.deepcopy(self.world.teams)
        self.world._begin_weekend()
        self.assertEqual(self.world.teams, before)

    def test_strong_season_does_not_cut_elite_salary_to_old_game_cap(self):
        wdc = self.world.get_wdc_table()
        champion = next(row for row in wdc if row["id"] == "verstappen")
        wdc.remove(champion)
        wdc.insert(0, champion)
        champion.update(rank=1, points=500, wins=12, podiums=20)
        self.world._adjust_driver_scores_from_performance(wdc, self.world.get_wcc_table())
        ver = self.world._drivers_by_id()["verstappen"]
        self.assertGreaterEqual(ver["salary_m"], 70.0)

    def test_saved_migration_is_applied_only_once_and_backs_up_original(self):
        self.world._save_state()
        original = json.loads(self.path.read_text())
        original.pop("balance_version")
        for team in original["teams"]:
            cash, levels = LEGACY_TEAMS[team["id"]]
            team["budget_m"] = cash - 10
            team["upgrades"] = dict(zip(team["upgrades"], levels))
        self.path.write_text(json.dumps(original))
        with patch.object(ChampionshipWorld, "_begin_weekend"):
            first = ChampionshipWorld(self.path)
            second = ChampionshipWorld(self.path)
        self.assertEqual(first.balance_version, BALANCE_VERSION)
        self.assertEqual(first.teams, second.teams)
        self.assertEqual(len([r for r in second.ledger if r["desc"] == "Team budget scale adjustment"]), 1)
        backup = self.path.with_name("career.before-balance-v1.json")
        self.assertEqual(json.loads(backup.read_text()), original)

    def test_race_ban_sub_persists_across_reload_and_prefers_non_legend_reserve(self):
        self.world.current_round = 3
        before_lineups = {d["id"]: d.get("team_id") for d in self.world.drivers if d.get("team_id")}
        rus = self.world._drivers_by_id()["russell"]
        rus["penalty_points"] = 12

        self.world._begin_weekend()
        self.assertIsNone(rus["team_id"])
        self.assertEqual(len(self.world.temp_ban_subs), 1)
        reg_id, sub_id, team_id = self.world.temp_ban_subs[0]
        self.assertEqual((reg_id, team_id), ("russell", "mercedes"))
        sub_drv = self.world._drivers_by_id()[sub_id]
        self.assertEqual(sub_drv["team_id"], "mercedes")
        self.assertFalse(sub_drv.get("legend", False))

        # Server restart / reload mid-weekend must preserve the pending ban restoration.
        with patch.object(ChampionshipWorld, "_run_ai_rd_upgrades"):
            resumed = ChampionshipWorld(self.path)
        self.assertEqual(resumed.temp_ban_subs, [("russell", sub_id, "mercedes")])
        self.assertEqual(resumed._drivers_by_id()[sub_id]["team_id"], "mercedes")
        self.assertIsNone(resumed._drivers_by_id()["russell"]["team_id"])

        resumed._prepare_race_grid()
        resumed._conclude_race()
        self.assertEqual(resumed.temp_ban_subs, [])
        self.assertEqual(resumed._drivers_by_id()["russell"]["team_id"], "mercedes")
        self.assertIsNone(resumed._drivers_by_id()[sub_id]["team_id"])
        after_lineups = {d["id"]: d.get("team_id") for d in resumed.drivers if d.get("team_id")}
        self.assertEqual(after_lineups, before_lineups)


if __name__ == "__main__":
    unittest.main()
