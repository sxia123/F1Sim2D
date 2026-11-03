"""Build an offline preview of all circuits using the actual browser renderer."""
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from sim.tracks import COMPILED_TRACKS

canvas=(ROOT/'public/canvas.js').read_text(encoding='utf-8')
canvas='\n'.join(line for line in canvas.splitlines() if not line.startswith('import ')).replace('export class CircuitRenderer','class CircuitRenderer')
scenery=(ROOT/'public/scenery.js').read_text().replace('export class SceneryLayer','class SceneryLayer')
payloads={t.id:t.to_client_payload() for t in COMPILED_TRACKS}
html=(ROOT/'scratch/scenery_review.html').read_text()
a=html.index('<script type="module">')
script=html[a:].replace("import {CircuitRenderer} from '/canvas.js';",scenery+'\nconst getTeamLogoImage=()=>null;\n'+canvas)
script=script.replace("const tracks=await(await fetch('/review-data/list')).json();",'const payloads='+json.dumps(payloads,ensure_ascii=True).replace('<','\\u003c')+';const tracks=Object.values(payloads);')
script=script.replace("await(await fetch('/review-data/'+sel.value)).json()","payloads[sel.value]")
(ROOT/'scratch/scenery_standalone.html').write_text(html[:a]+script,encoding='utf-8')
for tid,t in payloads.items():
    e=t['environment']
    print(tid, {k:len(e[k]) for k in ('terrain','buildings','trees','water_bodies','grandstands')},flush=True)
