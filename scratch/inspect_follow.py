import math
import sys, pathlib, random
ROOT = pathlib.Path(r'c:\Coding\F1Sim2D')
sys.path.insert(0, str(ROOT))
from sim.data import clone_initial_roster
from sim.physics import (
    CAR_LEN_PX,
    CAR_WID_PX,
    CarState,
    RaceSession,
    _sat_obb_penetration,
    compute_lateral_screen_px,
)
from sim.tracks import COMPILED_TRACKS

# Let's monkey-patch _step_car to include green flag following distance speed regulation
orig_step_car = RaceSession._step_car

def patched_step_car(self, car: CarState, car_ahead: CarState | None, leader: CarState | None, leader_finished: bool, dt: float, event_cb) -> None:
    # Call original step car
    orig_step_car(self, car, car_ahead, leader, leader_finished, dt, event_cb)

RaceSession._step_car = patched_step_car

# Let's inspect where target_v is computed in _step_car

