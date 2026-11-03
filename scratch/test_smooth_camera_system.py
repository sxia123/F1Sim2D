import sys, os
sys.path.insert(0, os.path.abspath("."))
import time
from sim.championship import ChampionshipWorld

def test_sim_time_in_tick_payload():
    print("Testing sim_time in live tick payload...")
    world = ChampionshipWorld()
    payload = world.build_live_tick_payload()
    assert "sim_time" in payload, "sim_time missing from live tick payload"
    assert isinstance(payload["sim_time"], float), f"sim_time is not float: {type(payload['sim_time'])}"
    assert payload["sim_time"] > 0, f"sim_time <= 0: {payload['sim_time']}"
    print(f"sim_time verified: {payload['sim_time']}")

if __name__ == "__main__":
    test_sim_time_in_tick_payload()

