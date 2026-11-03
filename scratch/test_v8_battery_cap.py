import sys
import os
sys.path.insert(0, os.path.abspath("."))
import math
from sim.championship import ChampionshipWorld
from sim.physics import QualifyingSession, RaceSession

def test_v8_battery_cap():
    print("Testing V8 battery capping and charge scaling...")
    world = ChampionshipWorld()
    world.season_year = 2028
    reg = world.regulations
    assert reg["era_id"] == "V8_DRS"
    assert reg["max_battery_mj"] == 2.0, f"Expected 2.0 MJ max battery in V8 era, got {reg['max_battery_mj']}"

    # 1. Test QualifyingSession in V8 era
    world._start_qualifying()
    qs = world.quali_session
    assert qs is not None
    for car in qs.cars:
        assert car.max_battery_mj == 2.0
        assert car.battery_mj <= 2.0, f"Car {car.code} initialized with {car.battery_mj} > 2.0 MJ"

    # Step qualifying for 100 ticks and inspect battery
    for _ in range(100):
        world.step(0.1)
        payload = world.build_live_tick_payload()
        for c in payload.get("cars", []):
            bat = c["bat"]
            assert 0 <= bat <= 100, f"Qualifying tick: car {c['code']} has bat={bat} (>100 or <0)"
        for car in qs.cars:
            assert 0.0 <= car.battery_mj <= car.max_battery_mj, (
                f"Qualifying physics: car {car.code} has battery_mj={car.battery_mj} > max={car.max_battery_mj}"
            )

    print("Qualifying in V8 era passed: all cars strictly <= 100% and <= 2.0 MJ.")

    # 2. Test RaceSession in V8 era
    world.grid_order_ids = [c.driver_id for c in qs.standings]
    world._prepare_race_grid()
    world._start_race()
    rs = world.race_session
    assert rs is not None
    for car in rs.cars:
        assert car.max_battery_mj == 2.0
        assert car.battery_mj <= 2.0

    # Step race for 200 ticks
    for _ in range(200):
        world.step(0.1)
        payload = world.build_live_tick_payload()
        for c in payload.get("cars", []):
            bat = c["bat"]
            assert 0 <= bat <= 100, f"Race tick: car {c['code']} has bat={bat} (>100 or <0)"
        for car in rs.cars:
            assert 0.0 <= car.battery_mj <= car.max_battery_mj + 1e-6, (
                f"Race physics: car {car.code} has battery_mj={car.battery_mj} > max={car.max_battery_mj}"
            )

    print("Race in V8 era passed: all cars strictly <= 100% and <= 2.0 MJ.")

    # 3. Test 2026 Hybrid era as well to verify no regressions
    world_2026 = ChampionshipWorld()
    world_2026.season_year = 2026
    reg_2026 = world_2026.regulations
    assert reg_2026["era_id"] == "2026_HYBRID"
    assert reg_2026["max_battery_mj"] == 4.0

    world_2026._start_qualifying()
    for _ in range(50):
        world_2026.step(0.1)
        payload = world_2026.build_live_tick_payload()
        for c in payload.get("cars", []):
            assert 0 <= c["bat"] <= 100, f"2026 Quali: car {c['code']} has bat={c['bat']}"
        for car in world_2026.quali_session.cars:
            assert 0.0 <= car.battery_mj <= 4.0

    print("2026 Hybrid era passed: all cars strictly <= 100% and <= 4.0 MJ.")
    print("ALL BATTERY CAPPING TESTS PASSED!")

if __name__ == "__main__":
    test_v8_battery_cap()
