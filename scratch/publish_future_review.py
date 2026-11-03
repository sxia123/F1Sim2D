"""Publish an offline gallery and source manifest for the three returning maps."""
import hashlib,html,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent/'pdf_tools'))
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from sim.tracks import TRACK_BY_ID, get_season_tracks, calendar_status

folder=ROOT/'circuit_maps_2026/future'
names={'portugal':'Portimão / Algarve','turkey':'Istanbul Park','malaysia':'Sepang'}
seasons={str(y):dict(info=calendar_status(y),tracks=[dict(id=t.id,name=t.circuit,city=t.city,sprint=t.is_sprint) for t in get_season_tracks(y)]) for y in range(2026,2031)}
sheet=Image.new('RGB',(1800,510),'#0b0c12');draw=ImageDraw.Draw(sheet)
try:font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',25)
except OSError:font=ImageFont.load_default()
cards=[];manifest=[]
for i,(tid,title) in enumerate(names.items()):
    t=TRACK_BY_ID[tid];l=t.layout
    im=Image.open(folder/f'{tid}.png');im.thumbnail((590,410));sheet.paste(im,(i*600+(600-im.width)//2,55))
    draw.text((i*600+22,16),title,fill='white',font=font)
    draw.text((i*600+22,475),f'{t.length_m/1000:.3f} km  |  {len(t.corners)} turns  |  playable',fill='#b5bfcd',font=font)
    source=ROOT/l['reference_pdf']
    manifest.append(dict(id=tid,circuit=t.circuit,reference_year=l['reference_year'],reference_pdf=l['reference_pdf'],
        reference_url=l['reference_url'],reference_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        pit_reference=l['pit_reference'],width_note=l['width_note'],accuracy_note=l['accuracy_note'],
        game_preview=f'{tid}.png',source_overlay=f'{tid}_reference_overlay.png',
        copyright='FIA / Formula One World Championship Limited: reference drawings, all rights reserved. Geographic centerline: Tomislav Bacinger, MIT. Pit roads/scenery: OpenStreetMap contributors, ODbL 1.0.'))
    years=', '.join(str(y) for y in range(2026,2031) if tid in {tr.id for tr in get_season_tracks(y)})
    cards.append(f'''<article><div class="eyebrow">NEW PLAYABLE MAP</div><h2>{title}</h2>
<a href="{tid}.png"><img src="{tid}.png" alt="{title} rendered in F1Sim2D"></a>
<p class="stats">{t.length_m/1000:.3f} km <span>·</span> {len(t.corners)} turns <span>·</span> independent pit road</p>
<p>Included in game seasons: <strong>{years}</strong>.</p>
<p class="muted">{l['reference_year']} FIA baseline. {html.escape(l['width_note'])}</p>
<nav><a href="{tid}_pit_detail.png">Driving view</a><a href="{tid}_reference_overlay.png">Source overlay</a><a href="../../{l['reference_pdf']}">FIA drawing</a></nav></article>''')
sheet.save(folder/'new_maps.png')
(folder/'manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False),encoding='utf-8')
(folder/'seasons_2026_2030.json').write_text(json.dumps(seasons,indent=2,ensure_ascii=False),encoding='utf-8')
page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>F1Sim2D — New circuits through 2030</title><style>
*{box-sizing:border-box}body{margin:0;background:#0b0c12;color:#edf1f7;font:15px/1.6 system-ui,sans-serif}main{max-width:1400px;margin:auto;padding:46px 28px}header{max-width:950px;margin-bottom:34px}.eyebrow{color:#ff626a;font-size:11px;font-weight:800;letter-spacing:2px}h1{font-size:clamp(32px,5vw,58px);line-height:1.1;margin:12px 0 20px;letter-spacing:-2px}h2{margin:6px 0 14px;font-size:25px}p{margin:10px 0}.muted{color:#a7b0c1}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(310px,1fr));gap:18px}article,.calendar{background:#151923;border:1px solid #2d3442;border-radius:14px;padding:20px}img{width:100%;aspect-ratio:1250/850;object-fit:contain;border-radius:8px;background:#0b0c12}.stats{font-weight:700;font-size:13px}.stats span{padding:0 7px;color:#ff626a}a{color:#89d4ff;text-underline-offset:3px}nav{display:flex;gap:15px;flex-wrap:wrap;font-size:13px}.calendar{margin:30px 0}select{background:#262d3b;color:white;border:1px solid #677389;border-radius:7px;padding:8px 15px;font:inherit}ol{display:grid;grid-template-columns:repeat(auto-fit,minmax(245px,1fr));gap:6px 28px;padding-left:25px}li{font-size:13px;padding-left:2px}small{color:#ffb4b8}footer{margin-top:26px;color:#a7b0c1;font-size:13px}.badge{background:#423039;border-radius:5px;padding:3px 8px;color:#ffc1c5;font-size:12px;margin-left:10px}
</style><main><header><div class="eyebrow">F1SIM2D · CALENDAR RESEARCH · NOVEMBER 2, 2026</div>
<h1>Three returning circuits.<br>Calendars through 2030.</h1>
<p>Portimão, Istanbul Park and Sepang now have playable geographic maps, pit roads and offline scenery. Madrid is already in the game. The library now contains 27 circuits.</p>
<p class="muted">Portugal returns in 2027–28; Türkiye returns from 2027 through 2031. Zandvoort leaves after 2026. Barcelona races in 2028 and 2030, alternating with Spa in 2027 and 2029. Sepang hosts the relocated Bahrain GP in 2026.</p>
<nav><a href="README.md">Research and sources</a><a href="manifest.json">Map source manifest</a><a href="new_maps.png">Download overview image</a></nav></header>
<section class="cards">'''+''.join(cards)+'''</section>
<section class="calendar"><h2>Explore the season calendars</h2><label for="year">Season </label><select id="year">'''+''.join(f'<option>{y}</option>' for y in range(2026,2031))+'''</select><span class="badge" id="status"></span><p class="muted" id="note"></p><ol id="races"></ol></section>
<footer>2028–30 are game projections, not published full calendars. Portugal is unconfirmed beyond 2028, leaving 23 known-venue races in the 2029–30 game schedules. Other retained venues are continuity assumptions. Qiddiya's switch, Thailand's bid and Rwanda's unspecified early-2030s debut are not assigned fixed seasons here.<br>Widths, garage allocations and aero/OVT zones are estimates. Portugal and Türkiye use historical 2021 FIA baselines; Sepang uses the 2026 FIA drawing. Existing careers keep their current season's schedule and switch at the next season.<br>Centerlines: Tomislav Bacinger (MIT). Pit roads and mapped scenery: OpenStreetMap contributors (ODbL 1.0). Reference drawings: FIA / Formula One World Championship Limited.</footer>
<script>const seasons='''+json.dumps(seasons,ensure_ascii=True)+''';function render(){const s=seasons[document.querySelector('#year').value];document.querySelector('#status').textContent=s.info.status.toUpperCase();document.querySelector('#note').textContent=s.info.note;const list=document.querySelector('#races');list.replaceChildren(...s.tracks.map(t=>{const li=document.createElement('li');li.textContent=t.name+(t.sprint?' · Sprint':'');if(['portugal','turkey','malaysia'].includes(t.id))li.style.color='#ff969c';return li;}));}document.querySelector('#year').addEventListener('change',render);render();</script></main></html>'''
(folder/'index.html').write_text(page,encoding='utf-8')
print('Published 3 map previews, source manifest, overview and five season lists.')
