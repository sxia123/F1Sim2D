"""Export new circuits to the actual renderer without touching a career."""
import json,sys
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from sim.championship import ChampionshipWorld
from sim.physics import RaceSession

fixtures=[]
with patch.object(ChampionshipWorld,'_load_state',return_value=False),patch.object(ChampionshipWorld,'_save_state'):
    world=ChampionshipWorld(ROOT/'scratch/unused_preview_save.json')
    teams={t['id']:t for t in world.teams}
    drivers=[d for d in world.drivers if d.get('team_id')]
    for tid,year in [('portugal',2027),('turkey',2027),('malaysia',2026)]:
        world.season_year=year
        track=next(t for t in world.calendar if t.id==tid)
        world.current_round=track.round;world.phase='RACE'
        race=RaceSession(track,teams,drivers,0,.1,world.player_team_id)
        world.race_session=race;race.flag_state='GREEN';race.lights_out=True
        for i,c in enumerate(race.cars):
            c.s=(i*track.length_m/len(race.cars)+60)%track.length_m
            c.total_dist=track.length_m+c.s;c.lap=2;c.laps_completed=1;c.v=50
            race._update_xy(c)
        fixtures.append({'track':track.to_client_payload(),'tick':world.build_live_tick_payload()})
(ROOT/'scratch/future_map_fixtures.json').write_text(json.dumps(fixtures),encoding='utf-8')
print('Exported',len(fixtures),'new game maps')
