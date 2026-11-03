"""Isolated driving smoke check; never reads or writes the player's career."""
import json
import math
import random
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from sim.data import clone_initial_roster
from sim.physics import RaceSession, _sat_obb_penetration
from sim.tracks import COMPILED_TRACKS

teams,drivers=clone_initial_roster()
teams={t['id']:t for t in teams}
drivers=[d for d in drivers if d.get('team_id')]
report=[]
for name in ('monaco','japan','italy'):
    track=next(t for t in COMPILED_TRACKS if t.id==name)
    random.seed(14)
    race=RaceSession(track,teams,drivers,0,.1,'williams')
    race.lights_out=True;race.flag_state='GREEN'
    before=[c.total_dist for c in race.cars]
    overlap_frames=0
    for i in range(900):
        race.step(.05,lambda *_:None)
        assert all(math.isfinite(v) for c in race.cars for v in (c.x,c.y,c.heading,c.v,c.total_dist))
        if i%20==0:
            active=[c for c in race.cars if not c.dnf and not c.in_pits]
            if any(_sat_obb_penetration(a,b) for j,a in enumerate(active) for b in active[j+1:]):overlap_frames+=1
    assert all(c.total_dist>old+50 for c,old in zip(race.cars,before)),name
    report.append({'track':name,'simulated_seconds':45,'cars':len(race.cars),'sampled_overlap_frames':overlap_frames})
print(json.dumps(report))
