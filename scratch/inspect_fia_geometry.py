"""Render FIA map/pit pages and collect reference text coordinates."""
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent/'pdf_tools'))
import fitz
from PIL import Image,ImageDraw

ROOT=Path(__file__).resolve().parents[1]
folder=ROOT/'scratch/fia_review';folder.mkdir(exist_ok=True)
records=json.loads((ROOT/'circuit_maps_2026/fia_reference_manifest.json').read_text())
contact=Image.new('RGB',(2000,6*500),'white')
pit_contact=Image.new('RGB',(2400,6*360),'white')
metadata={}
for i,r in enumerate(records):
    doc=fitz.open(ROOT/r['pdf'])
    page=doc[1]
    pix=page.get_pixmap(matrix=fitz.Matrix(2,2));im=Image.frombytes('RGB',(pix.width,pix.height),pix.samples)
    im.save(folder/f'{r["id"]}_circuit.png')
    im.thumbnail((490,470));contact.paste(im,((i%4)*500,(i//4)*500+25))
    ImageDraw.Draw(contact).text(((i%4)*500+5,(i//4)*500+5),r['id'],fill='black')
    p=doc[2];pix=p.get_pixmap(matrix=fitz.Matrix(1.5,1.5));im=Image.frombytes('RGB',(pix.width,pix.height),pix.samples)
    im.save(folder/f'{r["id"]}_pit.png');im.thumbnail((590,335));pit_contact.paste(im,((i%4)*600,(i//4)*360+25))
    ImageDraw.Draw(pit_contact).text(((i%4)*600+5,(i//4)*360+5),r['id'],fill='black')
    spans=[s for b in page.get_text('dict')['blocks'] if 'lines' in b for l in b['lines'] for s in l['spans']]
    metadata[r['id']]={'spans':[{'text':s['text'],'color':s['color'],'bbox':s['bbox']} for s in spans],
        'pit_text':p.get_text(),'circuit_text':page.get_text(),'page_size':[page.rect.width,page.rect.height]}
    print(r['id'],len(page.get_drawings()),flush=True)
contact.save(folder/'circuits.png');pit_contact.save(folder/'pits.png')
(folder/'metadata.json').write_text(json.dumps(metadata),encoding='utf-8')
