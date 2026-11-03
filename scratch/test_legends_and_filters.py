import unittest
import copy
from sim.data import INITIAL_DRIVERS, driver_overall
from sim.championship import ChampionshipWorld

class TestLegendsAndComms(unittest.TestCase):
    def test_legends_present_and_stats(self):
        legends = {d["id"]: d for d in INITIAL_DRIVERS if d.get("legend")}
        self.assertEqual(len(legends), 9, f"Expected 9 legends, got {len(legends)}")
        
        expected_ids = ["senna", "lauda", "vettel", "raikkonen", "schumacher", "fangio", "prost", "hakkinen", "mansell"]
        for eid in expected_ids:
            self.assertIn(eid, legends, f"Legend {eid} missing from INITIAL_DRIVERS")
            d = legends[eid]
            self.assertIsNone(d["team_id"], f"{d['name']} should be a Free Agent (team_id=None)")
            ovr = driver_overall(d)
            self.assertGreaterEqual(ovr, 95.0, f"{d['name']} OVR is {ovr}, must be 95+")

    def test_world_payload_drivers(self):
        world = ChampionshipWorld()
        payload = world.build_full_state_payload()
        drivers = payload["drivers"]
        self.assertEqual(len(drivers), 41, f"Expected 41 drivers in payload, got {len(drivers)}")
        
        d_map = {d["id"]: d for d in drivers}
        for eid in ["senna", "lauda", "vettel", "raikkonen", "schumacher", "fangio", "prost", "hakkinen", "mansell"]:
            self.assertIn(eid, d_map)
            self.assertGreaterEqual(d_map[eid]["overall"], 95.0)
            self.assertTrue(d_map[eid]["legend"])
            self.assertEqual(d_map[eid]["team_short"], "Free Agent")

    def test_sign_legend_free_agent(self):
        world = ChampionshipWorld()
        p_team_id = world.player_team_id
        p_team = world._teams_by_id()[p_team_id]
        p_team["budget_m"] = 150.0  # Ensure sufficient budget
        
        my_drivers = [d for d in world.drivers if d["team_id"] == p_team_id]
        rel_drv = my_drivers[0]
        
        res = world.sign_free_agent(rel_drv["id"], "schumacher")
        self.assertTrue(res["ok"], f"Failed to sign Schumacher: {res}")
        
        schumacher = world._drivers_by_id()["schumacher"]
        self.assertEqual(schumacher["team_id"], p_team_id, "Schumacher should now be on the player team")
        self.assertIsNone(rel_drv["team_id"], "Released driver should now be a free agent")

if __name__ == "__main__":
    unittest.main()
