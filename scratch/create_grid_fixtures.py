import json
import sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from sim.championship import ChampionshipWorld
from sim.tracks import COMPILED_TRACKS

frames=[]
with patch.object(ChampionshipWorld,'_load_state',return_value=False), \
     patch.object(ChampionshipWorld,'_save_state'):
    world=ChampionshipWorld(Path.cwd()/'scratch'/'unused_grid_preview_save.json')
    for track in COMPILED_TRACKS:
        world.current_round=track.round
        world._start_qualifying()
        world.quali_session.standings.reverse()
        world._finish_qualifying_to_grid()
        frames.append({'track':track.to_client_payload(),'tick':world.build_live_tick_payload()})
Path('scratch/grid_fixtures.json').write_text(json.dumps(frames),encoding='utf-8')
print('Prepared 24 stationary grid-walk previews.')
