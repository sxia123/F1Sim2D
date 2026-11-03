import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import copy
import random
from sim.championship import ChampionshipWorld, get_season_regulations
from sim.data import UPGRADE_DEPARTMENTS, TIRE_COMPOUNDS
from sim.tracks import COMPILED_TRACKS
from sim.physics import RaceSession, QualifyingSession

def test_regulations_eras():
    print("Testing Regulations Eras...")
    reg2026 = get_season_regulations(2026)
    assert reg2026["era_id"] == "2026_HYBRID", f"Expected 2026_HYBRID, got {reg2026['era_id']}"
    assert reg2026["has_active_aero"] is True
    assert reg2026["has_classic_drs"] is False
    assert reg2026["max_battery_mj"] == 4.0
    assert reg2026["ice_power_mult"] == 1.0

    reg2027 = get_season_regulations(2027)
    assert reg2027["era_id"] == "2026_HYBRID"

    reg2028 = get_season_regulations(2028)
    assert reg2028["era_id"] == "V8_DRS", f"Expected V8_DRS, got {reg2028['era_id']}"
    assert reg2028["has_active_aero"] is False
    assert reg2028["has_classic_drs"] is True
    assert reg2028["max_battery_mj"] == 2.0
    assert reg2028["ice_power_mult"] == 1.25
    assert reg2028["drs_boost_kmh"] == 22.0
    assert "2.4L" in reg2028["engine_type"]

    reg2029 = get_season_regulations(2029)
    assert reg2029["era_id"] == "V8_DRS"
    reg2030 = get_season_regulations(2030)
    assert reg2030["era_id"] == "V8_DRS"
    print("✓ Regulations Eras passed successfully!")

def test_transfer_window_restrictions():
    print("Testing Transfer Window Restrictions...")
    world = ChampionshipWorld()
    world.season_year = 2026
    world.current_round = 1
    world.phase = "PRE_WEEKEND"
    assert world.is_transfer_window_open() is True, "Transfer window should be OPEN in Round 1"

    # Trade evaluation should be allowed in Round 1
    p_driver = next(d for d in world.drivers if d["team_id"] == world.player_team_id)
    rival_driver = next(d for d in world.drivers if d["team_id"] and d["team_id"] != world.player_team_id)
    eval_res = world.evaluate_trade(p_driver["id"], rival_driver["id"], 5.0)
    assert eval_res.get("ok") is True, f"Expected ok in Round 1, got {eval_res}"

    # Advance to Round 2
    world.current_round = 2
    world.phase = "PRE_WEEKEND"
    assert world.is_transfer_window_open() is False, "Transfer window should be LOCKED in Round 2"

    eval_locked = world.evaluate_trade(p_driver["id"], rival_driver["id"], 5.0)
    assert eval_locked.get("ok") is False, "Trade evaluation should fail when locked"
    assert "Transfer window is currently LOCKED" in eval_locked.get("error", "")

    exec_locked = world.execute_trade(p_driver["id"], rival_driver["id"], 5.0)
    assert exec_locked.get("ok") is False
    assert "Transfer window is currently LOCKED" in exec_locked.get("error", "")

    fa = next(d for d in world.drivers if d["team_id"] is None)
    sign_locked = world.sign_free_agent(p_driver["id"], fa["id"])
    assert sign_locked.get("ok") is False
    assert "Transfer window is currently LOCKED" in sign_locked.get("error", "")

    # When entering OFF_SEASON
    world.phase = "OFF_SEASON"
    assert world.is_transfer_window_open() is True, "Transfer window should be OPEN during OFF_SEASON"
    print("✓ Transfer Window Restrictions passed successfully!")

def test_starting_tyre_choice():
    print("Testing Starting Tyre Choice...")
    world = ChampionshipWorld()
    world.season_year = 2026
    world.current_round = 1
    p_drivers = [d for d in world.drivers if d["team_id"] == world.player_team_id]
    d1 = p_drivers[0]["id"]
    d2 = p_drivers[1]["id"]

    # Choose starting tyre
    res1 = world.set_starting_compound(d1, "HARD")
    assert res1["ok"] is True
    assert world.starting_compounds[d1] == "HARD"

    res2 = world.set_starting_compound(d2, "SOFT")
    assert res2["ok"] is True
    assert world.starting_compounds[d2] == "SOFT"

    # Prepare grid and check RaceSession
    world.grid_order_ids = [d["id"] for d in world._active_drivers()]
    world._prepare_race_grid()
    assert world.race_session is not None
    car1 = world.race_session.cars_by_id[d1]
    car2 = world.race_session.cars_by_id[d2]
    assert car1.compound == "HARD", f"Car 1 expected HARD, got {car1.compound}"
    assert car2.compound == "SOFT", f"Car 2 expected SOFT, got {car2.compound}"

    # Dynamic swap during GRID_WALK
    world.phase = "GRID_WALK"
    world.race_session.lights_countdown = 5.0
    res3 = world.set_starting_compound(d1, "MEDIUM")
    assert res3["ok"] is True
    assert car1.compound == "MEDIUM", f"Car 1 expected dynamic switch to MEDIUM, got {car1.compound}"
    print("✓ Starting Tyre Choice passed successfully!")

