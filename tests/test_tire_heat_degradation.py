import unittest
from sim.data import (
    INITIAL_TEAMS,
    INITIAL_DRIVERS,
    TIRE_COMPOUNDS,
    tire_thermal_wear_mult,
    tire_thermal_grip_mult,
    tire_temp_status,
)
from sim.tracks import COMPILED_TRACKS
from sim.physics import RaceSession


class TestTireHeatDegradation(unittest.TestCase):
    def setUp(self):
        self.track = COMPILED_TRACKS[0]
        self.teams = {team["id"]: team for team in INITIAL_TEAMS}
        self.drivers = [d for d in INITIAL_DRIVERS if d.get("team_id")]

    def test_optimal_temp_window_nominal_wear_and_grip(self):
        """Within the compound's optimal operating temperature window, wear and grip multipliers are nominal (1.0)."""
        for comp_name, spec in TIRE_COMPOUNDS.items():
            t_min = spec["opt_temp_min"]
            t_max = spec["opt_temp_max"]
            t_mid = (t_min + t_max) / 2.0

            # At mid, min, max
            for t in (t_min, t_mid, t_max):
                wear_mult = tire_thermal_wear_mult(comp_name, t)
                grip_mult = tire_thermal_grip_mult(comp_name, t)
                self.assertEqual(wear_mult, 1.0, f"{comp_name} at {t}C should have 1.0 wear multiplier")
                self.assertEqual(grip_mult, 1.0, f"{comp_name} at {t}C should have 1.0 grip multiplier")
                self.assertEqual(tire_temp_status(comp_name, t), "OPTIMAL")

    def test_overheating_thermal_degradation_wear_curve(self):
        """As tire temperature exceeds the optimal window, wear multiplier escalates non-linearly (blistering)."""
        soft_max = TIRE_COMPOUNDS["SOFT"]["opt_temp_max"]  # 106.0

        w_nominal = tire_thermal_wear_mult("SOFT", soft_max)
        w_plus10 = tire_thermal_wear_mult("SOFT", soft_max + 10.0)
        w_plus20 = tire_thermal_wear_mult("SOFT", soft_max + 20.0)

        self.assertEqual(w_nominal, 1.0)
        self.assertGreater(w_plus10, 1.45, "10C overheat on Softs should increase degradation by at least 45%")
        self.assertGreater(w_plus20, 2.20, "20C overheat on Softs should more than double degradation (blistering)")
        self.assertGreater(w_plus20, w_plus10, "Thermal wear curve must be monotonically increasing")

        # Hard compound is more resilient to overheating than Soft compound
        hard_max = TIRE_COMPOUNDS["HARD"]["opt_temp_max"]
        w_hard_plus10 = tire_thermal_wear_mult("HARD", hard_max + 10.0)
        self.assertLess(w_hard_plus10, w_plus10, "Hard compound should have lower overheat degradation than Soft")

    def test_overheating_thermal_grip_fade(self):
        """Overheating causes surface rubber to grease over, resulting in thermal grip loss."""
        med_max = TIRE_COMPOUNDS["MEDIUM"]["opt_temp_max"]  # 113.0

        g_nominal = tire_thermal_grip_mult("MEDIUM", med_max)
        g_plus10 = tire_thermal_grip_mult("MEDIUM", med_max + 10.0)
        g_plus20 = tire_thermal_grip_mult("MEDIUM", med_max + 20.0)

        self.assertEqual(g_nominal, 1.0)
        self.assertLess(g_plus10, 0.96, "10C overheat should cause ~4-6% grip loss")
        self.assertLess(g_plus20, g_plus10, "20C overheat should cause further grip loss")
        self.assertGreaterEqual(g_plus20, 0.85, "Grip fade is bounded at 0.85")

    def test_cold_tire_graining_and_grip_reduction(self):
        """Cold tires have reduced grip and suffer from cold shear graining."""
        hard_min = TIRE_COMPOUNDS["HARD"]["opt_temp_min"]  # 100.0

        # Cold out-lap at 75C (25C below optimal)
        w_cold = tire_thermal_wear_mult("HARD", hard_min - 25.0)
        g_cold = tire_thermal_grip_mult("HARD", hard_min - 25.0)

        self.assertGreater(w_cold, 1.15, "Cold tires under stress experience graining wear")
        self.assertLess(g_cold, 0.88, "Cold tires have reduced chemical grip")

    def test_dynamic_thermal_evolution_in_race_session(self):
        """In a dynamic simulation step, pushing generates higher tire heat and degradation than conserving on the same compound."""
        race = RaceSession(
            self.track,
            self.teams,
            self.drivers,
            wetness=0.0,
            rain_forecast=0.0,
            player_team_id="mclaren",
            starting_compounds={self.drivers[0]["id"]: "MEDIUM", self.drivers[1]["id"]: "MEDIUM"},
            rain_scheduled=False,
        )

        car_push = race.cars[0]
        car_conserve = race.cars[1]

        car_push.auto_strategy = False
        car_conserve.auto_strategy = False
        car_push.tire_wear = 0.01
        car_conserve.tire_wear = 0.01

        car_push.pace_mode = "ATTACK"
        car_conserve.pace_mode = "CONSERVE"

        # Step 150 seconds of simulation
        dt = 0.05
        for _ in range(3000):
            race.race_clock += dt
            race.step(dt, lambda *args: None)

        self.assertGreater(
            car_push.tire_temp,
            car_conserve.tire_temp,
            "ATTACK pace mode must produce higher tire temperature than CONSERVE",
        )
        self.assertGreater(
            car_push.tire_wear,
            car_conserve.tire_wear,
            "ATTACK pace with thermal degradation must yield higher wear than CONSERVE",
        )

    def test_wet_compound_dry_overheat_spike(self):
        """Intermediates running on dry track experience severe thermal overheat compared to wet conditions."""
        norris = next(d for d in self.drivers if d["id"] == "norris")
        # Race 1: Dry track with Inters
        race_dry = RaceSession(
            self.track,
            self.teams,
            [norris],
            wetness=0.0,
            rain_forecast=0.0,
            player_team_id="mclaren",
            starting_compounds={"norris": "INTER"},
            rain_scheduled=False,
        )
        # Race 2: Wet track with Inters
        race_wet = RaceSession(
            self.track,
            self.teams,
            [norris],
            wetness=0.35,
            rain_forecast=0.35,
            player_team_id="mclaren",
            starting_compounds={"norris": "INTER"},
            rain_scheduled=True,
        )

        dt = 0.05
        for _ in range(2000):
            race_dry.race_clock += dt
            race_dry.step(dt, lambda *args: None)
            race_wet.race_clock += dt
            race_wet.step(dt, lambda *args: None)

        dry_car = race_dry.cars[0]
        wet_car = race_wet.cars[0]

        self.assertGreater(
            dry_car.tire_temp,
            wet_car.tire_temp + 20.0,
            "Inters on dry asphalt must run significantly hotter than on wet track",
        )
        self.assertGreater(
            dry_car.tire_wear,
            wet_car.tire_wear,
            "Inters on dry asphalt must experience severe thermal degradation",
        )


    def test_pace_mode_heating_derived_from_driving_not_flat_step(self):
        """Pace mode heating is derived from physical driving work (cornering G & braking), not an instant flat input step."""
        race = RaceSession(
            self.track,
            self.teams,
            self.drivers[:2],
            wetness=0.0,
            rain_forecast=0.0,
            player_team_id="mclaren",
            rain_scheduled=False,
        )
        car_std = race.cars[0]
        car_attack = race.cars[1]
        car_std.auto_strategy = False
        car_attack.auto_strategy = False

        car_std.pace_mode = "BALANCED"
        car_attack.pace_mode = "ATTACK"

        # Position both cars on a long straight traveling at 80 m/s
        for c in (car_std, car_attack):
            c.s = 200.0  # Main straight
            c.v = 80.0
            c.tire_temp = 98.0
            c.braking = False

        # Run for 2 seconds (40 physics ticks) on the straight
        dt = 0.05
        for _ in range(40):
            race.race_clock += dt
            race.step(dt, lambda *args: None)

        # On the straight, because there is no cornering scrub or hard braking,
        # ATTACK mode does NOT produce an immediate artificial 13C temperature spike
        temp_diff = car_attack.tire_temp - car_std.tire_temp
        self.assertLess(
            temp_diff,
            3.0,
            f"On a straight, ATTACK should not instantly spike temperature by a flat offset (diff was {temp_diff:.2f}C)",
        )


if __name__ == "__main__":
    unittest.main()
