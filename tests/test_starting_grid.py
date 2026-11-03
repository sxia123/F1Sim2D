import math
import unittest
from pathlib import Path
from unittest.mock import patch

from sim.championship import ChampionshipWorld
from sim.data import clone_initial_roster
from sim.physics import RaceSession, _sat_obb_penetration
from sim.tracks import COMPILED_TRACKS
from sim.car_geometry import CAR_HALF_LENGTH, CAR_HALF_WIDTH


class StartingGridTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        teams, drivers = clone_initial_roster()
        cls.teams = {t['id']:t for t in teams}
        cls.drivers = list(reversed([d for d in drivers if d.get('team_id')]))

    def test_all_grids_match_the_cars_and_fit_the_start_straight(self):
        for track in COMPILED_TRACKS:
            for sprint in (False, True):
                with self.subTest(track=track.id,sprint=sprint):
                    race = RaceSession(track,self.teams,self.drivers,0,.1,'williams',is_sprint=sprint)
                    self.assertEqual(len(race.cars),22)
                    # Real grids follow the local roadway, including Monaco's
                    # gentle bend and the rear of the Las Vegas grid. Do not
                    # move the published start line to satisfy a straightness fit.
                    self.assertEqual(track.grid_spacing_m,8.0)
                    self.assertAlmostEqual(track.start_line_s,track.layout['start_line_fraction']*track.length_m)
                    for i,(car,box) in enumerate(zip(race.cars,track.grid_boxes)):
                        self.assertEqual(car.driver_id,self.drivers[i]['id'])
                        self.assertEqual(car.grid_pos,i+1)
                        self.assertAlmostEqual(track.start_line_s-car.total_dist,10+i*track.grid_spacing_m)
                        self.assertLess(math.hypot(car.x-box['x'],car.y-box['y']),.02)
                        self.assertLess(abs(car.heading-box['heading']),.001)
                        self.assertEqual(car.d,box['d'])
                        point=track.sample(car.s)
                        self.assertAlmostEqual(box['heading'],math.atan2(point['ty'],point['tx']))
                        self.assertEqual(car.laps_completed,0)
                        # All four body corners remain inside the road ribbon.
                        for x in (-CAR_HALF_LENGTH,CAR_HALF_LENGTH):
                            for y in (-CAR_HALF_WIDTH,CAR_HALF_WIDTH):
                                px=car.x+x*math.cos(car.heading)-y*math.sin(car.heading)
                                py=car.y+x*math.sin(car.heading)+y*math.cos(car.heading)
                                nearby=[track.sample(car.s+j) for j in range(-4,5)]
                                distance=min(math.hypot(px-p['x'],py-p['y']) for p in nearby)
                                self.assertLess(distance,track.width_px_at(car.s)/2)
                    for i,car in enumerate(race.cars):
                        for other in race.cars[i+1:]:
                            self.assertIsNone(_sat_obb_penetration(car,other))
                    before=[(c.s,c.x,c.y,c.heading) for c in race.cars]
                    for _ in range(20):race.step(.05,lambda *_:None)
                    self.assertEqual(before,[(c.s,c.x,c.y,c.heading) for c in race.cars])

    def test_grid_walk_and_lights_reuse_the_qualifying_order(self):
        # Mock persistence so this lifecycle test never reads or changes a career.
        with patch.object(ChampionshipWorld,'_load_state',return_value=False), \
             patch.object(ChampionshipWorld,'_save_state'):
            world=ChampionshipWorld(Path.cwd()/'scratch'/'unused_grid_test_save.json')
            world._start_qualifying()
            world.quali_session.standings.reverse()
            order=[c.driver_id for c in world.quali_session.standings]
            world._finish_qualifying_to_grid()
            prepared=world.race_session
            walk=world.build_live_tick_payload()
            self.assertEqual(world.phase,'GRID_WALK')
            self.assertEqual([c['id'] for c in walk['cars']],order)
            self.assertTrue(all(c['kph']==0 for c in walk['cars']))
            coords=[(c['x'],c['y'],c['h']) for c in walk['cars']]
            world._step_sub(world.phase_timer+.01)
            lights=world.build_live_tick_payload()
            self.assertEqual(world.phase,'RACE')
            self.assertIs(world.race_session,prepared)
            self.assertEqual([c['id'] for c in lights['cars']],order)
            self.assertEqual(coords,[(c['x'],c['y'],c['h']) for c in lights['cars']])

    def test_crossing_timing_line_does_not_restart_first_lap_clock(self):
        track=COMPILED_TRACKS[0]
        race=RaceSession(track,self.teams,self.drivers,0,.1,'williams')
        car=race.cars[-1]
        self.assertLess(car.total_dist,0)
        race.race_clock=12
        race._advance_car_progress(car,-car.total_dist+1,False,lambda *_:None)
        self.assertTrue(car.crossed_start_line)
        self.assertEqual(car.lap_start_time,0)
        self.assertEqual(car.laps_completed,0)


if __name__=='__main__':unittest.main()
