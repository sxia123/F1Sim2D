import unittest
from sim.tracks import COMPILED_TRACKS
from sim.data import INITIAL_TEAMS, INITIAL_DRIVERS
from sim.physics import RaceSession, CarState

class TestBatteryDrain(unittest.TestCase):
    def test_overtake_battery_drain(self):
        trk = COMPILED_TRACKS[0]
        tmap = {t["id"]: t for t in INITIAL_TEAMS}
        active_drivers = [d for d in INITIAL_DRIVERS if d.get("team_id")][:4]
        
        session = RaceSession(trk, tmap, active_drivers, 0.0, 0.0, "mercedes", is_sprint=False)
        car = session.cars[0]
        car.battery_mj = 4.0
        car.overtake_eligible = True
        car.ers_mode = "OVERTAKE"
        car.s = trk.length_m * 0.05  # on main straight
        car.v = 70.0
        
        # Step simulation by 2.0 seconds
        dt = 0.05
        steps = int(2.0 / dt)
        initial_battery = car.battery_mj
        for _ in range(steps):
            session.step(dt, lambda k, m: None)
            
        final_battery = car.battery_mj
        drain = initial_battery - final_battery
        print(f"2-second Overtake drain: {drain:.2f} MJ (from {initial_battery:.2f} to {final_battery:.2f} MJ)")
        self.assertGreater(drain, 1.0, f"Expected >1.0 MJ drain in 2 seconds of high power, got {drain:.2f}")

if __name__ == "__main__":
    unittest.main()

