"""Small cached OSM map extracts, for circuits whose Overpass query timed out."""
from datetime import datetime, timezone
import argparse
import json
from pathlib import Path
import sys
import urllib.request
import xml.etree.ElementTree as ET

from build_scenery_maps import ROOT, CACHE, LOCATIONS, category, build

geo=json.loads((ROOT/'circuit_maps_2026/geographic/f1-circuits.geojson').read_text(encoding='utf-8'))
CACHE.mkdir(exist_ok=True)
parser=argparse.ArgumentParser()
parser.add_argument('tracks',nargs='+')
parser.add_argument('--margin-m',type=float,default=350)
args=parser.parse_args()
for tid in args.tracks:
    coords=next(f['geometry']['coordinates'] for f in geo['features'] if f['properties']['Location']==LOCATIONS[tid])
    import math
    sx=111195*math.cos(math.radians(sum(p[1] for p in coords)/len(coords)))
    x0,y0=min(p[0] for p in coords)-args.margin_m/sx,min(p[1] for p in coords)-args.margin_m/111195
    x1,y1=max(p[0] for p in coords)+args.margin_m/sx,max(p[1] for p in coords)+args.margin_m/111195
    nodes,ways,relations={},{},{}
    complete=True
    for i in range(3):
        for j in range(3):
            prefix=tid if args.margin_m==350 else f'{tid}_margin{args.margin_m:g}'
            cache=CACHE/f'{prefix}_tile_{i}_{j}.xml'
            bbox=[x0+(x1-x0)*i/3,y0+(y1-y0)*j/3,x0+(x1-x0)*(i+1)/3,y0+(y1-y0)*(j+1)/3]
            if not cache.exists():
                url='https://api.openstreetmap.org/api/0.6/map?bbox='+','.join(f'{v:.7f}' for v in bbox)
                try:
                    req=urllib.request.Request(url,headers={'User-Agent':'F1Sim2D offline scenery authoring'})
                    with urllib.request.urlopen(req,timeout=35) as r:blob=r.read()
                    cache.write_bytes(blob)
                except Exception as e:
                    print(tid,i,j,str(e),flush=True);complete=False;continue
            tree=ET.fromstring(cache.read_bytes())
            for e in tree:
                if e.tag=='node':nodes[int(e.attrib['id'])]={'lat':float(e.attrib['lat']),'lon':float(e.attrib['lon'])}
                elif e.tag=='way':ways[int(e.attrib['id'])]=e
                elif e.tag=='relation':relations[int(e.attrib['id'])]=e
            print(tid,i,j,'downloaded',flush=True)
    if not complete:
        print(tid,'incomplete; rerun to fill missing tiles',flush=True);continue
    tags=lambda e:{t.attrib['k']:t.attrib['v'] for t in e.findall('tag')}
    member_ids={int(m.attrib['ref']) for r in relations.values() if category(tags(r)) for m in r.findall('member') if m.attrib['type']=='way'}
    def geometry(e):
        ids=[int(n.attrib['ref']) for n in e.findall('nd')]
        return [nodes[n] for n in ids] if all(n in nodes for n in ids) else []
    elements=[]
    for wid,e in ways.items():
        linear=tid=='saudi' and (tags(e).get('highway') in ('footway','pedestrian','cycleway','path','primary','secondary','tertiary','residential','service','unclassified') or tags(e).get('man_made')=='pier')
        if category(tags(e)) or wid in member_ids or linear:
            elements.append(dict(type='way',id=wid,tags=tags(e),geometry=geometry(e)))
    for rid,e in relations.items():
        if not category(tags(e)):continue
        members=[]
        for m in e.findall('member'):
            ref=int(m.attrib['ref'])
            if m.attrib['type']=='way' and ref in ways:
                members.append(dict(type='way',ref=ref,role=m.attrib.get('role',''),geometry=geometry(ways[ref])))
        # Only replace member ways if all required geometry is present.
        if len(members)==sum(m.attrib['type']=='way' for m in e.findall('member')):
            elements.append(dict(type='relation',id=rid,tags=tags(e),members=members))
    data=dict(version=.6,generator='OSM map API tiled extract',source_url='https://api.openstreetmap.org/api/0.6/map',
              osm3s=dict(timestamp_osm_base=datetime.now(timezone.utc).isoformat(),copyright='© OpenStreetMap contributors'),elements=elements,bbox=[y0,x0,y1,x1])
    (CACHE/f'{tid}.json').write_text(json.dumps(data,ensure_ascii=True,separators=(',',':')),encoding='utf-8')
    build(only=[tid])
