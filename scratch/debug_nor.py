import sys; sys.path.insert(0, '.')
from sim.tracks import COMPILED_TRACKS
from sim.data import clone_initial_roster
from sim.physics import RaceSession, CarState

trk = {t.id: t for t in COMPILED_TRACKS}['japan']
t_list, d_list = clone_initial_roster()
race = RaceSession(trk, {t['id']: t for t in t_list}, [d for d in d_list if d.get('team_id')], 0.0, 0.1, 'mercedes')

original_setattr = CarState.__setattr__

def custom_setattr(self, name, val):
    if name == 'v' and hasattr(self, 'v') and self.code == 'NOR':
        old_v = getattr(self, 'v')
        if race.tick_count in (171, 172, 173):
            import traceback
            print(f'TICK {race.tick_count}: NOR v changed {old_v:.3f} -> {val:.3f} (delta={val-old_v:+.3f})')
            traceback.print_stack(limit=3)
    original_setattr(self, name, val)

CarState.__setattr__ = custom_setattr

dt = 0.05
for tick in range(175):
    race.step(dt, lambda c, m: None)

