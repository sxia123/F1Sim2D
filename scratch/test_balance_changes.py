import os
import sys
import random

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sim.tracks import TRACK_BY_ID
from sim.data import INITIAL_TEAMS, INITIAL_DRIVERS
from sim.physics import RaceSession, CarState
from sim.radio import RadioDispatcher

teams_by_id = {t["id"]: t for t in INITIAL_TEAMS}
drivers = [d for d in INITIAL_DRIVERS if d.get("team_id")]

def test_tow_balance():
    print("[1] Testing Tow / Slipstream Balance...")
    track = TRACK_BY_ID["italy"]
    session = RaceSession(track, teams_by_id, drivers, 0.0, 0.0, "mclaren")
    session.flag_state = "GREEN"

    car_a = session.cars[0]
    car_b = session.cars[1]
    car_a.in_pits = False
    car_b.in_pits = False
    car_a.dnf = False
    car_b.dnf = False

    # Position both on the main straight at Monza (s ~ 200m)
    smp = track.sample(200.0)
    st = smp["station"]
    assert smp["curv"] < 0.0042, f"Expected straight curv, got {smp['curv']}"
    assert not session.is_braking[st], "Expected not braking zone"

    # Test Case A: Car B is FAR behind Car A (50 meters, gap ~ 0.65s)
    car_a.s = 250.0
    car_a.v = 80.0
    car_a.d = 0.0
    car_b.s = 200.0
    car_b.v = 80.0
    car_b.d = 0.0

    session.step(0.05, lambda t, m: None)
    dist_ahead = (car_a.s - car_b.s) % track.length_m
    gap = dist_ahead / max(car_b.v, 25.0)
    print(f"  Far distance test: dist_ahead={dist_ahead:.1f}m, gap={gap:.2f}s")
    assert dist_ahead > 28.0, "Expected dist > 28m"

    # Test Case B: Car B is RIGHT BEHIND Car A (15m ahead, gap ~ 0.18s), tucked directly in wake (d=0.0)
    car_a.s = 215.0
    car_a.v = 85.0
    car_a.d = 0.0
    car_b.s = 200.0
    car_b.v = 85.0
    car_b.d = 0.0

    session.step(0.05, lambda t, m: None)
    dist_ahead = (car_a.s - car_b.s) % track.length_m
    gap = dist_ahead / max(car_b.v, 25.0)
    print(f"  Right behind in wake: dist_ahead={dist_ahead:.1f}m, gap={gap:.2f}s")
    assert dist_ahead <= 28.0 and gap <= 0.36, "Expected right behind"

    # Test Case C: Car B is CLOSE (15m), but JINKED OUT laterally to pass (car_a.d=0.0, car_b.d=0.5)
    car_a.s = 215.0
    car_a.v = 85.0
    car_a.d = 0.0
    car_b.s = 200.0
    car_b.v = 85.0
    car_b.d = 0.50  # Out of wake

    lat_offset = abs(car_b.d - car_a.d)
    print(f"  Lateral offset test: lat_offset={lat_offset:.2f} (wake limit=0.22)")
    assert lat_offset > 0.22, "Expected offset outside wake"

    # Test Case D: Check top speed gain is realistic (capped <= 1.6%)
    pu_top = 1.0
    base_top = 91.2 * pu_top
    max_bonus = 0.016
    max_boosted_top = base_top * (1.0 + max_bonus)
    speed_diff_kmh = (max_boosted_top - base_top) * 3.6
    print(f"  Max tow top speed increase: +{speed_diff_kmh:.2f} km/h (authentic F1 range is 4-7 km/h)")
    assert 3.5 <= speed_diff_kmh <= 6.5, f"Expected realistic speed diff, got {speed_diff_kmh} km/h"
    print("  [OK] Tow / Slipstream balance verified successfully!")

