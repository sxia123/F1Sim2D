import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sim.championship import ChampionshipWorld

def test_instant_2028_restart():
    print("[1] Testing instant start at 2028 season via reset_career...")
    world = ChampionshipWorld()
    
    # Reset career with start_year=2028
    res = world.reset_career(team_id="ferrari", start_year=2028)
    assert res["ok"] is True
    assert res["season_year"] == 2028
    assert world.season_year == 2028
    assert world.current_round == 1
    assert world.player_team_id == "ferrari"
    print("  reset_career(start_year=2028) returned ok and set season_year=2028.")
    
    # Verify regulations era
    reg = world.regulations
    print(f"  Regulations name: {reg['name']}")
    print(f"  Engine type: {reg['engine_type']}")
    print(f"  Has classic DRS: {reg['has_classic_drs']}")
    print(f"  Has active aero: {reg['has_active_aero']}")
    assert reg["era_id"] == "V8_DRS"
    assert "V8" in reg["engine_type"]
    assert reg["has_classic_drs"] is True
    assert reg["has_active_aero"] is False
    assert reg["max_battery_mj"] == 2.0
    print("  2028 V8 & Classic DRS regulations active immediately.")
    
    # Verify reigning champion Car #1 allocation
    ver = next(d for d in world.drivers if d["id"] == "verstappen")
    nor = next(d for d in world.drivers if d["id"] == "norris")
    print(f"  Max Verstappen: #{ver['number']} (career: #{ver.get('career_number')})")
    print(f"  Lando Norris: #{nor['number']} (career: #{nor.get('career_number')})")
    assert ver["number"] == 1
    assert nor["number"] == 4
    assert world.reigning_wdc_id == "verstappen"
    print("  Car #1 correctly assigned to reigning champion Max Verstappen.")
    
    # Verify driver ages (2026 + 2 = 2028)
    # Hamilton was 41 in 2026 -> 43 in 2028
    ham = next(d for d in world.drivers if d["id"] == "hamilton")
    print(f"  Lewis Hamilton age in 2028: {ham['age']}")
    assert ham["age"] == 43
    print("  Drivers properly aged by 2 years for 2028 start.")
    
    # Verify live tick payload in 2028
    payload = world.build_live_tick_payload()
    assert payload["season"] == 2028
    assert payload["regulations"]["era_id"] == "V8_DRS"
    assert payload["regulations"]["has_classic_drs"] is True
    print("  build_live_tick_payload confirms season=2028 and V8_DRS era.")
    
    # Verify reset back to 2026 works as well
    print("\n[2] Testing reset back to 2026...")
    res26 = world.reset_career(team_id="williams", start_year=2026)
    assert res26["ok"] is True
    assert res26["season_year"] == 2026
    assert world.season_year == 2026
    assert world.regulations["era_id"] == "2026_HYBRID"
    assert world.regulations["has_active_aero"] is True
    assert world.regulations["has_classic_drs"] is False
    print("  Reset back to 2026 Hybrid era functions perfectly.")
    
    print("\nALL 2028 INSTANT RESTART TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_instant_2028_restart()

