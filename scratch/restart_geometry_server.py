"""Replace only verified F1Sim2D servers, keeping a copy of the career save."""
import json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scratch/geometry_deps'))
import psutil

servers=[]
for p in psutil.process_iter(['pid','name','cmdline','cwd']):
    try:
        args=p.info['cmdline'] or []
        if (p.info['name'] or '').lower()=='python.exe' and args[1:]==['server.py','--port','8080'] and Path(p.info['cwd']).resolve()==ROOT:
            servers.append(p)
    except (psutil.AccessDenied,psutil.NoSuchProcess):pass
if not servers:raise SystemExit('No verified game servers to replace.')
save=ROOT/'data/championship_state.json'
raw=save.read_bytes();json.loads(raw)
backup=ROOT/'scratch'/(sys.argv[1] if len(sys.argv)>1 else 'career_before_geometry_restart.json');backup.write_bytes(raw)
print('Career backed up. Replacing verified game server PIDs:',[p.pid for p in servers],flush=True)
for p in servers:p.terminate()
gone,alive=psutil.wait_procs(servers,timeout=8)
if alive:raise SystemExit('Some old processes remain; no new server launched.')
print('Stopped',len(gone),'stale game servers.',flush=True)
