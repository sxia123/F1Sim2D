import os
import sys
import random

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pathlib import Path
from sim.tracks import TRACK_BY_ID
from sim.data import INITIAL_TEAMS, INITIAL_DRIVERS
from sim.physics import CarState, RaceSession
from sim.radio import (
    RadioDispatcher,
    DRIVER_PUSH_RADIOS,
    PUSH_MODE_RADIOS,
    CONSERVE_MODE_RADIOS,
    DRIVER_OVERTAKEN_RADIOS,
    OVERTAKEN_RADIOS,
    DRIVER_OVERTAKE_RADIOS,
    OVERTAKE_SUCCESS_RADIOS,
)
from sim.championship import ChampionshipWorld

def test_push_and_conserve_mode_triggers():
    print("[1] Testing Push/Max/Attack and Conserve mode radio event triggers...")
    disp = RadioDispatcher()

    drivers_by_id = {d["id"]: d for d in INITIAL_DRIVERS}
    teams_by_id = {t["id"]: t for t in INITIAL_TEAMS}

    ham = CarState(drivers_by_id["hamilton"], teams_by_id["ferrari"], 1, "MEDIUM", 50)
    ver = CarState(drivers_by_id["verstappen"], teams_by_id["redbull"], 2, "MEDIUM", 50)
    alo = CarState(drivers_by_id["alonso"], teams_by_id["aston"], 3, "MEDIUM", 50)
    nor = CarState(drivers_by_id["norris"], teams_by_id["mclaren"], 4, "MEDIUM", 50)

    events = []
    def cb(kind, msg):
        events.append((kind, msg))

    # Test Hamilton push mode trigger
    disp.trigger_push_mode(car=ham, mode_name="PUSH", is_pit_wall=False, event_cb=cb, clock=10.0, turn=3)
    assert len(events) == 1
    assert events[-1][0] == "RADIO"
    print("  Hamilton push mode radio:", events[-1][1])

    # Test Verstappen max mode trigger
    disp.trigger_push_mode(car=ver, mode_name="MAX ATTACK", is_pit_wall=False, event_cb=cb, clock=25.0, turn=1)
    assert len(events) == 2
    assert "VER" in events[-1][1] or "Red Bull" in events[-1][1]
    print("  Verstappen max mode radio:", events[-1][1])

    # Test Alonso attack mode trigger
    disp.trigger_push_mode(car=alo, mode_name="ATTACK", is_pit_wall=False, event_cb=cb, clock=40.0, turn=10)
    assert len(events) == 3
    assert "ALO" in events[-1][1] or "Aston Martin" in events[-1][1]
    print("  Alonso attack mode radio:", events[-1][1])

    # Test Norris conserve mode trigger
    disp.trigger_conserve_mode(car=nor, event_cb=cb, clock=55.0, turn=8)
    assert len(events) == 4
    assert "NOR" in events[-1][1] or "McLaren" in events[-1][1]
    print("  Norris conserve mode radio:", events[-1][1])

    print("  [OK] Push/Max and Conserve mode events verified!\n")

def test_overtaken_and_overtake_success_triggers():
    print("[2] Testing Overtaken and Overtake event radio triggers...")
    disp = RadioDispatcher()

    drivers_by_id = {d["id"]: d for d in INITIAL_DRIVERS}
    teams_by_id = {t["id"]: t for t in INITIAL_TEAMS}

    alo = CarState(drivers_by_id["alonso"], teams_by_id["aston"], 3, "MEDIUM", 50)
    ham = CarState(drivers_by_id["hamilton"], teams_by_id["ferrari"], 1, "MEDIUM", 50)
    lec = CarState(drivers_by_id["leclerc"], teams_by_id["ferrari"], 2, "MEDIUM", 50)
    ver = CarState(drivers_by_id["verstappen"], teams_by_id["redbull"], 4, "MEDIUM", 50)
    nor = CarState(drivers_by_id["norris"], teams_by_id["mclaren"], 5, "MEDIUM", 50)

    events = []
    def cb(kind, msg):
        events.append((kind, msg))

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
    temp_save = os.path.join("scratch", "temp_radio_test_save.json")
    if os.path.exists(temp_save):
        os.remove(temp_save)
    world = ChampionshipWorld(save_path=Path(temp_save))
    # Advance to RACE phase
    guard = 0
    while world.phase != "RACE" and guard < 15:
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
    last_conserve_msg = conserve_events[-1]["msg"]
    print("  Pit wall conserve command triggered radio:", last_conserve_msg)
    assert lead_car.code in last_conserve_msg or lead_car.team_short in last_conserve_msg or "conserve" in last_conserve_msg.lower() or "temperatures" in last_conserve_msg.lower() or "harvest" in last_conserve_msg.lower() or "tyres" in last_conserve_msg.lower()

    print("  [OK] Pit Wall command live triggers verified!\n")
    if os.path.exists(temp_save):
        try:
            os.remove(temp_save)
        except Exception:
            pass

def test_no_random_chatter_during_clean_cruising():
    print("[4] Testing that step() does not broadcast random chatter when cars are cruising...")
    teams_by_id = {t["id"]: t for t in INITIAL_TEAMS}
    drivers = [d for d in INITIAL_DRIVERS if d.get("team_id")]
    track = TRACK_BY_ID["italy"]
    session = RaceSession(track, teams_by_id, drivers, 0.0, 0.0, "mclaren")
    session.flag_state = "GREEN"

    # Space all cars out cleanly so no battles or passes occur
    for idx, c in enumerate(session.cars):
        c.s = (idx * 250.0) % track.length_m
        c.total_dist = c.s
        c.v = 75.0
        c.d = 0.0
        c.target_d = 0.0
        c.auto_strategy = False  # disable dynamic push to isolate cruising

    radio_events = []
    def radio_cb(kind, msg):
        if kind == "RADIO":
            radio_events.append(msg)

    # Step for 20 seconds of simulation
    for _ in range(400):
        session.step(0.05, radio_cb)

    print(f"  Clean air test: exactly {len(radio_events)} random radio messages emitted during 20 seconds of cruising.")
    assert len(radio_events) == 0, f"Expected 0 random radio messages during clean cruising, got {len(radio_events)}!"
    print("  [OK] Random chatter completely eliminated in favor of event triggers!\n")

if __name__ == "__main__":
    test_push_and_conserve_mode_triggers()
    test_overtaken_and_overtake_success_triggers()
    test_pit_wall_command_triggers_radio()
    test_no_random_chatter_during_clean_cruising()
    print("ALL EVENT-TRIGGERED RADIO TESTS PASSED SUCCESSFULLY!")
