import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sim.radio import (
    RadioDispatcher,
    DRIVER_PUSH_RADIOS,
    DRIVER_OVERTAKEN_RADIOS,
    DRIVER_OVERTAKE_RADIOS,
)
from sim.championship import ChampionshipWorld

def test_push_mode_radio_events():
    print("[1] Testing Push/Max/Attack and Conserve mode radio event triggers...")
    disp = RadioDispatcher()
    events = []
    def cb(kind, msg):
        events.append((kind, msg))

    class MockCar:
        def __init__(self, code, name, number, team, driver_id):
            self.driver_id = driver_id
            self.code = code
            self.driver_name = name
            self.number = number
            self.team_short = team
            self.s = 850.0
            self.last_radio_time = -99.0
            self.pace_mode = "BALANCED"
            self.ers_mode = "AUTO"

    ham = MockCar("HAM", "Lewis Hamilton", 44, "Ferrari", "hamilton")
    ver = MockCar("VER", "Max Verstappen", 1, "Red Bull", "verstappen")
    alo = MockCar("ALO", "Fernando Alonso", 14, "Aston Martin", "alonso")
    nor = MockCar("NOR", "Lando Norris", 4, "McLaren", "norris")

    # Test Hamilton push mode trigger
    disp.trigger_push_mode(ham, "PUSH", is_pit_wall=False, event_cb=cb, clock=10.0, turn=1)
    assert len(events) == 1
    assert events[-1][0] == "RADIO"
    assert "44" in events[-1][1] or "HAM" in events[-1][1] or "Ferrari" in events[-1][1]
    print("  Hamilton push mode radio:", events[-1][1])

    # Test Verstappen max mode trigger
    disp.trigger_push_mode(ver, "MAX ATTACK", is_pit_wall=False, event_cb=cb, clock=20.0, turn=3)
    assert len(events) == 2
    assert "VER" in events[-1][1] or "Red Bull" in events[-1][1]
    print("  Verstappen max mode radio:", events[-1][1])

    # Test Alonso push mode trigger
    disp.trigger_push_mode(alo, "ATTACK", is_pit_wall=False, event_cb=cb, clock=30.0, turn=4)
    assert len(events) == 3
    assert "ALO" in events[-1][1] or "Aston Martin" in events[-1][1]
    print("  Alonso attack mode radio:", events[-1][1])

    # Test Conserve mode trigger
    disp.trigger_conserve_mode(nor, event_cb=cb, clock=40.0, turn=6)
    assert len(events) == 4
    assert "NOR" in events[-1][1] or "McLaren" in events[-1][1]
    low = events[-1][1].lower()
    assert any(w in low for w in ["conserve", "harvest", "saving", "tyre", "lifting", "rears", "temperatures"])
    print("  Norris conserve mode radio:", events[-1][1])

    print("  [OK] Push/Max and Conserve mode events verified!\n")

def test_overtaken_radio_events():
    print("[2] Testing Overtaken and Overtake event radio triggers...")
    disp = RadioDispatcher()
    events = []
    def cb(kind, msg):
        events.append((kind, msg))

    class MockCar:
        def __init__(self, code, name, number, team, driver_id):
            self.driver_id = driver_id
            self.code = code
            self.driver_name = name
            self.number = number
            self.team_short = team
            self.s = 1200.0
            self.last_radio_time = -99.0

    alo = MockCar("ALO", "Fernando Alonso", 14, "Aston Martin", "alonso")
    ham = MockCar("HAM", "Lewis Hamilton", 44, "Ferrari", "hamilton")
    lec = MockCar("LEC", "Charles Leclerc", 16, "Ferrari", "leclerc")
    nor = MockCar("NOR", "Lando Norris", 4, "McLaren", "norris")
    ver = MockCar("VER", "Max Verstappen", 1, "Red Bull", "verstappen")

    # Alonso gets overtaken by Hamilton
    disp.trigger_overtaken(overtaken_car=alo, overtaker_car=ham, turn=4, event_cb=cb, clock=15.0)
    assert len(events) == 1
    assert "ALO" in events[-1][1] or "Aston Martin" in events[-1][1]
    print("  Alonso overtaken radio:", events[-1][1])

    # Leclerc gets overtaken by Verstappen
    disp.trigger_overtaken(overtaken_car=lec, overtaker_car=ver, turn=1, event_cb=cb, clock=25.0)
    assert len(events) == 2
    assert "LEC" in events[-1][1] or "Ferrari" in events[-1][1]
    print("  Leclerc overtaken radio:", events[-1][1])

    # Hamilton makes an overtake on Norris
    disp.trigger_overtake_success(overtaker_car=ham, overtaken_car=nor, new_p=2, turn=5, event_cb=cb, clock=35.0)
    assert len(events) == 3
    assert "HAM" in events[-1][1] or "Ferrari" in events[-1][1]
    print("  Hamilton overtake success radio:", events[-1][1])

    # General overtake event dispatcher
    disp.trigger_overtake_event(overtaker=ver, overtaken=alo, new_p=1, turn=1, event_cb=cb, clock=50.0)
    assert len(events) == 4
    print("  Overtake dispatcher radio:", events[-1][1])

    print("  [OK] Overtaken and Overtake event radios verified!\n")

