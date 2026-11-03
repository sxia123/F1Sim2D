import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sim.championship import ChampionshipWorld
from sim.data import driver_overall

def test_performance_scoring():
    print("[1] Testing driver score adjustments based on last year's performance...")
    import tempfile
    tmp_path = Path(tempfile.mktemp(suffix=".json"))
    world = ChampionshipWorld(save_path=tmp_path)
    world.reset_career(start_year=2026)
    world.season_year = 2026
    
    # Capture pre-season driver stats and overalls
    pre_stats = {d["id"]: {k: d[k] for k in ("pace", "racecraft", "consistency", "tire_mgmt", "defense", "wet_skill")} for d in world.drivers}
    pre_ovr = {d["id"]: driver_overall(d) for d in world.drivers}
    
    # Realistic grid results:
    # 1. Oscar Piastri has a sensational championship-winning season for McLaren: 420 pts, 8 wins, 14 podiums
    # 2. Kimi Antonelli (Mercedes rookie) breaks out: 120 pts, 3 podiums, beats Russell (90 pts)
    # 3. Isack Hadjar (Red Bull) has a disastrous season: 2 pts, 5 DNFs, while Verstappen scores 380 pts
    points_map = {
        "piastri": 420, "verstappen": 380, "hamilton": 350, "leclerc": 340, "norris": 310,
        "antonelli": 140, "russell": 70, "alonso": 85, "gasly": 40, "sainz": 35,
        "colapinto": 30, "lawson": 25, "albon": 22, "stroll": 20, "lindblad": 18,
        "hulkenberg": 15, "ocon": 12, "bortoleto": 10, "bearman": 8, "bottas": 6,
        "perez": 4, "hadjar": 2
    }
    team_points_map = {
        "mclaren": 730, "redbull": 382, "ferrari": 690, "mercedes": 210, "aston": 105,
        "alpine": 70, "williams": 57, "racingbulls": 43, "audi": 25, "haas": 20, "cadillac": 10
    }
    world.driver_points = points_map
    world.team_points = team_points_map
    
    world.driver_wins = {d["id"]: 0 for d in world.drivers}
    world.driver_podiums = {d["id"]: 0 for d in world.drivers}
    world.driver_poles = {d["id"]: 0 for d in world.drivers}
    world.driver_dnfs = {d["id"]: 0 for d in world.drivers}
    
    world.driver_wins["piastri"] = 8
    world.driver_podiums["piastri"] = 14
    world.driver_poles["piastri"] = 6
    world.driver_podiums["antonelli"] = 3
    world.driver_dnfs["hadjar"] = 5
    
    # Enter off season and start next season
    world._enter_off_season()
    world._start_next_season()
    
    assert world.season_year == 2027
    
    post_ovr = {d["id"]: driver_overall(d) for d in world.drivers}
    
    # 1. Piastri (WDC winner, 8 wins, 14 podiums) should receive a major score upgrade
    piastri_d = next(d for d in world.drivers if d["id"] == "piastri")
    print(f"  Oscar Piastri: {pre_ovr['piastri']} -> {post_ovr['piastri']} (diff: {piastri_d.get('last_ovr_change')})")
    assert post_ovr["piastri"] > pre_ovr["piastri"], f"Expected Piastri to improve, but {pre_ovr['piastri']} >= {post_ovr['piastri']}"
    assert piastri_d["last_ovr_change"] >= 1.5
    assert piastri_d["pace"] >= pre_stats["piastri"]["pace"] + 2
    
    # 2. Antonelli (Rookie breakout, 120 pts, 3 podiums, beat teammate) should gain score
    ant_d = next(d for d in world.drivers if d["id"] == "antonelli")
    print(f"  Kimi Antonelli: {pre_ovr['antonelli']} -> {post_ovr['antonelli']} (diff: {ant_d.get('last_ovr_change')})")
    assert post_ovr["antonelli"] > pre_ovr["antonelli"]
    assert ant_d["last_ovr_change"] >= 1.0
    
    # 3. Hadjar (Disastrous season in top car: 2 pts vs 380 teammate, 5 DNFs) should decrease in score
    hadjar_d = next(d for d in world.drivers if d["id"] == "hadjar")
    print(f"  Isack Hadjar: {pre_ovr['hadjar']} -> {post_ovr['hadjar']} (diff: {hadjar_d.get('last_ovr_change')})")
    assert post_ovr["hadjar"] < pre_ovr["hadjar"], f"Expected Hadjar to decline, but {post_ovr['hadjar']} >= {pre_ovr['hadjar']}"
    assert hadjar_d["last_ovr_change"] <= -1.0
    assert hadjar_d["pace"] < pre_stats["hadjar"]["pace"]
    
    # 4. Check that news events were generated for driver developments
    dev_events = [ev for ev in world.event_feed if "DRIVER DEVELOPMENT" in ev["msg"] or "DRIVER RATINGS" in ev["msg"]]
    assert len(dev_events) > 0, "Expected driver development feed events"
    print("  Feed events emitted:")
    for ev in dev_events:
        print(f"    - {ev['msg']}")
        
    # 5. Check build_full_state_payload includes last_ovr_change
    full_state = world.build_full_state_payload()
    pia_payload = next(d for d in full_state["drivers"] if d["id"] == "piastri")
    assert "last_ovr_change" in pia_payload
    assert pia_payload["last_ovr_change"] == piastri_d["last_ovr_change"]
    print(f"  full_state payload driver has last_ovr_change: {pia_payload['last_ovr_change']}")
    
    print("\nALL PERFORMANCE SCORING TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_performance_scoring()
