"""Physical car dimensions shared by simulation, grid markings and canvas.

The public JSON is the single source; the API adds the track's world-unit scale.
The 3cm collision margin is clearance, not an enlargement of the drawn car.
"""
import json
from pathlib import Path
from sim.track_geometry import WORLD_UNITS_PER_M

CAR_GEOMETRY=json.loads((Path(__file__).resolve().parents[1]/'public/car_geometry.json').read_text())
CAR_LEN_PX=(CAR_GEOMETRY['length_m']+2*CAR_GEOMETRY['collision_margin_m'])*WORLD_UNITS_PER_M
CAR_WID_PX=(CAR_GEOMETRY['width_m']+2*CAR_GEOMETRY['collision_margin_m'])*WORLD_UNITS_PER_M
CAR_HALF_LENGTH=CAR_LEN_PX/2
CAR_HALF_WIDTH=CAR_WID_PX/2
CAR_PAIR_RADIUS_SQ=CAR_LEN_PX**2+CAR_WID_PX**2
SC_HALF_LENGTH=CAR_GEOMETRY['safety_car_length_m']*WORLD_UNITS_PER_M/2
SC_HALF_WIDTH=CAR_GEOMETRY['safety_car_width_m']*WORLD_UNITS_PER_M/2


def client_car_geometry():
    return {**CAR_GEOMETRY,'world_units_per_m':WORLD_UNITS_PER_M,
            'collision_length_m':CAR_LEN_PX/WORLD_UNITS_PER_M,
            'collision_width_m':CAR_WID_PX/WORLD_UNITS_PER_M}
