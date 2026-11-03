"""Create an offline review page for the baked circuit data and its sources."""
import html,json,math,sys
from pathlib import Path
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from sim.tracks import COMPILED_TRACKS

contact=Image.new('RGB',(2400,6*410),'#0b0c12');draw=ImageDraw.Draw(contact)
rows=[];audit={}
for i,t in enumerate(COMPILED_TRACKS):
    l=t.layout;widths=[p['width_m'] for p in t.stations]
    im=Image.open(ROOT/f'scratch/final_map_review/{t.id}.png');im.thumbnail((590,380))
    x=(i%4)*600;y=(i//4)*410
    contact.paste(im,(x,y+25));draw.text((x+8,y+6),t.circuit,fill='white')
    audit[t.id]={'reference_year':l['reference_year'],'source_pdf':l['reference_pdf'],
      'source_url':l['reference_url'],'lap_length_m':t.length_m,'corner_count':len(t.corners),
      'start_offset_from_control_m':round(t.start_line_s,1),'slot_pitch_m':t.grid_spacing_m,
      'same_column_pitch_m':16,'pole_side':'right' if t.grid_pole_side==1 else 'left',
      'width_range_m':[round(min(widths),2),round(max(widths),2)],'width_source':l['width_note'],
      'pit_reference':l['pit_reference'],'pit_length_m':round(t.pit_length_m,1),
      'pit_tunnel_u':t.pit_tunnel_u,'geometry_revision':t.to_client_payload()['geometry_revision']}
    rows.append(f'''<article><h2>{html.escape(t.circuit)}</h2>
      <a href="../scratch/final_map_review/{t.id}.png"><img src="../scratch/final_map_review/{t.id}.png" alt="{html.escape(t.circuit)} game map"></a>
      <p>{l['reference_year']} FIA drawing · {len(t.corners)} turns · {t.length_m:g} m<br>
      Pole: {audit[t.id]['pole_side']} · Grid: 8 m stagger / 16 m same column<br>
      Width: {min(widths):.1f}–{max(widths):.1f} m</p>
      <p class="note">{html.escape(l['width_note'])}</p>
      <p><a href="../{l['reference_pdf']}">Official circuit / pit drawing</a> ·
      <a href="../scratch/accurate_review/{t.id}_overlay.png">Reference overlay</a> ·
      <a href="../scratch/final_grid_review/{t.id}.png">Starting grid</a></p></article>''')
contact.save(ROOT/'circuit_maps_2026/game_maps_review.png')
(ROOT/'circuit_maps_2026/geometry_audit.json').write_text(json.dumps(audit,indent=2),encoding='utf-8')
page='''<!doctype html><html lang="en"><meta charset="utf-8"><title>F1Sim2D circuit geometry review</title>
<style>body{margin:32px;background:#10131b;color:#e8edf6;font:16px system-ui}header{max-width:950px}a{color:#75d9ff}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(380px,1fr));gap:24px}article{background:#191f2b;padding:16px;border:1px solid #394052;border-radius:8px}h2{font-size:20px}img{width:100%;height:290px;object-fit:contain}.note{font-size:13px;color:#afb9ca}</style>
<header><h1>F1Sim2D — circuit geometry review</h1>
<p>All 24 game circuits use geographic GP centerlines and independent pit roads, with FIA start/control landmarks and turn numbering. Geographic aspect ratios are preserved. Grid slots are eight metres apart, sixteen metres in the same column.</p>
<p>These maps are reference-matched approximations, not survey models. Fourteen circuits use spatially matched satellite-derived width variation above the FIA reference width. Others retain FIA reference widths; Madrid uses the existing nominal width. Pit speed lines and garage allocations remain simulation placements. Aero/OVT zones are simulation-generated, not verified 2026 race-control overlays.</p>
<p>Seventeen main drawings are 2026 editions. Bahrain, Saudi Arabia, Brazil, Las Vegas, Qatar and Abu Dhabi use 2025 baselines (six editions); see each source below. Pole sides also use the FIA circuit register and explicitly labelled 2025 pit drawings. The Madrid pole side remains an assumption pending a labelled source.</p>
<p><a href="geometry_audit.json">Machine-readable geometry audit</a> · <a href="game_maps_review.png">All maps contact sheet</a> · <a href="../sim/track_layouts.LICENSE.md">Data attribution</a></p></header><main>'''+''.join(rows)+'</main></html>'
# Count from the actual manifest, rather than implying all 24 are new editions.
years=[t.layout['reference_year'] for t in COMPILED_TRACKS]
page=page.replace('Seventeen main drawings are 2026 editions.','Eighteen main drawings are 2026 editions.') if years.count(2026)==18 else page
(ROOT/'circuit_maps_2026/accuracy_review.html').write_text(page,encoding='utf-8')
print('Published review for',len(rows),'circuits; source years:',{y:years.count(y) for y in set(years)})
