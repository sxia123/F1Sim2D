"""Cache OSM raceway / service-road data for geographic geometry checks."""
import concurrent.futures
import json
import math
import urllib.parse
import urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CENTERS={
 'portugal':(37.232, -8.628), 'turkey':(40.952,29.405), 'malaysia':(2.761,101.738),
 'australia':(-37.8497,144.968), 'china':(31.3393,121.220), 'japan':(34.844,136.536),
 'bahrain':(26.0325,50.5106), 'saudi':(21.636,39.104), 'miami':(25.958,-80.239),
 'canada':(45.5017,-73.527), 'monaco':(43.736,7.423), 'barcelona':(41.57,2.261),
 'austria':(47.222,14.765), 'britain':(52.073,-1.015), 'belgium':(50.439,5.966),
 'hungary':(47.581,19.25), 'netherlands':(52.388,4.544), 'italy':(45.621,9.29),
 'madrid':(40.471,-3.614), 'azerbaijan':(40.373,49.853), 'singapore':(1.292,103.862),
 'usa':(30.133,-97.641), 'mexico':(19.405,-99.091), 'brazil':(-23.702,-46.697),
 'vegas':(36.114,-115.168), 'qatar':(25.49,51.454), 'abudhabi':(24.469,54.604),
}

def fetch(item):
    tid,(lat,lon)=item
    target=ROOT/'circuit_maps_2026'/'osm'/f'{tid}.json'
    target.parent.mkdir(exist_ok=True)
    if target.exists():return tid,len(json.loads(target.read_text(encoding='utf-8'))['elements'])
    dx=.026/math.cos(math.radians(lat));dy=.026
    query=f'[out:json][timeout:60];(way[highway]({lat-dy},{lon-dx},{lat+dy},{lon+dx});node[sport=motorsport]({lat-dy},{lon-dx},{lat+dy},{lon+dx}););out geom;'
    request=urllib.request.Request('https://overpass-api.de/api/interpreter',data=urllib.parse.urlencode({'data':query}).encode(),headers={'User-Agent':'F1Sim2D circuit reference/1.0'})
    data=urllib.request.urlopen(request,timeout=90).read()
    result=json.loads(data)
    target.write_bytes(data)
    return tid,len(result['elements'])

if __name__=='__main__':
    import sys
    if '--batch' in sys.argv:
        missing=[(k,v) for k,v in CENTERS.items() if not (ROOT/'circuit_maps_2026/osm'/f'{k}.json').exists()]
        clauses=[]
        for tid,(lat,lon) in missing:
            dx=.025/math.cos(math.radians(lat));dy=.025
            box=f'({lat-dy},{lon-dx},{lat+dy},{lon+dx})'
            clauses.extend([f'way[highway=raceway]{box};',f'way[highway=service]{box};',f'way["name"~"[Pp]it [Ll]ane"]{box};'])
        query='[out:json][timeout:90];('+''.join(clauses)+');out geom;'
        req=urllib.request.Request('https://overpass-api.de/api/interpreter',data=urllib.parse.urlencode({'data':query}).encode(),headers={'User-Agent':'F1Sim2D circuit reference/1.0'})
        try:
            result=json.loads(urllib.request.urlopen(req,timeout=110).read())
        except urllib.error.HTTPError as exc:
            print('HTTP',exc.code,'Retry-After:',exc.headers.get('Retry-After'),flush=True)
            raise
        for tid,(lat,lon) in missing:
            elems=[e for e in result['elements'] if any(abs(g['lat']-lat)<.026 and abs(g['lon']-lon)<.026/math.cos(math.radians(lat)) for g in e.get('geometry',[]))]
            out={**result,'elements':elems}
            (ROOT/'circuit_maps_2026/osm'/f'{tid}.json').write_text(json.dumps(out),encoding='utf-8')
            print(tid,len(elems),flush=True)
        sys.exit()
    selected={k:v for k,v in CENTERS.items() if not sys.argv[1:] or k in sys.argv[1:]}
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        for item,future in [(i,pool.submit(fetch,i)) for i in selected.items()]:
            try:print(future.result(),flush=True)
            except Exception as exc:print('FAILED',item[0],str(exc),flush=True)
