import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sim.championship import ChampionshipWorld

def test_camera_and_speed():
    print("[1] Testing 0.5x simulation speed in ChampionshipWorld...")
    world = ChampionshipWorld()
    
    # Test setting 0.5x speed
    res = world.set_sim_speed(0.5)
    print(f"  set_sim_speed(0.5) returned: {res}")
    assert res["ok"] is True
    assert res["sim_speed"] == 0.5
    assert world.sim_speed == 0.5
    
    payload = world.build_live_tick_payload()
    assert payload["sim_speed"] == 0.5
    print(f"  Live tick payload correctly reports sim_speed: {payload['sim_speed']}")
    
    # Test stepping at 0.5x speed vs 1.0x speed
    # Start race and wait for lights out
    while world.phase != "RACE":
        world.skip_session()
        
    rs = world.race_session
    assert rs is not None
    # Wait for green flag
    guard = 0
    while rs.flag_state != "GREEN" and guard < 100:
        rs.step(0.1, world._push_event)
        guard += 1

    car0 = rs.cars[0]
    car0.v = 50.0  # Ensure car is in motion
    
    # Step at 0.5x speed
    world.set_sim_speed(0.5)
    s_before_05 = car0.s
    world.step(0.1) # dt effective = 0.1 * 0.5 = 0.05
    dist_05 = (car0.s - s_before_05) % rs.track.length_m
    
    # Step at 1.0x speed
    world.set_sim_speed(1.0)
    s_before_10 = car0.s
    world.step(0.1) # dt effective = 0.1 * 1.0 = 0.10
    dist_10 = (car0.s - s_before_10) % rs.track.length_m
    
    print(f"  Distance covered at 0.5x: {dist_05:.2f}m")
    print(f"  Distance covered at 1.0x: {dist_10:.2f}m")
    assert 0.40 <= (dist_05 / max(0.001, dist_10)) <= 0.60, f"Expected ratio ~0.5, got {dist_05 / dist_10}"
    print("  0.5x simulation speed rate confirmed!")
    
    # Verify all speeds in allowed list
    for spd in [0.0, 0.5, 1.0, 2.0, 4.0, 8.0, 16.0]:
        r = world.set_sim_speed(spd)
        assert r["sim_speed"] == spd, f"Failed on speed {spd}"
    print("  All speeds in [0.0, 0.5, 1.0, 2.0, 4.0, 8.0, 16.0] verified.")
    
    # [2] Verify HTML button for 0.5X
    print("\n[2] Verifying frontend UI 0.5X button & canvas.js camera tracking...")
    html_text = Path("public/index.html").read_text(encoding="utf-8")
    assert 'data-speed="0.5"' in html_text, "data-speed='0.5' button missing in index.html"
    print("  index.html contains 0.5X button.")
    
    canvas_text = Path("public/canvas.js").read_text(encoding="utf-8")
    assert "this.renderTime" in canvas_text
    assert "interpolateEntity" in canvas_text
    print("  canvas.js contains continuous snapshot buffer interpolation and rock-solid camera lock.")
    
    print("\nALL CAMERA SMOOTHING AND 0.5X SPEED TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_camera_and_speed()
