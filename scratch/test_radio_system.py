import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sim.radio import (
    RadioDispatcher,
    DRIVER_ICONIC_RADIOS,
    BOX_CALL_RADIOS,
    PIT_EXIT_RADIOS,
    DIRTY_AIR_AND_BATTLE_RADIOS,
    CONTACT_RADIOS,
    FASTEST_LAP_RADIOS,
    TYRE_CLIFF_RADIOS,
    WEATHER_RADIOS,
    AMBIENT_TECHNICAL_RADIOS,
)
from sim.championship import ChampionshipWorld

def test_radio_dispatcher():
    print("[1] Testing RadioDispatcher directly...")
    disp = RadioDispatcher()
    events = []
    def cb(kind, msg):
        events.append((kind, msg))

    class DummyCar:
        def __init__(self, code, name, number, team, compound, tyre_wear=0.0):
            self.driver_id = name.split()[-1].lower()
            self.code = code
            self.driver_name = name
            self.number = number
            self.team_short = team
            self.compound = compound
            self.next_compound = "MEDIUM"
            self.tire_wear = tyre_wear
            self.dnf = False
            self.last_radio_time = -99.0
            self.tailing_timer = 10.0
            self.front_wing_dmg = 0.3
            self.laps_completed = 5
            self.in_pits = False
            self.position = 3
            self.s = 1500.0

    ham = DummyCar("HAM", "Lewis Hamilton", 44, "Ferrari", "HARD")
    ver = DummyCar("VER", "Max Verstappen", 1, "Red Bull", "MEDIUM")
    alo = DummyCar("ALO", "Fernando Alonso", 14, "Aston Martin", "SOFT")
    rai = DummyCar("RAI", "Kimi Raikkonen", 7, "Ferrari", "HARD")

    # Test box call
    disp.trigger_box_call(ham, cb)
    assert len(events) == 1
    assert events[-1][0] == "RADIO"
    assert "Ferrari" in events[-1][1] or "HAM" in events[-1][1]
    print("  Box call OK:", events[-1][1])

    # Test pit exit
    disp.trigger_pit_exit(ver, 2.34, cb)
    assert len(events) == 2
    assert events[-1][0] == "RADIO"
    assert "Red Bull" in events[-1][1] or "VER" in events[-1][1]
    print("  Pit exit OK:", events[-1][1])

    # Test fastest lap
    disp.trigger_fastest_lap(alo, "1:21.450", cb)
    assert len(events) == 3
    assert events[-1][0] == "RADIO"
    assert "Aston Martin" in events[-1][1] or "ALO" in events[-1][1]
    print("  Fastest lap OK:", events[-1][1])

    # Test contact
    disp.trigger_contact(ham, ver, 4, cb, 50.0)
    assert len(events) == 4
    assert events[-1][0] == "RADIO"
    print("  Contact OK:", events[-1][1])

    # Test iconic radios for legends and current grid
    for leg in ["hamilton", "verstappen", "alonso", "raikkonen", "senna", "schumacher", "lauda", "vettel"]:
        assert leg in DRIVER_ICONIC_RADIOS, f"Missing iconic quote for {leg}"
    print("  Driver iconic radios verified for icons (Hamilton, Verstappen, Alonso, Kimi, Senna, Schumacher, Lauda, Vettel).")

    # Test step periodic chatter
    disp.radio_timer = 0.0 # Force timer trigger
    dummy_track = type("Track", (), {"nearest_corner": lambda self, s: 4})()
    disp.step(0.1, 100.0, [ham, ver, alo, rai], dummy_track, 0.0, "GREEN", cb)
    assert len(events) >= 5
    print("  Ambient/battle radio step OK:", events[-1][1])

    print("[1] RadioDispatcher passed!\n")

def test_championship_world_radio_integration():
    print("[2] Testing ChampionshipWorld live radio integration...")
    world = ChampionshipWorld()
    # Advance to RACE phase
    guard = 0
    while world.phase != "RACE" and guard < 10:
        world.skip_session()
        guard += 1
    print(f"  Championship reached phase: {world.phase} in {guard} steps")
    assert world.phase == "RACE"
    assert world.race_session is not None
    assert hasattr(world.race_session, "radio_dispatcher")

    # Capture initial events count
    initial_event_count = len(world.event_feed)

    # Let the race run for a bit
    world.set_sim_speed(5.0)
    for _ in range(60):
        world.step(0.1)

    # Manually trigger box call and contact to verify push_event
    car1 = world.race_session.cars[0]
    car2 = world.race_session.cars[1]
    world.race_session.radio_dispatcher.trigger_box_call(car1, world._push_event)
    world.race_session.radio_dispatcher.trigger_contact(car1, car2, 1, world._push_event, 500.0)
    world.race_session.radio_dispatcher.trigger_fastest_lap(car2, "1:23.456", world._push_event)

    radio_events = [ev for ev in world.event_feed if ev["kind"] == "RADIO"]
    assert len(radio_events) >= 3, f"Expected at least 3 radio events, got {len(radio_events)}"
    print(f"  Captured {len(radio_events)} radio events in ChampionshipWorld.event_feed:")
    for r in radio_events[-3:]:
        print(f"    [{r['tag']} | {r['kind']}] {r['msg']}")

    # Verify live tick payload contains RADIO events and respect 60 max events limit
    payload = world.build_live_tick_payload()
    payload_radios = [ev for ev in payload["events"] if ev["kind"] == "RADIO"]
    assert len(payload_radios) >= 3
    assert len(payload["events"]) <= 60
    assert len(world.event_feed) <= 160
    print("  Live tick payload correctly formatted with RADIO kind and tags.")

    print("[2] ChampionshipWorld radio integration passed!\n")

if __name__ == "__main__":
    test_radio_dispatcher()
    test_championship_world_radio_integration()
    print("ALL TESTS PASSED SUCCESSFULLY!")
