import json
import math
import random
import sys
import tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from sim.championship import ChampionshipWorld
from sim.physics import RaceSession
from sim.tracks import COMPILED_TRACKS

fixtures=[]
with tempfile.TemporaryDirectory() as tmp:
    random.seed(9)
    world=ChampionshipWorld(Path(tmp)/'test_career.json')
    teams={t['id']:t for t in world.teams}
    drivers=[d for d in world.drivers if d.get('team_id')]
    for t in COMPILED_TRACKS:
        world.current_round=t.round;world.phase='RACE'
        race=RaceSession(t,teams,drivers,0,.1,world.player_team_id)
        world.race_session=race
        race.flag_state='GREEN';race.lights_out=True
        for i,c in enumerate(race.cars):
            c.s=(i*t.length_m/len(race.cars)+60)%t.length_m
            c.total_dist=t.length_m+c.s;c.lap=2;c.laps_completed=1;c.v=50
            race._update_xy(c)
        # A moving car and a parked car expose pit width / apron alignment.
        for i in (0,1):
            c=race.cars[i];c.s=t.pit_garages[i]['s_m'];c.total_dist=t.length_m+c.s
            c.in_pits=True;c.pit_phase='STOPPED' if i==0 else 'EXIT';c.pit_apron=1 if i==0 else 0
            c.v=0 if i==0 else 22.22;race._update_xy(c)
        fixtures.append({'track':t.to_client_payload(),'tick':world.build_live_tick_payload()})
Path('scratch/map_fixtures.json').write_text(json.dumps(fixtures),encoding='utf-8')
print('Exported',len(fixtures),'rendering fixtures without changing the career save.')
