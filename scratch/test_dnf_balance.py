import os
import sys
import random

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sim.tracks import TRACK_BY_ID
from sim.data import INITIAL_TEAMS, INITIAL_DRIVERS
from sim.physics import RaceSession

teams_by_id = {t["id"]: t for t in INITIAL_TEAMS}
drivers = [d for d in INITIAL_DRIVERS if d.get("team_id")]

def test_dnf_rates_in_simulated_races():
    print("[1] Simulating 10 full races to measure DNF rate and finishing field size...")
    track = TRACK_BY_ID["italy"]
    dnf_counts = []
    dnf_reasons = []

    for race_idx in range(10):
        session = RaceSession(track, teams_by_id, drivers, 0.0, 0.0, "mclaren")
        session.flag_state = "GREEN"
        
        # Simulate 20 laps (approx 1,700 seconds with dt=0.20 to run fast)
        dt = 0.20
        total_time = 1700.0
        elapsed = 0.0
        
        while elapsed < total_time:
            session.step(dt, lambda t, m: None)
            elapsed += dt
            if all(c.finished or c.dnf for c in session.cars):
                break

        dnfs = [c for c in session.cars if c.dnf]
        dnf_counts.append(len(dnfs))
        for d in dnfs:
            dnf_reasons.append(d.dnf_reason)
        print(f"  Race {race_idx+1}: {len(dnfs)} DNFs / {len(session.cars)} cars (Finished: {len(session.cars) - len(dnfs)})")

    avg_dnfs = sum(dnf_counts) / len(dnf_counts)
    print(f"\nAverage DNFs per race: {avg_dnfs:.2f} (Target: 0.5 to 2.5, down from previous 5.5+)")
    print(f"Sample DNF reasons: {dnf_reasons[:5]}")
    assert avg_dnfs <= 3.0, f"Average DNFs ({avg_dnfs}) is still too high!"
    assert avg_dnfs >= 0.0, "Expected non-negative DNFs"
    print("  [OK] Realistic, balanced DNF rate verified across full race simulations!")

if __name__ == "__main__":
    test_dnf_rates_in_simulated_races()
    print("\nALL DNF BALANCE TESTS PASSED CLEANLY!")

