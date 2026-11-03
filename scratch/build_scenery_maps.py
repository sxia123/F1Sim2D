"""Download and bake geographic scenery. Authoring only; game stays offline/stdlib.

Run with Python 3. OSM responses are cached; --fetch fills missing responses.
The output uses the same north-up, metre-based layout frame as track_layouts.
"""
import argparse
import json
import math
from pathlib import Path
import urllib.request
import urllib.parse

ROOT = Path(__file__).resolve().parents[1]
LOCATIONS = dict(zip(
    'australia china japan bahrain saudi miami canada monaco barcelona austria britain belgium hungary netherlands italy madrid azerbaijan singapore usa mexico brazil vegas qatar abudhabi'.split(),
    ['Melbourne', 'Shanghai', 'Suzuka', 'Sakhir', 'Jeddah', 'Miami', 'Montreal', 'Monaco', 'Barcelona', 'Spielberg', 'Silverstone', 'Spa Francorchamps', 'Budapest', 'Zandvoort', 'Monza', 'Madrid', 'Baku', 'Singapore', 'Austin', 'Mexico City', 'Sao Paulo', 'Las Vegas', 'Lusail', 'Yas Marina']))
CACHE = ROOT / 'circuit_maps_2026/scenery'
LOCATIONS.update({'portugal':'Portimão', 'turkey':'Istanbul', 'malaysia':'Sepang'})


def simplify(points, tolerance=1.2):
    if len(points) < 3:
        return points
    a, b = points[0], points[-1]
    dx, dy = b[0]-a[0], b[1]-a[1]
    length = dx*dx+dy*dy
    best, index = 0, 0
    for i, p in enumerate(points[1:-1], 1):
        u = max(0, min(1, ((p[0]-a[0])*dx+(p[1]-a[1])*dy)/length)) if length else 0
        d = math.hypot(p[0]-a[0]-u*dx, p[1]-a[1]-u*dy)
        if d > best:
            best, index = d, i
    if best <= tolerance:
        return [a, b]
    return simplify(points[:index+1], tolerance)[:-1] + simplify(points[index:], tolerance)


def rings(parts):
    """Join relation member ways by their geographic endpoints, preserving holes."""
    parts = [p[:] for p in parts if len(p) > 1]
    result = []
    while parts:
        ring = parts.pop()
        while ring[0] != ring[-1]:
            found = False
            for i, p in enumerate(parts):
                if ring[-1] == p[0]:
                    ring += p[1:]
                elif ring[-1] == p[-1]:
                    ring += p[-2::-1]
                elif ring[0] == p[-1]:
                    ring = p[:-1] + ring
                elif ring[0] == p[0]:
                    ring = p[:0:-1] + ring
                else:
                    continue
                parts.pop(i)
                found = True
                break
            if not found:
                break
        if ring[0] == ring[-1] and len(ring) >= 4:
            result.append(ring)
    return result


def category(tags):
    if tags.get('building') == 'grandstand' or tags.get('leisure') == 'grandstand':
        return 'grandstand'
    if tags.get('building') and tags['building'] != 'no':
        return 'building'
    if tags.get('natural') == 'water' or tags.get('waterway') == 'riverbank' or tags.get('leisure') == 'swimming_pool':
        return 'water'
    if tags.get('natural') == 'coastline':
        return 'coastline'
    if tags.get('natural') == 'wood' or tags.get('landuse') == 'forest':
        return 'wood'
    if tags.get('natural') in ('sand', 'beach', 'bare_rock'):
        return 'sand'
    if tags.get('natural') in ('scrub', 'heath', 'grassland'):
        return 'scrub'
    if tags.get('amenity') == 'parking':
        return 'parking'
    if tags.get('leisure') == 'pitch':
        return 'pitch'
    if tags.get('landuse') in ('farmland', 'farmyard'):
        return 'field'
    if tags.get('leisure') in ('park', 'garden', 'golf_course') or tags.get('landuse') in ('grass', 'meadow', 'recreation_ground', 'village_green'):
        return 'grass'
    return None