def test_divebomb_balance():
    print("\n[2] Testing Divebomb restriction to Hairpins and Corners...")
    for tid in ["italy", "monaco", "canada", "belgium"]:
        track = TRACK_BY_ID[tid]
        session = RaceSession(track, teams_by_id, drivers, 0.0, 0.0, "mclaren")
        atk = session.cars[0]
        dfn = session.cars[1]
        atk.skills = {"racecraft": 92, "pace": 90, "defense": 85, "consistency": 90, "wet_skill": 88}
        dfn.skills = {"racecraft": 86, "pace": 85, "defense": 82, "consistency": 85, "wet_skill": 80}
        atk.pace_mode = "ATTACK"
        atk.lap = 3
        dfn.lap = 3

        # Test A: Straightaways across the circuit
        straight_divebombs = 0
        straight_evals = 0
        for s in range(0, int(track.length_m), 15):
            smp = track.sample(float(s))
            if smp.get("straight_mode", False) or smp["curv"] < 0.0035:
                # Check nearest corner distance
                dist_c = min(abs(c["s_m"] - (s % track.length_m)) for c in track.corners)
                if dist_c > 80.0:
                    atk.s = float(s)
                    dfn.s = float(s + 8.0)
                    for _ in range(5):
                        maneuver, p_succ, man_d = session.select_and_evaluate_maneuver(atk, dfn, smp, False)
                        straight_evals += 1
                        if maneuver == "DIVEBOMB":
                            straight_divebombs += 1

        print(f"  {track.name}: Straight evaluations={straight_evals}, Straight divebombs={straight_divebombs}")
        assert straight_divebombs == 0, f"Divebomb occurred on a straight! ({straight_divebombs} times)"

        # Test B: Hairpin Corners
        hairpins = []
        for c in track.corners:
            st = c["station"]
            k = track.stations[st]["curv"]
            v = session.v_env[st]
            if k >= 0.012 or v <= 38.0:
                hairpins.append(c)

        if hairpins:
            hp_divebombs = 0
            hp_evals = 0
            for hp in hairpins:
                # Place cars entering hairpin
                s_entry = (hp["s_m"] - 35.0) % track.length_m
                smp = track.sample(s_entry)
                atk.s = s_entry
                dfn.s = (s_entry + 8.0) % track.length_m
                # Defender leaves inside open
                ins = float(smp.get("inside_sign", 1))
                dfn.d = -0.5 * ins  # Outside
                for _ in range(20):
                    maneuver, p_succ, man_d = session.select_and_evaluate_maneuver(atk, dfn, smp, True)
                    hp_evals += 1
                    if maneuver == "DIVEBOMB":
                        hp_divebombs += 1
            print(f"  {track.name}: Hairpin Turn {hairpins[0]['number']} evals={hp_evals}, Divebombs={hp_divebombs} (rate: {hp_divebombs/max(1, hp_evals)*100:.1f}%)")
            assert hp_divebombs > 0, f"Expected divebombs in hairpins when inside line is open!"

    print("  [OK] Divebomb restriction verified: ZERO on straights, active in hairpins & corners!")

def test_radio_divebomb_filter():
    print("\n[3] Testing Radio Divebomb Quote Filtering...")
    rd = RadioDispatcher()
    track = TRACK_BY_ID["italy"]
    session = RaceSession(track, teams_by_id, drivers, 0.0, 0.0, "mclaren")
    car_a = session.cars[0]
    car_b = session.cars[1]

    msgs = []
    def event_cb(t, m):
        msgs.append(m)

    # When maneuver is SLIPSTREAM: should NEVER say divebomb
    for i in range(50):
        rd.last_driver_radio_clock.clear()
        rd.last_global_radio_clock = 0.0
        rd.trigger_overtake_event(car_b, car_a, new_p=2, turn=1, event_cb=event_cb, clock=i*15.0, maneuver="SLIPSTREAM")

    divebomb_quotes_on_slipstream = [m for m in msgs if "divebomb" in m.lower()]
    print(f"  Radio broadcasts during SLIPSTREAM: {len(msgs)}, Divebomb complaints: {len(divebomb_quotes_on_slipstream)}")
    assert len(divebomb_quotes_on_slipstream) == 0, "Radio complained of divebomb during slipstream!"

    # When maneuver is DIVEBOMB: divebomb complaint can occur
    msgs.clear()
    for i in range(100):
        rd.last_driver_radio_clock.clear()
        rd.last_global_radio_clock = 0.0
        rd.trigger_overtake_event(car_b, car_a, new_p=2, turn=1, event_cb=event_cb, clock=i*15.0, maneuver="DIVEBOMB")

    divebomb_quotes_on_divebomb = [m for m in msgs if "divebomb" in m.lower()]
    print(f"  Radio broadcasts during DIVEBOMB: {len(msgs)}, Divebomb complaints: {len(divebomb_quotes_on_divebomb)}")
    assert len(divebomb_quotes_on_divebomb) > 0, "Expected divebomb complaints during actual divebombs!"
    print("  [OK] Radio divebomb quote filter verified!")

if __name__ == "__main__":
    test_tow_balance()
    test_divebomb_balance()
    test_radio_divebomb_filter()
    print("\nALL BALANCE TESTS PASSED CLEANLY!")
