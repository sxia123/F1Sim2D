"""Scenery regression checks: continuous roads, footprints, geography and isolation."""
import copy
import json
import math
import random
from types import SimpleNamespace
import unittest

from sim.tracks import COMPILED_TRACKS
from sim.track_environment import (
    _ENV_CACHE, _SCENERY, CIRCUIT_THEMES, ROAD_CLEARANCE, RoadClearance,
    coast_water, get_track_environment, inside_feature, rectangle,
)


class EnvironmentTests(unittest.TestCase):
    def test_continuous_segments_local_widths_pits_and_closing_segment(self):
        t = SimpleNamespace(track_width_px=20, pit_width_px=28,
            stations=[dict(x=0,y=0,width_px=20),dict(x=600,y=0,width_px=100),
                      dict(x=600,y=600,width_px=20)],
            pit_stations=[dict(x=0,y=150),dict(x=600,y=150)])
        road = RoadClearance(t)
        # These positions lie between widely separated stations.
        self.assertFalse(road.circle_safe(250,20,12))
        self.assertFalse(road.circle_safe(580,250,8))
        self.assertFalse(road.circle_safe(280,280,8))  # Closing diagonal.
        self.assertFalse(road.circle_safe(260,170,8))  # Independent pit road.
        self.assertFalse(road.polygon_safe([rectangle(250,70,180,90,.45)]))
        self.assertFalse(road.polygon_safe([rectangle(300,300,1000,1000,0)]))
        self.assertTrue(road.circle_safe(-150,300,30))

    def test_full_rendered_object_footprints_clear_every_road(self):
        for t in COMPILED_TRACKS:
            with self.subTest(track=t.id):
                e = get_track_environment(t)
                road = RoadClearance(t)
                for tree in e['trees']:
                    self.assertTrue(road.circle_safe(tree['x'],tree['y'],tree['r']*1.35+2.8))
                for detail in e['details']:
                    self.assertTrue(road.circle_safe(detail['x'],detail['y'],detail['r']+2.8))
                for f in e['buildings']+e['grandstands']:
                    self.assertTrue(road.polygon_safe(f['paths'],padding=8.8), f['id'])
                for yacht in e['yachts']:
                    self.assertTrue(road.circle_safe(yacht['x'],yacht['y'],yacht['len']/2+7.8))
                    self.assertTrue(any(all(inside_feature(*p,w['paths']) for p in
                        rectangle(yacht['x'],yacht['y'],yacht['len'],yacht['width'],yacht['angle']))
                        for w in e['water_bodies']))

    def test_geographic_coverage_and_regional_character(self):
        self.assertEqual(set(_SCENERY), {t.id for t in COMPILED_TRACKS})
        for t in COMPILED_TRACKS:
            e = get_track_environment(t)
            self.assertGreater(len(e['terrain']), 3, t.id)
            self.assertGreater(len(e['trees'])+len(e['buildings'])+len(e['details']),100,t.id)
            self.assertTrue(e['attribution'])
            self.assertEqual(e['theme'],CIRCUIT_THEMES[t.id])
        by_id = {t.id:get_track_environment(t) for t in COMPILED_TRACKS}
        self.assertTrue(any('albert' in w.get('name','').lower() for w in by_id['australia']['water_bodies']))
        self.assertGreater(len(by_id['italy']['trees']),500)
        self.assertGreater(len(by_id['belgium']['trees']),500)
        self.assertGreater(len(by_id['monaco']['buildings']),100)
        self.assertTrue(any(w.get('coastal') for w in by_id['monaco']['water_bodies']))
        # No imaginary infield Interlagos lake or invented street-circuit gravel traps.
        self.assertFalse(any(w.get('name')=='Lagoa de Interlagos' for w in by_id['brazil']['water_bodies']))
        self.assertFalse(by_id['monaco']['gravel_traps'])
        for tid in ('bahrain','qatar'):
            self.assertTrue(all(t['type']=='palm' for t in by_id[tid]['trees']))
        for t in COMPILED_TRACKS:
            for water in by_id[t.id]['water_bodies']:
                if water.get('coastal'):
                    self.assertLess(sum(inside_feature(p['x'],p['y'],water['paths']) for p in t.stations),5,
                                    f'{t.id}: coastline flooded the circuit')

    def test_determinism_cache_invalidation_and_no_race_mutation(self):
        t = COMPILED_TRACKS[0]
        before = copy.deepcopy((t.stations,t.pit_stations,t.pit_garages,t.bounds))
        random.seed(190)
        rng_state = random.getstate()
        original = json.dumps(get_track_environment(t),sort_keys=True)
        _ENV_CACHE.pop(t,None)
        self.assertEqual(original,json.dumps(get_track_environment(t),sort_keys=True))
        self.assertEqual(rng_state,random.getstate())
        self.assertEqual(before,(t.stations,t.pit_stations,t.pit_garages,t.bounds))
        clone = copy.copy(t)
        clone.stations = [dict(p,width_px=p['width_px']+20) for p in t.stations]
        self.assertIsNot(get_track_environment(t),get_track_environment(clone))
        old = get_track_environment(clone)
        clone.pit_width_px += 20
        self.assertIsNot(old,get_track_environment(clone))

    def test_jeddah_has_a_full_sea_view_and_clear_waterfront_details(self):
        t=next(t for t in COMPILED_TRACKS if t.id=='saudi')
        e=get_track_environment(t)
        road=RoadClearance(t)
        coast=next(w for w in e['water_bodies'] if w.get('coastal'))
        y=(t.bounds['min_y']+t.bounds['max_y'])/2
        self.assertTrue(inside_feature(t.bounds['min_x']-4000,y,coast['paths']))
        self.assertFalse(inside_feature(t.bounds['max_x']+4000,y,coast['paths']))
        self.assertGreater(e['bounds'][2]-e['bounds'][0],(t.bounds['max_y']-t.bounds['min_y'])*2)
        self.assertGreater(len(e['buildings']),30)
        self.assertGreater(len(e['routes']),200)
        self.assertGreater(len(e['lights']),60)
        self.assertTrue(any(r['kind']=='pier' for r in e['routes']))
        self.assertTrue(all(p['type']=='palm' for p in e['trees']))
        for route in e['routes']:
            for a,b in zip(route['points'],route['points'][1:]):
                self.assertTrue(road.circle_safe((a[0]+b[0])/2,(a[1]+b[1])/2,route['width']/2+4))
        for light in e['lights']:
            self.assertTrue(road.circle_safe(light['x'],light['y'],light['r']+2.8))

    def test_directed_coastline_closes_on_boundary_and_holes_stay_dry(self):
        # Screen-north coastline, land west and water east.
        water = coast_water([[[40,150],[40,60]],[[40,60],[40,-50]]],[0,0,100,100])
        self.assertTrue(any(inside_feature(70,50,[p]) for p in water))
        self.assertFalse(any(inside_feature(20,50,[p]) for p in water))
        self.assertFalse(coast_water([[[20,20],[40,40]]],[0,0,100,100]))
        # A peninsula leaves and re-enters the viewport. Its water faces must
        # connect through perimeter endpoints rather than flood each other.
        water=coast_water([[[40,150],[40,60],[150,60],[150,40],[40,40],[40,-50]]],[0,0,100,100])
        self.assertTrue(inside_feature(60,70,water))
        self.assertTrue(inside_feature(60,30,water))
        self.assertFalse(inside_feature(60,50,water))
        self.assertFalse(inside_feature(50,50,[[[0,0],[100,0],[100,100],[0,100]],
                                             [[30,30],[70,30],[70,70],[30,70]]]))


if __name__ == '__main__':
    unittest.main()
