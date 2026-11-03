import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sim.championship import ChampionshipWorld

def test_team_orders_swap():
    print("[1] Testing Team Orders position swap...")
    world = ChampionshipWorld()
    # Advance to RACE phase
    guard = 0
    while world.phase != "RACE" and guard < 10:
        world.skip_session()
        guard += 1
    assert world.phase == "RACE"
    assert world.race_session is not None

    rs = world.race_session
    # Green light racing condition
    rs.lights_countdown = 0.0
    rs.flag_state = "GREEN"
    rs.race_clock = 15.0

    player_team = world.player_team_id
    team_cars = [c for c in rs.cars if c.team_id == player_team]
    assert len(team_cars) == 2, f"Expected 2 team cars, got {len(team_cars)}"

    car_a, car_b = team_cars[0], team_cars[1]
    print(f"  Team {player_team}: Car A (#{car_a.number} {car_a.code}) and Car B (#{car_b.number} {car_b.code})")

    # Position car_a ahead of car_b by 25 meters on a straight
    car_a.total_dist = 1200.0
    car_a.s = 1200.0 % rs.track.length_m
    car_a.v = 65.0
    car_a.d = 0.0

    car_b.total_dist = 1175.0
    car_b.s = 1175.0 % rs.track.length_m
    car_b.v = 75.0
    car_b.d = -0.4

    rs._update_standings(0.05, world._push_event)
    pos_a_initial = car_a.pos
    pos_b_initial = car_b.pos
    print(f"  Initial positions: #{car_a.code} P{pos_a_initial} (dist={car_a.total_dist:.1f}m), #{car_b.code} P{pos_b_initial} (dist={car_b.total_dist:.1f}m)")
    assert car_a.total_dist > car_b.total_dist

    # Issue team order to SWAP: click SWAP on car_b (the trailing car!)
    res = world.pit_wall_command(car_b.driver_id, {"team_order": "YIELD"})
    assert res["ok"] is True
    print(f"  Issued SWAP command on trailing car #{car_b.code}")

    # Verify that car_a (ahead) was set to YIELD and car_b is FREE to pass
    assert car_a.team_order == "YIELD", f"Expected car_a to have team_order YIELD, got {car_a.team_order}"
    assert car_b.team_order == "FREE"

    # Step physics for up to 6 seconds (120 steps of dt=0.05)
    swapped = False
    for step_i in range(120):
        rs.step(0.05, world._push_event)
        if car_b.total_dist > car_a.total_dist:
            swapped = True
            print(f"  Successfully swapped at step {step_i}! #{car_b.code} (dist={car_b.total_dist:.1f}m) > #{car_a.code} (dist={car_a.total_dist:.1f}m)")
            break

    assert swapped, f"Team cars failed to swap! car_a={car_a.total_dist:.1f}m, car_b={car_b.total_dist:.1f}m"

    # Verify car_a reverted to FREE after completing swap
    assert car_a.team_order == "FREE", f"Expected car_a to revert to FREE after swap, got {car_a.team_order}"

    # Verify radio and team order event was logged
    all_events = [ev for ev in world.event_feed if ev["kind"] in ("RADIO", "TEAM_ORDER")]
    swap_events = [ev for ev in all_events if "swap" in ev["msg"].lower() or "team orders" in ev["msg"].lower()]
    assert len(swap_events) >= 1, "Expected team order announcement in event feed"
    print(f"  Team order events logged: {[ev['msg'] for ev in swap_events]}")

    print("[1] Team Orders position swap passed successfully!\n")

def test_team_orders_swap_when_clicking_ahead_car():
    print("[2] Testing Team Orders position swap when clicking SWAP on ahead car...")
    world = ChampionshipWorld()
    guard = 0
    while world.phase != "RACE" and guard < 10:
        world.skip_session()
        guard += 1
    rs = world.race_session
    rs.lights_countdown = 0.0
    rs.flag_state = "GREEN"
    rs.race_clock = 20.0

    player_team = world.player_team_id
    team_cars = [c for c in rs.cars if c.team_id == player_team]
    car_a, car_b = team_cars[0], team_cars[1]

    # Car B ahead of Car A
    car_b.total_dist = 1600.0
    car_b.s = 1600.0 % rs.track.length_m
    car_b.v = 65.0
    car_b.d = 0.0

    car_a.total_dist = 1578.0
    car_a.s = 1578.0 % rs.track.length_m
    car_a.v = 75.0
    car_a.d = -0.4

    # Issue SWAP on Car B (the ahead car!)
    res = world.pit_wall_command(car_b.driver_id, {"team_order": "YIELD"})
    assert res["ok"] is True
    assert car_b.team_order == "YIELD"
    assert car_a.team_order == "FREE"

    swapped = False
    for step_i in range(120):
        rs.step(0.05, world._push_event)
        if car_a.total_dist > car_b.total_dist:
            swapped = True
            print(f"  Successfully swapped at step {step_i}! #{car_a.code} (dist={car_a.total_dist:.1f}m) > #{car_b.code} (dist={car_b.total_dist:.1f}m)")
            break

    assert swapped, "Car A failed to pass Car B!"
    assert car_b.team_order == "FREE"
    print("[2] Swap when clicking ahead car passed successfully!\n")

def test_team_orders_hold():
    print("[3] Testing Team Orders HOLD...")
    world = ChampionshipWorld()
    guard = 0
    while world.phase != "RACE" and guard < 10:
        world.skip_session()
        guard += 1
    rs = world.race_session
    rs.lights_countdown = 0.0
    rs.flag_state = "GREEN"

    player_team = world.player_team_id
    team_cars = [c for c in rs.cars if c.team_id == player_team]
    car_a, car_b = team_cars[0], team_cars[1]

    # Car A ahead, Car B trailing
    car_a.total_dist = 2000.0
    car_a.s = 2000.0 % rs.track.length_m
    car_a.v = 60.0

    car_b.total_dist = 1990.0
    car_b.s = 1990.0 % rs.track.length_m
    car_b.v = 70.0 # Faster car behind

    # Set Car B to HOLD
    res = world.pit_wall_command(car_b.driver_id, {"team_order": "HOLD"})
    assert res["ok"] is True
    assert car_b.team_order == "HOLD"

    # Step physics: Car B must NOT overtake Car A
    for _ in range(80):
        rs.step(0.05, world._push_event)

    assert car_b.total_dist <= car_a.total_dist, f"Car B passed Car A despite HOLD! B={car_b.total_dist}, A={car_a.total_dist}"
    print(f"  Car B held station behind Car A successfully (A={car_a.total_dist:.1f}m, B={car_b.total_dist:.1f}m).")
    print("[3] HOLD passed successfully!\n")

if __name__ == "__main__":
    test_team_orders_swap()
    test_team_orders_swap_when_clicking_ahead_car()
    test_team_orders_hold()
    print("ALL TEAM ORDER TESTS PASSED CLEANLY!")
