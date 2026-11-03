import sys; sys.path.insert(0, '.')
import traceback
from sim.tracks import COMPILED_TRACKS
from sim.data import clone_initial_roster
from sim.physics import RaceSession, CarState

trk = {t.id: t for t in COMPILED_TRACKS}['japan']
t_list, d_list = clone_initial_roster()
race = RaceSession(trk, {t['id']: t for t in t_list}, [d for d in d_list if d.get('team_id')], 0.0, 0.1, 'mercedes')

original_setattr = CarState.__setattr__

def custom_setattr(self, name, val):
    if name == 'd' and hasattr(self, 'd'):
        old_d = getattr(self, 'd')
        diff = abs(val - old_d)
        if diff > 0.14 and getattr(self, 'spin_timer', 0.0) <= 0.0 and getattr(self, 'pit_phase', '') != 'STOPPED':
            tc = getattr(race, 'tick_count', 0)
            print(f'TICK {tc}: {self.code} d changed from {old_d:.3f} to {val:.3f} (delta={val-old_d:+.3f})')
            traceback.print_stack(limit=4)
            if not hasattr(race, '_d_count'): race._d_count = 0
            race._d_count += 1
            if race._d_count >= 5:
                CarState.__setattr__ = original_setattr
    original_setattr(self, name, val)

CarState.__setattr__ = custom_setattr

dt = 0.05
for tick in range(300):
    race.step(dt, lambda c, m: None)
    if hasattr(race, '_d_count') and race._d_count >= 5:
        break

