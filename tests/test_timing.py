"""Timing splits share the lap clock and survive/reset at session boundaries."""
import unittest
from pathlib import Path
from unittest.mock import patch

from sim.championship import ChampionshipWorld
from sim.data import clone_initial_roster
from sim.physics import QualifyingSession, RaceSession
from sim.tracks import COMPILED_TRACKS


def ignore_event(*_):
    pass


class TimingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        teams, drivers = clone_initial_roster()
        cls.teams = {team['id']: team for team in teams}
        cls.drivers = [driver for driver in drivers if driver.get('team_id')]
        cls.track = COMPILED_TRACKS[0]

    def race(self, sprint=False):
        race = RaceSession(self.track, self.teams, self.drivers, 0, .1,
                           'williams', is_sprint=sprint)
        car = race.cars[0]
        car.total_dist = car.s = 0.0
        return race, car

    def advance_to(self, race, car, distance, clock):
        race.race_clock = clock
        race._advance_car_progress(car, distance - car.total_dist, False, ignore_event)

    def test_race_and_sprint_splits_sum_to_lap_and_keep_personal_bests(self):
        for sprint in (False, True):
            with self.subTest(sprint=sprint):
                race, car = self.race(sprint)
                length = self.track.length_m
                self.advance_to(race, car, length / 3, 31.111)
                self.assertEqual(car.current_sector_times, [31.111, None, None])
                self.assertIsNone(car.last_lap_time)
                self.advance_to(race, car, length * 2 / 3, 58.222)
                self.assertEqual(car.current_sector_times, [31.111, 27.111, None])
                self.advance_to(race, car, length, 90.555)
                self.assertEqual(car.last_sector_times, [31.111, 27.111, 32.333])
                self.assertEqual(car.current_sector_times, [None, None, None])
                self.assertAlmostEqual(sum(car.last_sector_times), car.last_lap_time, places=3)
                self.assertEqual(race.fastest_lap_time, car.last_lap_time)
                self.advance_to(race, car, length * 4 / 3, 120.555)
                self.advance_to(race, car, length * 5 / 3, 150.555)
                self.advance_to(race, car, length * 2, 185.555)
                self.assertEqual(car.last_lap_time, 95.0)
                self.assertEqual(car.best_lap_time, 90.555)
                self.assertEqual(car.best_sector_times, [30.0, 27.111, 32.333])

    def test_multiple_gates_interpolate_and_repeated_crossings_do_not_overwrite(self):
        race, car = self.race()
        race._current_dt = 90.0
        self.advance_to(race, car, self.track.length_m, 90.0)
        self.assertEqual(car.last_sector_times, [30.0, 30.0, 30.0])
        self.assertEqual(car.last_lap_time, 90.0)
        # A separation correction can move a car back over a gate. It must
        # not record that same split twice or count a second completed lap.
        car.total_dist -= 2
        race._current_dt = .05
        self.advance_to(race, car, self.track.length_m + 1, 90.05)
        self.assertEqual(car.laps_completed, 1)
        self.assertEqual(car.current_sector_times, [None, None, None])

    def test_grid_timing_line_is_not_a_completed_sector_or_lap(self):
        race, car = self.race()
        car.total_dist = -100
        self.advance_to(race, car, 1, 12.0)
        self.assertEqual(car.current_sector_times, [None, None, None])
        self.assertEqual(car.lap_start_time, 0.0)
        self.advance_to(race, car, self.track.length_m / 3, 40.0)
        self.assertEqual(car.current_sector_times, [40.0, None, None])

    def test_stationary_pit_time_is_included_in_the_sector(self):
        race, car = self.race()
        self.advance_to(race, car, self.track.length_m / 3, 30.0)
        car.in_pits = True
        car.pit_phase = 'STOPPED'
        car.pit_stop_timer = 20.0
        race.race_clock = 35.0
        race._step_pit_lane(car, False, 5.0, ignore_event)
        self.assertEqual(car.current_sector_times, [30.0, None, None])
        self.advance_to(race, car, self.track.length_m * 2 / 3, 65.0)
        self.assertEqual(car.current_sector_times, [30.0, 35.0, None])

    def test_finish_freezes_completed_lap_splits(self):
        race, car = self.race(sprint=True)
        race.total_laps = 1
        race._current_dt = 90.0
        self.advance_to(race, car, self.track.length_m, 90.0)
        self.assertTrue(car.finished)
        self.advance_to(race, car, self.track.length_m * 2, 180.0)
        self.assertEqual(car.last_sector_times, [30.0, 30.0, 30.0])
        self.assertEqual(car.laps_completed, 1)

    def test_qualifying_live_sectors_match_modeled_laps_and_stage_reset(self):
        for sprint in (False, True):
            with self.subTest(sprint=sprint):
                quali = QualifyingSession(self.track, self.teams, self.drivers, 0,
                                          is_sprint_quali=sprint)
                car = quali.cars[0]
                car.total_dist = self.track.length_m / 3 - .01
                car.s = car.total_dist
                quali.step(.05, ignore_event)
                self.assertIsNotNone(car.current_sector_times[0])
                self.assertIsNone(car.current_sector_times[1])
                car.total_dist = self.track.length_m - .01
                car.s = car.total_dist
                quali.stage_elapsed = 20
                quali.step(.05, ignore_event)
                self.assertTrue(all(t > 0 for t in car.last_sector_times))
                self.assertAlmostEqual(sum(car.last_sector_times), car.last_lap_time, places=3)
                quali._complete_current_stage(ignore_event)
                self.assertEqual(quali.stage_idx, 1)
                for advancing in (c for c in quali.cars if not c.eliminated):
                    self.assertIsNone(advancing.last_lap_time)
                    self.assertEqual(advancing.current_sector_times, [None, None, None])
                    self.assertEqual(advancing.last_sector_times, [None, None, None])
                    self.assertEqual(advancing.best_sector_times, [None, None, None])
                for eliminated in (c for c in quali.cars if c.eliminated):
                    self.assertAlmostEqual(sum(eliminated.last_sector_times),
                                           eliminated.last_lap_time, places=3)

    def test_live_payload_has_copied_sector_times_and_stage_specific_bests(self):
        with patch.object(ChampionshipWorld, '_load_state', return_value=False), \
             patch.object(ChampionshipWorld, '_save_state'):
            world = ChampionshipWorld(Path.cwd() / 'scratch' / 'unused_timing_save.json')
            world._start_qualifying()
            car, eliminated = world.quali_session.cars[:2]
            car.record_sector(0, 30.123)
            eliminated.record_sector(0, 29.0)
            eliminated.eliminated = True
            tick = world.build_live_tick_payload()
            row = next(c for c in tick['cars'] if c['id'] == car.driver_id)
            self.assertEqual(tick['sector_bests'], [30.123, None, None])
            self.assertEqual(row['sectors'], [30.123, None, None])
            self.assertEqual(row['best_sectors'], [30.123, None, None])
            self.assertEqual(row['last_sectors'], [None, None, None])
            car.current_sector_times[0] = 31.0
            self.assertEqual(row['sectors'][0], 30.123)


if __name__ == '__main__':
    unittest.main()