def test_car_improvements_carryover_and_2028_regulations_reset():
    print("Testing Car Improvements Carryover & 2028 New Regulations Reset...")
    world = ChampionshipWorld()

    # 1. Normal transition (2026 -> 2027)
    world.season_year = 2026
    # Give player team upgrades
    p_team = world._teams_by_id()[world.player_team_id]
    p_team["upgrades"]["power_unit"] = 7
    p_team["upgrades"]["active_aero"] = 8
    p_team["upgrades"]["chassis"] = 6
    p_team["upgrades"]["suspension"] = 5

    saved_upgrades = copy.deepcopy(p_team["upgrades"])
    world._start_next_season()
    assert world.season_year == 2027, f"Expected 2027, got {world.season_year}"
    # In normal seasons, upgrades must be 100% kept!
    for dept, lvl in saved_upgrades.items():
        assert p_team["upgrades"][dept] == lvl, f"Expected {dept} level {lvl} kept in 2027, got {p_team['upgrades'][dept]}"

    # 2. Transition entering 2028 (New Regulations: 2.4L V8 NA + DRS)
    world.season_year = 2027
    wcc = world.get_wcc_table()
    top4_ids = [wcc[i]["id"] for i in range(4)]
    midfield_ids = [wcc[i]["id"] for i in range(4, len(wcc))]

    world._start_next_season()
    assert world.season_year == 2028, f"Expected 2028, got {world.season_year}"
    assert world.regulations["era_id"] == "V8_DRS"

    tmap = world._teams_by_id()
    # Verify top 4 teams start off better (levels 5 to 8)
    for idx, tid in enumerate(top4_ids):
        t = tmap[tid]
        min_lvl = min(t["upgrades"].values())
        max_lvl = max(t["upgrades"].values())
        assert min_lvl >= 5, f"Top 4 team {t['short']} (P{idx+1}) expected min level >= 5, got {min_lvl}"
        assert max_lvl <= 8, f"Top 4 team {t['short']} (P{idx+1}) expected max level <= 8, got {max_lvl}"

    # Verify midfield teams (5-11) are randomized (levels 2 to 5)
    for tid in midfield_ids:
        t = tmap[tid]
        min_lvl = min(t["upgrades"].values())
        max_lvl = max(t["upgrades"].values())
        assert min_lvl >= 2, f"Midfield team {t['short']} expected min level >= 2, got {min_lvl}"
        assert max_lvl <= 5, f"Midfield team {t['short']} expected max level <= 5, got {max_lvl}"

    # 3. Transition from 2028 -> 2029 (V8 era continues, upgrades kept 100%)
    saved_2028 = copy.deepcopy(p_team["upgrades"])
    world._start_next_season()
    assert world.season_year == 2029
    assert world.regulations["era_id"] == "V8_DRS"
    for dept, lvl in saved_2028.items():
        assert p_team["upgrades"][dept] == lvl, f"Expected {dept} level {lvl} kept in 2029"

    print("✓ Car Improvements Carryover & 2028 New Regulations Reset passed successfully!")

def test_v8_and_drs_physics():
    print("Testing 2028 V8 & DRS Physics...")
    track = COMPILED_TRACKS[0] # Melbourne
    world = ChampionshipWorld()
    world.season_year = 2028 # V8 era
    reg = world.regulations

    grid_drivers = world._active_drivers()
    rs = RaceSession(
        track,
        world._teams_by_id(),
        grid_drivers,
        wetness=0.0,
        rain_forecast=0.0,
        player_team_id=world.player_team_id,
        is_sprint=False,
        regulations=reg,
    )

    # Battery must be initialized to 2.0 MJ for 120kW KERS
    for c in rs.cars:
        assert c.max_battery_mj == 2.0, f"Expected 2.0 MJ max battery in V8 era, got {c.max_battery_mj}"
        assert c.battery_mj == 2.0

    # Start lights green
    rs.lights_countdown = 0.0
    rs.flag_state = "GREEN"

    # Step simulation
    for _ in range(60):
        rs.step(0.05, lambda k, m: None)

    # Cars in V8 era should have corner aero unless DRS is active
    corner_or_drs = all(c.aero_mode in ("CORNER", "DRS") for c in rs.cars)
    assert corner_or_drs, "In V8 era, cars must use CORNER or DRS aero mode (no 2026 straight-mode)"

    # Verify DRS arming and activation when within 1.0s in DRS zone
    c1 = rs.cars[0]
    c2 = rs.cars[1]
    c1.s = 100.0
    c2.s = 90.0 # 10m behind c1 in DRS zone 1 (activation 0 to 252m)
    c2.lap = 2
    c2.v = 80.0
    c2.drs_eligible = True
    c2.drs_eligible_zone = 1

    rs._step_car(c2, c1, c1, False, 0.05, lambda k, m: None)
    assert c2.drs_active is True, "c2 should have DRS active in DRS zone when eligible"
    assert c2.aero_mode == "DRS", f"c2 aero_mode should be DRS, got {c2.aero_mode}"

    # Outside DRS zone
    c2.s = 600.0 # Past zone 1 end
    rs._step_car(c2, c1, c1, False, 0.05, lambda k, m: None)
    assert c2.drs_active is False, "c2 DRS should snap shut outside DRS zone"
    assert c2.aero_mode == "CORNER"

    print("✓ 2028 V8 & DRS Physics passed successfully!")

if __name__ == "__main__":
    test_regulations_eras()
    test_transfer_window_restrictions()
    test_starting_tyre_choice()
    test_car_improvements_carryover_and_2028_regulations_reset()
    test_v8_and_drs_physics()
    print("\n========================================================")
    print("ALL VERIFICATION TESTS COMPLETED AND PASSED PERFECTLY!")
    print("========================================================")