def build(fetch=False, only=None, endpoint='https://overpass-api.de/api/interpreter'):
    geo = json.loads((ROOT/'circuit_maps_2026/geographic/f1-circuits.geojson').read_text(encoding='utf-8'))
    CACHE.mkdir(exist_ok=True)
    baked = {}
    output = ROOT/'sim/scenery_maps.json'
    if output.exists():
        baked = json.loads(output.read_text())
    for tid, location in LOCATIONS.items():
        if only and tid not in only:
            continue
        coords = next(f['geometry']['coordinates'] for f in geo['features'] if f['properties']['Location'] == location)
        lon0 = sum(p[0] for p in coords)/len(coords)
        lat0 = sum(p[1] for p in coords)/len(coords)
        sx, sy = 111195*math.cos(math.radians(lat0)), -111195
        raw = [[(p[0]-lon0)*sx, (p[1]-lat0)*sy] for p in coords]
        cx = (min(p[0] for p in raw)+max(p[0] for p in raw))/2
        cy = (min(p[1] for p in raw)+max(p[1] for p in raw))/2
        def project(p):
            return [round((p[0]-lon0)*sx-cx+500, 1), round((p[1]-lat0)*sy-cy+325, 1)]
        bbox = (min(p[1] for p in coords)-350/111195, min(p[0] for p in coords)-350/sx,
                max(p[1] for p in coords)+350/111195, max(p[0] for p in coords)+350/sx)
        cache = CACHE/f'{tid}.json'
        if not cache.exists() and fetch:
            box = ','.join(f'{v:.7f}' for v in bbox)
            query = f'''[out:json][timeout:55];(
              way[building]({box});relation[building]({box});
              way[natural~"^(water|wood|sand|beach|scrub|heath|grassland|coastline)$"]({box});
              relation[natural~"^(water|wood|sand|beach|scrub|heath|grassland)$"]({box});
              way[landuse~"^(forest|grass|meadow|farmland|recreation_ground|village_green)$"]({box});
              relation[landuse~"^(forest|grass|meadow|farmland)$"]({box});
              way[leisure~"^(park|garden|golf_course|pitch|swimming_pool|grandstand)$"]({box});
              relation[leisure~"^(park|garden|golf_course)$"]({box});
              way[amenity=parking]({box});
            );out geom;'''
            request = urllib.request.Request(endpoint, data=urllib.parse.urlencode({'data':query}).encode(), headers={'User-Agent': 'F1Sim2D offline scenery authoring'})
            try:
                with urllib.request.urlopen(request, timeout=75) as response:
                    data = response.read()
                parsed = json.loads(data)
                if parsed.get('remark'):
                    raise RuntimeError(parsed['remark'])
                cache.write_bytes(data)
            except Exception as e:
                print(tid, 'FETCH FAILED', str(e), flush=True)
                continue
        if not cache.exists():
            continue
        data = json.loads(cache.read_text(encoding='utf-8'))
        features = []
        linear_features = []
        # Relation member footprints replace their standalone copies.
        members = {m['ref'] for e in data['elements'] if e['type'] == 'relation' and category(e.get('tags', {}))
                   for m in e.get('members', []) if m['type'] == 'way'}
        for e in data['elements']:
            tags = e.get('tags', {})
            kind = category(tags)
            if tid == 'saudi' and e['type'] == 'way':
                highway=tags.get('highway')
                is_pier=tags.get('man_made')=='pier'
                if is_pier or highway in ('footway','pedestrian','cycleway','path','primary','secondary','tertiary','residential','service','unclassified'):
                    line=simplify([project((g['lon'],g['lat'])) for g in e.get('geometry',[]) if 'lon' in g])
                    if len(line)>1:
                        linear_features.append(dict(id=f"way/{e['id']}",points=line,
                            kind='pier' if is_pier else 'promenade' if highway in ('footway','pedestrian','cycleway','path') else 'access_road',
                            name=tags.get('name:en',tags.get('name','')),width_m=4 if is_pier else 2.8 if highway in ('footway','pedestrian','cycleway','path') else 9 if highway in ('primary','secondary') else 6))
            if not kind or (e['type'] == 'way' and e['id'] in members):
                continue
            convert = lambda gs: [(g['lon'], g['lat']) for g in gs if 'lon' in g]
            if e['type'] == 'relation':
                outer = rings([convert(m.get('geometry', [])) for m in e.get('members', []) if m.get('role') != 'inner'])
                inner = rings([convert(m.get('geometry', [])) for m in e.get('members', []) if m.get('role') == 'inner'])
            else:
                p = convert(e.get('geometry', []))
                outer, inner = ([p] if len(p) > 2 and (p[0] == p[-1] or kind == 'coastline') else []), []
            if not outer:
                continue
            paths = [simplify([project(p) for p in ring]) for ring in outer+inner]
            if not paths or len(paths[0]) < 4:
                continue
            features.append({'id': f"{e['type']}/{e['id']}", 'kind': kind, 'paths': paths,
                             'name': tags.get('name:en', tags.get('name', '')),
                             'leaf_type': tags.get('leaf_type', '')})
        baked[tid] = {'features': features, 'timestamp': data.get('osm3s', {}).get('timestamp_osm_base'), 'bbox': data.get('bbox',bbox)}
        if tid == 'saudi':
            baked[tid]['linear_features']=linear_features
        output.write_text(json.dumps(baked, ensure_ascii=True, separators=(',', ':')), encoding='utf-8')
        print(tid, len(features), 'features', cache.stat().st_size, 'bytes', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--fetch', action='store_true')
    parser.add_argument('--only', nargs='*')
    parser.add_argument('--endpoint', default='https://overpass-api.de/api/interpreter')
    args = parser.parse_args()
    build(args.fetch, args.only, args.endpoint)
