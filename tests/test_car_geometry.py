"""Physical scale and close-contact regressions for the shared car model."""
import math
import random
import unittest
from types import SimpleNamespace

from sim.car_geometry import CAR_GEOMETRY, CAR_HALF_LENGTH, CAR_HALF_WIDTH
from sim.data import clone_initial_roster
from sim.physics import RaceSession, _sat_obb_penetration, enforce_2d_car_separation
from sim.track_geometry import WORLD_UNITS_PER_M
from sim.tracks import COMPILED_TRACKS


class CarGeometryTests(unittest.TestCase):
    def test_physical_dimensions_reach_every_circuit(self):
        g=CAR_GEOMETRY
        self.assertAlmostEqual(g['front_axle_m']-g['rear_axle_m'],g['wheelbase_m'])
        for track in COMPILED_TRACKS:
            payload=track.to_client_payload()['car_geometry']
            self.assertAlmostEqual(payload['world_units_per_m'],track.px_per_m)
            self.assertEqual(payload['length_m'],5.5)
            self.assertEqual(payload['width_m'],1.9)
            self.assertEqual(payload['wheelbase_m'],3.4)
            self.assertAlmostEqual(CAR_HALF_LENGTH*2,payload['collision_length_m']*track.px_per_m)
            self.assertAlmostEqual(CAR_HALF_WIDTH*2,payload['collision_width_m']*track.px_per_m)
        # Steered front tyre corners and the wider rear tyres fit the footprint.
        for steer in (0,.21,.42):
            front_width=g['front_track_m']+g['front_tyre_width_m']*math.cos(steer)+g['front_tyre_diameter_m']*math.sin(steer)
            self.assertLessEqual(front_width,CAR_HALF_WIDTH*2/WORLD_UNITS_PER_M)
        self.assertAlmostEqual(g['rear_track_m']+g['rear_tyre_width_m'],g['width_m'])

    def test_longer_footprints_are_detected_and_separated(self):
        teams,drivers=clone_initial_roster()
        drivers=[d for d in drivers if d.get('team_id')][:2]
        track=COMPILED_TRACKS[0]
        race=RaceSession(track,{t['id']:t for t in teams},drivers,0,.1,'williams')
        # At 5m separation, the old 4m rectangle and its broad phase both missed
        # contact. Disable driving so only the physical separation pass acts.
        for i,car in enumerate(race.cars):
            car.x=i*5*WORLD_UNITS_PER_M;car.y=0;car.heading=0
            car.s=100+i*5;car.total_dist=car.s;car.d=0
            car.dnf=True;car.dnf_timer=1;car.v=0
        self.assertIsNotNone(_sat_obb_penetration(*race.cars))
        enforce_2d_car_separation(track,race.cars,True,lambda _:None)
        self.assertIsNone(_sat_obb_penetration(*race.cars))
        a,b=race.cars
        b.x=a.x+5.57*WORLD_UNITS_PER_M;b.y=a.y
        self.assertIsNone(_sat_obb_penetration(a,b))
        b.x=a.x;b.y=a.y+2*WORLD_UNITS_PER_M
        self.assertIsNone(_sat_obb_penetration(a,b))
        b.y=a.y+1.9*WORLD_UNITS_PER_M
        self.assertIsNotNone(_sat_obb_penetration(a,b))

    def test_rotated_and_unequal_boxes_match_polygon_projection(self):
        # Independent corner projection also covers the differently sized SC.
        rng=random.Random(6)
        def corners(c,hl,hw):
            co,si=math.cos(c.heading),math.sin(c.heading)
            return [(c.x+x*co-y*si,c.y+x*si+y*co) for x in (-hl,hl) for y in (-hw,hw)]
        for _ in range(200):
            a=SimpleNamespace(x=0,y=0,heading=rng.uniform(-math.pi,math.pi))
            b=SimpleNamespace(x=rng.uniform(-20,20),y=rng.uniform(-20,20),heading=rng.uniform(-math.pi,math.pi))
            hl,hw=7.6,3.2
            ca,cb=corners(a,CAR_HALF_LENGTH,CAR_HALF_WIDTH),corners(b,hl,hw)
            overlaps=True
            for angle in (a.heading,a.heading+math.pi/2,b.heading,b.heading+math.pi/2):
                ax,ay=math.cos(angle),math.sin(angle)
                pa=[x*ax+y*ay for x,y in ca];pb=[x*ax+y*ay for x,y in cb]
                if max(pa)<=min(pb) or max(pb)<=min(pa):overlaps=False
            self.assertEqual(_sat_obb_penetration(a,b,other_half_l=hl,other_half_w=hw) is not None,overlaps)


if __name__=='__main__':unittest.main()
