import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sim.championship import ChampionshipWorld

world = ChampionshipWorld()
print("Phase:", world.phase)
p_drivers = [d["id"] for d in world.drivers if d["team_id"] == world.player_team_id]
print("Player team:", world.player_team_id, "drivers:", p_drivers)

for drv_id in p_drivers:
    res = world.set_starting_compound(drv_id, "SOFT")
    print(f"set_starting_compound({drv_id}, 'SOFT') -> {res}")

