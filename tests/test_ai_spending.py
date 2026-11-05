import random
import unittest
from sim.data import INITIAL_TEAMS, UPGRADE_DEPARTMENTS, upgrade_cost_m, team_car_rating
from sim.championship import ChampionshipWorld


class TestAISpending(unittest.TestCase):
    def setUp(self):
        state = random.getstate()
        self.addCleanup(random.setstate, state)
        random.seed(42)
        self.world = ChampionshipWorld()

    def test_ai_teams_spend_surplus_budget(self):
        """AI rival teams with surplus budget invest in R&D upgrades."""
        # Find an AI team and give it substantial surplus budget
        ai_team = next(t for t in self.world.teams if t["id"] != self.world.player_team_id)
        ai_team["budget_m"] = 150.0
        # Set a few departments low so upgrades are available
        for dept in UPGRADE_DEPARTMENTS:
            ai_team["upgrades"][dept] = 3

        prev_budget = ai_team["budget_m"]
        prev_rating = team_car_rating(ai_team)

        # Trigger AI R&D upgrades
        self.world._run_ai_rd_upgrades()

        self.assertLess(ai_team["budget_m"], prev_budget, "AI team with $150M surplus must spend money")
        self.assertGreater(team_car_rating(ai_team), prev_rating, "Upgrades must improve team car rating")

    def test_player_team_budget_and_upgrades_untouched(self):
        """Player team budget and upgrades must never be modified by AI spending routines."""
        p_team = self.world._teams_by_id()[self.world.player_team_id]
        p_team["budget_m"] = 180.0
        orig_upgrades = dict(p_team["upgrades"])

        self.world._run_ai_rd_upgrades()
        self.world._run_ai_offseason_development()

        self.assertEqual(p_team["budget_m"], 180.0, "Player team budget must remain untouched")
        self.assertEqual(p_team["upgrades"], orig_upgrades, "Player team upgrades must remain untouched")

    def test_operating_reserve_respected(self):
        """AI teams must never spend into or below their operating reserve ($22.0M)."""
        ai_team = next(t for t in self.world.teams if t["id"] != self.world.player_team_id)
        # Give team a budget right around the operating reserve
        ai_team["budget_m"] = 23.0
        ai_team["upgrades"]["pit_crew"] = 1  # Lv 1 pit crew costs ~$4.8M which would breach the 22M reserve

        self.world._run_ai_rd_upgrades()

        self.assertGreaterEqual(ai_team["budget_m"], 22.0, "Budget must not drop below operating reserve")

    def test_winter_offseason_development(self):
        """Off-season winter development invests surplus funds into pre-season car upgrades."""
        ai_team = next(t for t in self.world.teams if t["id"] != self.world.player_team_id)
        ai_team["budget_m"] = 90.0
        for dept in UPGRADE_DEPARTMENTS:
            ai_team["upgrades"][dept] = 4

        prev_budget = ai_team["budget_m"]
        prev_rating = team_car_rating(ai_team)

        self.world._run_ai_offseason_development()

        self.assertLess(ai_team["budget_m"], prev_budget, "Winter R&D must deduct budget")
        self.assertGreater(team_car_rating(ai_team), prev_rating, "Winter R&D must boost car rating")
        self.assertGreaterEqual(ai_team["budget_m"], 25.0, "Winter R&D must respect operating reserve")


if __name__ == "__main__":
    unittest.main()

