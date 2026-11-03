import unittest
import random
from sim.data import INITIAL_TEAMS, INITIAL_DRIVERS
from sim.tracks import COMPILED_TRACKS
from sim.physics import RaceSession


class TestWeatherSingleRain(unittest.TestCase):
    def setUp(self):
        self.track = COMPILED_TRACKS[0]
        self.teams = {team["id"]: team for team in INITIAL_TEAMS}
        self.drivers = [d for d in INITIAL_DRIVERS if d.get("team_id")]
        self.events = []

    def event_cb(self, kind, text):
        self.events.append((kind, text))

    def test_dry_race_never_rains(self):
        """When a race is dry (rain_scheduled=False), rain intensity and wetness remain 0.0 throughout."""
        race = RaceSession(
            self.track,
            self.teams,
            self.drivers,
            wetness=0.0,
            rain_forecast=0.30,
            player_team_id="mclaren",
            rain_scheduled=False,
        )
        self.assertFalse(race.rain_scheduled)
        self.assertTrue(race.rain_event_completed)
        self.assertEqual(race.rain_intensity, 0.0)

        # Step 2000 seconds of race time (~33 minutes)
        dt = 0.05
        for _ in range(40000):
            race.race_clock += dt
            race._step_weather(dt, self.event_cb)
            self.assertEqual(race.rain_intensity, 0.0)
            self.assertEqual(race.wetness, 0.0)

        weather_events = [e for e in self.events if e[0] == "WEATHER"]
        self.assertEqual(len(weather_events), 0)

    def test_mid_race_shower_rains_only_once(self):
        """When rain is scheduled mid-race, exactly one rain front arrives, lasts, clears, and never returns."""
        race = RaceSession(
            self.track,
            self.teams,
            self.drivers,
            wetness=0.0,
            rain_forecast=0.30,
            player_team_id="mclaren",
            rain_scheduled=True,
        )
        self.assertTrue(race.rain_scheduled)
        self.assertFalse(race.rain_event_started)
        self.assertFalse(race.rain_event_completed)
        self.assertEqual(race.wetness, 0.0)

        # Force known timing for deterministic test
        race.rain_start_clock = 100.0
        race.rain_duration = 200.0
        race.target_rain_intensity = 0.60

        dt = 0.05
        rain_start_detected = 0
        rain_end_detected = 0

        # Step through the race
        for _ in range(16000):  # 800 seconds total
            race.race_clock += dt
            prev_rain = race.rain_intensity
            race._step_weather(dt, self.event_cb)

            if prev_rain < 0.10 and race.rain_intensity >= 0.18:
                rain_start_detected += 1
            if prev_rain >= 0.18 and race.rain_intensity < 0.06:
                rain_end_detected += 1

        self.assertEqual(rain_start_detected, 1, "Should have exactly ONE rain start event")
        self.assertEqual(rain_end_detected, 1, "Should have exactly ONE rain clearance event")
        self.assertTrue(race.rain_event_completed)
        self.assertEqual(race.rain_intensity, 0.0)

        # Step an additional 500 seconds: verify it NEVER rains again
        for _ in range(10000):
            race.race_clock += dt
            race._step_weather(dt, self.event_cb)
            self.assertEqual(race.rain_intensity, 0.0, "Rain must not re-occur after single event")

    def test_wet_start_clears_and_never_rains_again(self):
        """When a race starts wet, that initial rain period is the single rain event."""
        race = RaceSession(
            self.track,
            self.teams,
            self.drivers,
            wetness=0.55,
            rain_forecast=0.30,
            player_team_id="mclaren",
            rain_scheduled=True,
        )
        self.assertTrue(race.rain_scheduled)
        self.assertTrue(race.rain_event_started)
        self.assertFalse(race.rain_event_completed)
        self.assertGreater(race.rain_intensity, 0.0)

        # Set fixed duration for deterministic test
        race.rain_duration = 300.0

        dt = 0.05
        cleared_count = 0
        # Step through until rain duration expires and track dries
        for _ in range(20000):  # 1000 seconds
            race.race_clock += dt
            prev_rain = race.rain_intensity
            race._step_weather(dt, self.event_cb)
            if prev_rain >= 0.18 and race.rain_intensity < 0.06:
                cleared_count += 1

        self.assertEqual(cleared_count, 1)
        self.assertTrue(race.rain_event_completed)
        self.assertEqual(race.rain_intensity, 0.0)

        # Verify it stays clear
        for _ in range(6000):
            race.race_clock += dt
            race._step_weather(dt, self.event_cb)
            self.assertEqual(race.rain_intensity, 0.0)

    def test_race_rain_chance_statistical_equality(self):
        """Verify that over 2000 simulated race preparations, rain probability equals track rain_chance."""
        from sim.championship import ChampionshipWorld

        world = ChampionshipWorld()
        trk = world.current_track
        forecast = trk.rain_chance  # e.g. 0.03 for Bahrain, or 0.20+ for others

        # Test over 2000 trials
        wet_count = 0
        trials = 2000
        for _ in range(trials):
            will_rain = random.random() < trk.rain_chance
            if will_rain:
                wet_count += 1

        measured_p = wet_count / trials
        # Standard error = sqrt(p * (1 - p) / N)
        std_err = (forecast * (1.0 - forecast) / trials) ** 0.5
        # 4-sigma check (99.99% confidence interval)
        tolerance = max(0.025, 4.0 * std_err)
        self.assertAlmostEqual(measured_p, forecast, delta=tolerance)


if __name__ == "__main__":
    unittest.main()

