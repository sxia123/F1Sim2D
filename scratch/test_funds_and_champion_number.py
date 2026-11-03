import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sim.championship import ChampionshipWorld

def test_funds_carryover_and_champion_number():
    print("[1] Testing Funds Carryover and Season Start Injections...")
    world = ChampionshipWorld()
    world.season_year = 2026
    
    # 1. Normal Season Transition (2026 -> 2027: +50M)
    p_team_id = world.player_team_id
    initial_budgets = {t["id"]: t["budget_m"] for t in world.teams}
    
    # Set simulated WDC standings: Lewis Hamilton wins 2026 WDC!
    world.driver_points = {d["id"]: 0 for d in world.drivers}
    world.driver_points["hamilton"] = 420
    world.driver_points["verstappen"] = 410
    world.driver_points["norris"] = 380
    
    # Enter off-season & advance
    world._enter_off_season()
    assert world.reigning_wdc_id == "hamilton", f"Expected hamilton as reigning champion, got {world.reigning_wdc_id}"
    
    budgets_with_prize = {t["id"]: t["budget_m"] for t in world.teams}
    world._start_next_season()
    
    assert world.season_year == 2027
    print("  Season advanced to 2027 successfully.")
    
    # Check that each team carried over funds + received exactly 50M
    for t in world.teams:
        expected = round(budgets_with_prize[t["id"]] + 50.0, 2)
        actual = t["budget_m"]
        assert actual == expected, f"Team {t['id']} budget mismatch: expected {expected}, got {actual}"
    print("  All teams retained funds and received +$50.0M for standard 2027 season start.")
    
    # Check player ledger
    player_ledger_entry = [entry for entry in world.ledger if "2027 Season Start Budget Allocation" in entry["desc"]]
    assert len(player_ledger_entry) > 0
    assert player_ledger_entry[-1]["amount_m"] == 50.0
    print("  Player ledger correctly logged +$50.0M season start budget allocation.")
    
    # Check Car #1 awarded to Hamilton, Norris reverted to 4
    ham = next(d for d in world.drivers if d["id"] == "hamilton")
    nor = next(d for d in world.drivers if d["id"] == "norris")
    assert ham["number"] == 1, f"Expected Hamilton to have #1, got #{ham['number']}"
    assert nor["number"] == 4, f"Expected Norris to revert to #4, got #{nor['number']}"
    print(f"  Drivers' Champion Car #1: Lewis Hamilton is #{ham['number']}, Lando Norris reverted to #{nor['number']}.")
    
    # 2. New Regulations Season Transition (2027 -> 2028: +100M)
    print("\n[2] Testing 2028 New Regulations (+100M) and WDC Title Defense...")
    # Charles Leclerc wins 2027 WDC!
    world.driver_points = {d["id"]: 0 for d in world.drivers}
    world.driver_points["leclerc"] = 450
    world.driver_points["hamilton"] = 430
    
    world._enter_off_season()
    assert world.reigning_wdc_id == "leclerc"
    
    budgets_2027_end = {t["id"]: t["budget_m"] for t in world.teams}
    world._start_next_season()
    
    assert world.season_year == 2028
    print("  Season advanced to 2028 (New Regulations V8 & DRS era).")
    
    # Check that each team carried over funds + received exactly 100M
    for t in world.teams:
        expected = round(budgets_2027_end[t["id"]] + 100.0, 2)
        actual = t["budget_m"]
        assert actual == expected, f"Team {t['id']} budget mismatch in 2028: expected {expected}, got {actual}"
    print("  All teams retained funds and received +$100.0M for new 2028 regulations!")
    
    # Check player ledger
    player_ledger_entry_100 = [entry for entry in world.ledger if "2028 New Regulations Technical R&D Grant" in entry["desc"]]
    assert len(player_ledger_entry_100) > 0
    assert player_ledger_entry_100[-1]["amount_m"] == 100.0
    print("  Player ledger correctly logged +$100.0M technical R&D grant.")
    
    # Check Car #1 awarded to Leclerc, Hamilton reverted to 44
    lec = next(d for d in world.drivers if d["id"] == "leclerc")
    ham_28 = next(d for d in world.drivers if d["id"] == "hamilton")
    assert lec["number"] == 1, f"Expected Leclerc to have #1, got #{lec['number']}"
    assert ham_28["number"] == 44, f"Expected Hamilton to revert to #44, got #{ham_28['number']}"
    print(f"  Drivers' Champion Car #1: Charles Leclerc is #{lec['number']}, Lewis Hamilton reverted to #{ham_28['number']}.")

    # 3. Title Defense (Leclerc wins 2028, stays #1 in 2029)
    print("\n[3] Testing Title Defense (Back-to-back WDC)...")
    world.driver_points = {d["id"]: 0 for d in world.drivers}
    world.driver_points["leclerc"] = 500
    world._enter_off_season()
    world._start_next_season()
    assert world.season_year == 2029
    lec_29 = next(d for d in world.drivers if d["id"] == "leclerc")
    assert lec_29["number"] == 1, f"Expected Leclerc to defend and keep #1, got #{lec_29['number']}"
    print(f"  Title defense OK: Charles Leclerc retains #{lec_29['number']} for 2029.")

    print("\nALL FUNDS CARRYOVER AND CAR #1 TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_funds_carryover_and_champion_number()
