"""Download FIA reference drawings without changing original source files."""
import concurrent.futures
import html
import json
import re
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVENTS = {
 'australia':('Australian Grand Prix',2026), 'china':('Chinese Grand Prix',2026),
 'japan':('Japanese Grand Prix',2026), 'bahrain':('Bahrain Grand Prix',2025),
 'saudi':('Saudi Arabian Grand Prix',2025), 'miami':('Miami Grand Prix',2026),
 'canada':('Canadian Grand Prix',2026), 'monaco':('Monaco Grand Prix',2026),
 'barcelona':('Barcelona-Catalunya Grand Prix',2026), 'austria':('Austrian Grand Prix',2026),
 'britain':('British Grand Prix',2026), 'belgium':('Belgian Grand Prix',2026),
 'hungary':('Hungarian Grand Prix',2026), 'netherlands':('Dutch Grand Prix',2026),
 'italy':('Italian Grand Prix',2026), 'madrid':('Spanish Grand Prix',2026),
 'azerbaijan':('Azerbaijan Grand Prix',2026), 'singapore':('Singapore Grand Prix',2026),
 'usa':('United States Grand Prix',2026), 'mexico':('Mexico City Grand Prix',2026),
 'brazil':('São Paulo Grand Prix',2025), 'vegas':('Las Vegas Grand Prix',2025),
 'qatar':('Qatar Grand Prix',2025), 'abudhabi':('Abu Dhabi Grand Prix',2025),
}

def get(url):
    req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'})
    return urllib.request.urlopen(req,timeout=60).read()

def fetch(item):
    tid,(event,year)=item
    index=('https://www.fia.com/documents/championships/fia-formula-one-world-championship-14/'
           f'season/season-{year}-{2072 if year==2026 else 2071}/event/'+urllib.parse.quote(event))
    cache=ROOT/'scratch'/f'fia_index_{tid}_{year}.html'
    body=cache.read_text(encoding='utf-8') if cache.exists() else get(index).decode()
    cache.write_text(body,encoding='utf-8')
    links=[html.unescape(u) for u in re.findall(r'href="([^\"]+\.pdf)"',body)]
    links=[u for u in links if f'{year}_' in u and 'circuit_map' in u and 'pit_lane' in u]
    if not links:
        raise ValueError(f'No map in {index}')
    link=urllib.parse.urljoin('https://www.fia.com',links[0])
    folder=ROOT/'circuit_maps_2026'/'fia_reference'
    folder.mkdir(exist_ok=True)
    target=folder/f'{tid}_{year}.pdf'
    if not target.exists():target.write_bytes(get(link))
    if not target.read_bytes().startswith(b'%PDF'):raise ValueError(f'Not PDF: {tid}')
    return {'id':tid,'year':year,'pdf':str(target.relative_to(ROOT)).replace('\\','/'),
            'source_url':link,'index_url':index}

if __name__=='__main__':
    results=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        for item,future in [(item,pool.submit(fetch,item)) for item in EVENTS.items()]:
            try:
                result=future.result();results.append(result)
                print(result['id'],result['year'],result['pdf'],flush=True)
            except Exception as exc:print('FAILED',item[0],str(exc),flush=True)
    (ROOT/'circuit_maps_2026'/'fia_reference_manifest.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
