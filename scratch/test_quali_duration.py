import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sim.championship import ChampionshipWorld
from sim.tracks import COMPILED_TRACKS

def test_qualifying_durations():
    print("[1] Testing Qualifying stage durations and Championship integration...")
    world = ChampionshipWorld()
    
    # Verify current phase is PRE_WEEKEND
    print(f"  Initial phase: {world.phase}")
    
    # Skip to Qualifying
    world.skip_session()
    print(f"  Advanced phase: {world.phase}")
    assert world.phase in ("QUALIFYING", "SPRINT_QUALIFYING"), f"Unexpected phase {world.phase}"
    assert world.quali_session is not None
    
    qs = world.quali_session
    print(f"  Stage name: {qs.stage_name}")
    print(f"  Stage duration: {qs.stage_duration}s ({qs.stage_duration / 60:.1f} mins)")
    print(f"  All stages: {qs.stages}")
    
    # Assert each stage is exactly 180 seconds (3 minutes)
    for st_name, dur, cut in qs.stages:
        assert dur == 180.0, f"Expected 180.0s for {st_name}, got {dur}"
    
    # Check payload clock
    payload = world.build_live_tick_payload()
    print(f"  Live payload clock: {payload['clock']}s (Stage: {payload['quali_stage']})")
    assert payload["clock"] == 180.0, f"Expected 180.0s clock, got {payload['clock']}"
    
    # Step simulation a few ticks
    for _ in range(20):
        world.step(0.1)
    
    payload = world.build_live_tick_payload()
    print(f"  Live payload clock after stepping: {payload['clock']}s")
    assert payload["clock"] < 180.0
    
    # Test advance stage (Q1 -> Q2)
    world.skip_session()
    print(f"  After 1st advance: stage={world.quali_session.stage_name}, time_left={world.quali_session.stage_time_left}s")
    assert world.quali_session.stage_name in ("Q2", "SQ2")
    assert world.quali_session.stage_duration == 180.0
    
    # Test advance stage (Q2 -> Q3)
    world.skip_session()
    print(f"  After 2nd advance: stage={world.quali_session.stage_name}, time_left={world.quali_session.stage_time_left}s")
    assert world.quali_session.stage_name in ("Q3", "SQ3")
    assert world.quali_session.stage_duration == 180.0
    
    # Test advance stage (Q3 -> finish)
    world.skip_session()
    print(f"  After 3rd advance: phase={world.phase}")
    assert world.phase in ("GRID_WALK", "SPRINT_RACE"), f"Unexpected phase {world.phase}"
    
    print("[1] Qualifying 3-minute stage duration test passed successfully!\n")

if __name__ == "__main__":
    test_qualifying_durations()
    print("ALL QUALI TESTS PASSED!")