def test_pit_wall_command_triggers_radio():
    print("[3] Testing pit wall command changing pace/ers mode in live ChampionshipWorld...")
    world = ChampionshipWorld()
    # Advance to RACE phase
    guard = 0
    while world.phase != "RACE" and guard < 10:
        world.skip_session()
        guard += 1
    assert world.phase == "RACE"

    player_team = world.player_team_id
    team_drivers = [d for d in world.drivers if d["team_id"] == player_team]
    assert len(team_drivers) >= 1
    lead_drv = team_drivers[0]
    lead_car = world.race_session.cars_by_id[lead_drv["id"]]
    lead_car.pace_mode = "BALANCED"

    initial_events = len([ev for ev in world.event_feed if ev["kind"] == "RADIO"])

    # Issue Pit Wall command: change pace mode to PUSH
    res = world.pit_wall_command(lead_drv["id"], {"pace_mode": "PUSH"})
    assert res["ok"] is True
    assert lead_car.pace_mode == "PUSH"

    push_events = [ev for ev in world.event_feed if ev["kind"] == "RADIO"]
    assert len(push_events) > initial_events, "Pit wall push command did not trigger radio event!"
    last_msg = push_events[-1]["msg"]
    print("  Pit wall push command triggered radio:", last_msg)
    assert lead_car.code in last_msg or lead_car.team_short in last_msg or "PUSH" in last_msg or "Hammer" in last_msg or "wick" in last_msg or "attack" in last_msg.lower() or "push" in last_msg.lower()

    # Issue Pit Wall command: change pace mode to CONSERVE
    res2 = world.pit_wall_command(lead_drv["id"], {"pace_mode": "CONSERVE"})
    assert res2["ok"] is True
    assert lead_car.pace_mode == "CONSERVE"

    conserve_events = [ev for ev in world.event_feed if ev["kind"] == "RADIO"]
    assert len(conserve_events) > len(push_events), "Pit wall conserve command did not trigger radio event!"
    last_msg2 = conserve_events[-1]["msg"]
    print("  Pit wall conserve command triggered radio:", last_msg2)

    print("  [OK] Pit Wall command live triggers verified!\n")

def test_no_random_empty_radios():
    print("[4] Testing that step() does not broadcast random chatter when cars are cruising...")
    disp = RadioDispatcher()
    events = []
    def cb(kind, msg):
        events.append((kind, msg))

    class CruisingCar:
        def __init__(self, code, num):
            self.code = code
            self.number = num
            self.team_short = "Team"
            self.driver_id = f"drv_{num}"
            self.tailing_timer = 0.0 # Clean air, not battling!
            self.blue_flag = False
            self.dnf = False
            self.in_pits = False
            self.s = 100.0

    cars = [CruisingCar("C1", 1), CruisingCar("C2", 2)]
    dummy_track = type("Track", (), {"nearest_corner": lambda self, s: 1})()

    # Run step 200 times (simulating 20 seconds of empty racing)
    for t in range(200):
        disp.step(0.1, t * 0.1, cars, dummy_track, 0.0, "GREEN", cb)

    # In clean air without tailing pressure or events, no radio messages should be randomly spat out!
    assert len(events) == 0, f"Expected 0 random radio messages in clean air, got {len(events)}!"
    print("  Clean air test: exactly 0 random radio messages emitted during 20 seconds of cruising.")
    print("  [OK] Random chatter completely eliminated in favor of event triggers!\n")

if __name__ == "__main__":
    test_push_mode_radio_events()
    test_overtaken_radio_events()
    test_pit_wall_command_triggers_radio()
    test_no_random_empty_radios()
    print("ALL EVENT-TRIGGERED RADIO TESTS PASSED SUCCESSFULLY!")
