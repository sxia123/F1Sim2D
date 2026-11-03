"""Independent checks against the downloaded geographic and FIA references."""
import json
import math
import unittest
from pathlib import Path
from sim.tracks import COMPILED_TRACKS

ROOT=Path(__file__).resolve().parents[1]
LOCATIONS=['Melbourne','Shanghai','Suzuka','Sakhir','Jeddah','Miami','Montreal','Monaco',
 'Barcelona','Spielberg','Silverstone','Spa Francorchamps','Budapest','Zandvoort','Monza',
 'Madrid','Baku','Singapore','Austin','Mexico City','Sao Paulo','Las Vegas','Lusail','Yas Marina',
 'Portimão','Istanbul','Sepang']

class ReferenceFidelityTests(unittest.TestCase):
    def test_geographic_aspect_ratio_is_preserved(self):
        data=json.loads((ROOT/'circuit_maps_2026/geographic/f1-circuits.geojson').read_text(encoding='utf-8'))
        for track,location in zip(COMPILED_TRACKS,LOCATIONS):
            with self.subTest(track=track.id):
                f=next(f for f in data['features'] if f['properties']['Location']==location)
                points=f['geometry']['coordinates']
                lat=sum(p[1] for p in points)/len(points)
                raw_ratio=(max(p[0] for p in points)-min(p[0] for p in points))*math.cos(math.radians(lat))/(max(p[1] for p in points)-min(p[1] for p in points))
                sts=track.stations
                actual_ratio=(max(p['x'] for p in sts)-min(p['x'] for p in sts))/(max(p['y'] for p in sts)-min(p['y'] for p in sts))
                self.assertLess(abs(actual_ratio/raw_ratio-1),.005,'Map has been stretched or corners displaced')

    def test_official_turn_sequence_and_fixed_grid(self):
        for track in COMPILED_TRACKS:
            with self.subTest(track=track.id):
                self.assertEqual(len(track.corners),track.layout['corner_count'])
                fractions=[c['fraction'] for c in track.layout['corner_markers']]
                self.assertEqual(fractions,sorted(fractions),'Wrong direction or a legend mistaken for a turn')
                self.assertGreater(track.corners[0]['s_m'],track.start_line_s)
                self.assertEqual(track.grid_boxes[2]['slot_offset']-track.grid_boxes[0]['slot_offset'],16)
                self.assertAlmostEqual(track.start_line_s,track.layout['start_line_fraction']*track.length_m)

    def test_pole_sides_and_local_width_coordinates(self):
        right={'saudi','monaco','belgium','azerbaijan','singapore','usa','brazil','vegas','abudhabi','turkey'}
        for track in COMPILED_TRACKS:
            with self.subTest(track=track.id):
                self.assertEqual(track.grid_pole_side,1 if track.id in right else -1)
                for k in range(0,track.NUM_STATIONS,11):
                    p=track.sample(k*track.ds_m)
                    self.assertAlmostEqual(track.lateral_to_px(1,k*track.ds_m),p['width_px']*.39)
                self.assertTrue((ROOT/track.layout['reference_pdf']).is_file())

if __name__=='__main__':unittest.main()
