"""Geometry integration checks against the baked reference-map routes."""
import math
import random
import unittest

from sim.data import clone_initial_roster
from sim.physics import RaceSession, enforce_2d_car_separation, _sat_obb_penetration
from sim.tracks import COMPILED_TRACKS
from sim.track_geometry import LAYOUTS, WORLD_UNITS_PER_M


class TrackGeometryTests(unittest.TestCase):
    def test_reference_routes_and_width_scale(self):
        self.assertEqual({t.id for t in COMPILED_TRACKS}, set(LAYOUTS))
        for t in COMPILED_TRACKS:
            with self.subTest(track=t.id):
                self.assertAlmostEqual(t.track_width_px/t.track_width_m, WORLD_UNITS_PER_M)
                self.assertAlmostEqual(t.px_per_m, WORLD_UNITS_PER_M)
                for p in t.stations+t.pit_stations:
                    self.assertTrue(all(math.isfinite(v) for v in p.values()))
                self.assertGreater(t.pit_span_m, 0)
                self.assertLess(t.pit_span_m, t.length_m*.5)
                self.assertEqual(len(t.pit_garages),11)
                for g in t.pit_garages:
                    self.assertLess((g['s_m']-t.pit_entry_s)%t.length_m,t.pit_span_m)
                self.assertEqual(t.to_client_payload()['pit_garages'],t.pit_garages)

    def test_pit_joins_share_racing_coordinates(self):
        for t in COMPILED_TRACKS:
            with self.subTest(track=t.id):
                a=t.sample(t.pit_entry_s);b=t.sample_pit(t.pit_entry_s)
                self.assertLess(math.hypot(a['x']-b['x'],a['y']-b['y']),.01)
                a=t.sample(t.pit_exit_s);b=t.sample_pit(t.pit_exit_s)
                offset=t.lateral_to_px(.76*t.pit_side,t.pit_exit_s)
                self.assertLess(math.hypot(a['x']+a['nx']*offset-b['x'],a['y']+a['ny']*offset-b['y']),.01)

    def test_complete_pit_visits_on_every_circuit(self):
        teams,drivers=clone_initial_roster()
        teams={t['id']:t for t in teams}
        driver=next(d for d in drivers if d.get('team_id'))
        for t in COMPILED_TRACKS:
            with self.subTest(track=t.id):
                random.seed(7)
                race=RaceSession(t,teams,[driver],0,.1,driver['team_id'])
                race.flag_state='GREEN';race.lights_out=True
                c=race.cars[0]
                c.s=t.pit_entry_s-1;c.total_dist=c.s;c.v=30
                c.box_this_lap=True;c.auto_strategy=False;c.d=.42*t.pit_side
                race._update_xy(c)
                before=(c.x,c.y)
                race._step_car(c,None,c,False,.05,lambda *_:None)
                race._update_xy(c)
                self.assertTrue(c.in_pits)
                self.assertLess(math.dist(before,(c.x,c.y)),15)
                max_jump=0
                for _ in range(5000):
                    if not c.in_pits:break
                    before=(c.x,c.y)
                    race._step_pit_lane(c,False,.05,lambda *_:None)
                    race._update_xy(c)
                    max_jump=max(max_jump,math.dist(before,(c.x,c.y)))
                    race.race_clock+=.05
                self.assertFalse(c.in_pits,'Pit visit did not complete')
                self.assertEqual(c.pit_stops,1)
                self.assertTrue(c.pit_blend_active)
                self.assertLess(max_jump,20,'Discontinuous pit movement')
                self.assertAlmostEqual(c.d,.76*t.pit_side)

    def test_shanghai_pit_split_is_after_turn_15_and_not_on_the_back_straight(self):
        t=next(t for t in COMPILED_TRACKS if t.id=='china')
        turns={c['number']:c['fraction'] for c in t.layout['corner_markers']}
        self.assertGreater(t.pit_entry_s/t.length_m,turns[15])
        self.assertLess(t.pit_entry_s/t.length_m,turns[16])
        self.assertIn('107371147',t.layout['pit_reference'])
        back_straight=t.stations[int(.65*t.NUM_STATIONS):int(.875*t.NUM_STATIONS)]
        distance=min(math.hypot(p['x']-s['x'],p['y']-s['y'])
                     for p in t.pit_stations[:90] for s in back_straight)
        self.assertGreater(distance,t.track_width_px,'Pit entry must not cut across the back straight')
        entry=t.sample(t.pit_entry_s);pit=t.pit_stations[0]
        self.assertGreater(entry['tx']*pit['tx']+entry['ty']*pit['ty'],.94)

        teams,drivers=clone_initial_roster()
        driver=next(d for d in drivers if d.get('team_id'))
        race=RaceSession(t,{team['id']:team for team in teams},[driver],0,.1,driver['team_id'])
        race.flag_state='GREEN';race.lights_out=True
        car=race.cars[0]
        car.s=t.length_m*.80325-1;car.total_dist=car.s;car.v=45
        car.box_this_lap=True;car.auto_strategy=False
        race._update_xy(car)
        race._step_car(car,None,car,False,.1,lambda *_:None)
        self.assertFalse(car.in_pits,'A box call must not take the old back-straight shortcut')

    def test_yas_tunnel_crossing_does_not_move_surface_traffic(self):
        t=next(t for t in COMPILED_TRACKS if t.id=='abudhabi')
        teams,drivers=clone_initial_roster()
        drivers=[d for d in drivers if d.get('team_id')][:2]
        race=RaceSession(t,{v['id']:v for v in teams},drivers,0,.1,'williams')
        pit,surface=race.cars
        # The tunnel is traced from the geographic way. Its geometric midpoint
        # need not be the crossing; select the actual closest surface crossing.
        lo,hi=t.pit_tunnel_u
        def distance(u):
            p=t.sample_pit((t.pit_entry_s+u*t.pit_span_m)%t.length_m)
            return min((p['x']-s['x'])**2+(p['y']-s['y'])**2 for s in t.stations)
        u=min((lo+(hi-lo)*i/100 for i in range(101)),key=distance)
        pit.s=(t.pit_entry_s+u*t.pit_span_m)%t.length_m
        pit.total_dist=pit.s;pit.in_pits=True;pit.pit_phase='EXIT';pit.pit_apron=0
        race._update_xy(pit)
        k=min(range(t.NUM_STATIONS),key=lambda k:(t.stations[k]['x']-pit.x)**2+(t.stations[k]['y']-pit.y)**2)
        surface.s=k*t.ds_m;surface.total_dist=surface.s;surface.d=0
        race._update_xy(surface)
        self.assertIsNotNone(_sat_obb_penetration(pit,surface),'Test must overlap in the 2D projection')
        before=(surface.s,surface.d,pit.s)
        enforce_2d_car_separation(t,race.cars,True,race._update_xy)
        self.assertEqual((surface.s,surface.d,pit.s),before)


if __name__=='__main__':unittest.main()
