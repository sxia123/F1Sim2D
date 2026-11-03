"""Geographic scenery with footprint clearance from every race and pit segment.

Mapped footprints and land cover come from the offline OSM scenery bake.
Small vegetation/ground details are deterministic illustration, never physics.
"""
from __future__ import annotations

from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import random
import weakref

CIRCUIT_THEMES = dict(zip(
    "australia china japan bahrain saudi miami canada monaco barcelona austria britain belgium hungary netherlands italy madrid azerbaijan singapore usa mexico brazil vegas qatar abudhabi".split(),
    "parkland parkland forest desert coastal marina parkland marina parkland forest parkland forest parkland dunes forest urban coastal marina parkland parkland parkland urban desert marina".split()))

_SCENERY_PATH = Path(__file__).with_name("scenery_maps.json")
CIRCUIT_THEMES.update({'portugal':'parkland', 'turkey':'forest', 'malaysia':'parkland'})
_SCENERY_BYTES = _SCENERY_PATH.read_bytes() if _SCENERY_PATH.exists() else b"{}"
_SCENERY = json.loads(_SCENERY_BYTES)
ENVIRONMENT_REVISION = "scenery-v2-" + hashlib.sha256(_SCENERY_BYTES).hexdigest()[:12]
_ENV_CACHE = weakref.WeakKeyDictionary()
ROAD_CLEARANCE = 14.0  # Beyond road edge: kerbs, verges, markings and working apron.


def point_segment_distance(p, a, b):
    dx, dy = b[0]-a[0], b[1]-a[1]
    u = max(0.0, min(1.0, ((p[0]-a[0])*dx+(p[1]-a[1])*dy)/max(dx*dx+dy*dy, 1e-12)))
    return math.hypot(p[0]-a[0]-u*dx, p[1]-a[1]-u*dy)


def inside_path(x, y, points):
    inside = False
    for a, b in zip(points, points[1:]+points[:1]):
        if (a[1] > y) != (b[1] > y) and x < (b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]:
            inside = not inside
    return inside


def inside_feature(x, y, paths):
    return sum(inside_path(x, y, p) for p in paths) % 2 == 1


def segment_distance(a, b, c, d):
    def cross(p, q, r):
        return (q[0]-p[0])*(r[1]-p[1])-(q[1]-p[1])*(r[0]-p[0])
    if cross(a,b,c)*cross(a,b,d) < 0 and cross(c,d,a)*cross(c,d,b) < 0:
        return 0.0
    return min(point_segment_distance(a,c,d), point_segment_distance(b,c,d),
               point_segment_distance(c,a,b), point_segment_distance(d,a,b))


def feature_bounds(paths):
    pts = [p for path in paths for p in path]
    return [min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts)]


def clip_path(points, bounds):
    """Clip large mapped land-cover rings before indexing or sending to the client."""
    for axis, edge, sign in ((0,bounds[0],1),(0,bounds[2],-1),(1,bounds[1],1),(1,bounds[3],-1)):
        out = []
        for a,b in zip(points,points[1:]+points[:1]):
            ain,bin = (a[axis]-edge)*sign >= 0,(b[axis]-edge)*sign >= 0
            if ain != bin:
                u = (edge-a[axis])/(b[axis]-a[axis])
                out.append([a[0]+u*(b[0]-a[0]),a[1]+u*(b[1]-a[1])])
            if bin:
                out.append(b)
        points = out
        if not points:
            break
    return points


def rectangle(x, y, w, h, angle):
    co, si = math.cos(angle), math.sin(angle)
    return [[x+a*co-b*si, y+a*si+b*co] for a,b in ((-w/2,-h/2),(w/2,-h/2),(w/2,h/2),(-w/2,h/2))]


def coast_water(lines, bounds):
    """Join directed OSM coastlines and close sea areas along the view boundary.

    OSM land is left of the geographic coastline. North-up screen projection
    reverses orientation; the water ring has positive signed screen area.
    Never close a partial coast through the middle of the scene.
    """
    parts = [line[:] for line in lines if len(line)>1]
    chains = []
    while parts:
        chain = parts.pop()
        changed = True
        while changed:
            changed = False
            for i,p in enumerate(parts):
                if math.dist(chain[-1],p[0])<1:
                    chain += p[1:]
                elif math.dist(p[-1],chain[0])<1:
                    chain = p[:-1]+chain
                else:
                    continue
                parts.pop(i);changed=True;break
        chains.append(chain)
    x0,y0,x1,y1 = bounds
    w,h=x1-x0,y1-y0
    perimeter=2*(w+h)
    corners=[(0,[x0,y0]),(w,[x1,y0]),(w+h,[x1,y1]),(2*w+h,[x0,y1])]
    def boundary_position(p):
        if abs(p[1]-y0)<.1:return p[0]-x0
        if abs(p[0]-x1)<.1:return w+p[1]-y0
        if abs(p[1]-y1)<.1:return w+h+x1-p[0]
        if abs(p[0]-x0)<.1:return 2*w+h+y1-p[1]
        return None
    result=[];open_lines=[];islands=[]
    for chain in chains:
        # Liang-Barsky clipping keeps each open fragment's boundary endpoints.
        fragments=[];fragment=[]
        for a,b in zip(chain,chain[1:]):
            dx,dy=b[0]-a[0],b[1]-a[1]
            lo,hi=0.0,1.0
            for p,q in ((-dx,a[0]-x0),(dx,x1-a[0]),(-dy,a[1]-y0),(dy,y1-a[1])):
                if abs(p)<1e-12:
                    if q<0:lo=2;break
                elif p<0:lo=max(lo,q/p)
                else:hi=min(hi,q/p)
            if lo>hi:
                if fragment:fragments.append(fragment);fragment=[]
                continue
            start=[a[0]+lo*dx,a[1]+lo*dy];end=[a[0]+hi*dx,a[1]+hi*dy]
            if fragment and math.dist(fragment[-1],start)>.1:
                fragments.append(fragment);fragment=[]
            if not fragment:fragment=[start]
            fragment.append(end)
        if fragment:fragments.append(fragment)
        for line in fragments:
            if math.dist(line[0],line[-1])<.1:
                islands.append(line)
            elif boundary_position(line[0]) is not None and boundary_position(line[-1]) is not None:
                open_lines.append(line)
    # Follow each water face: a coastline fragment, then the scene perimeter to
    # the next directed fragment. Closing each fragment independently floods
    # peninsulas when one coastline enters the view more than once.
    unused=set(range(len(open_lines)))
    while unused:
        first=min(unused);current=first;polygon=[];visited=set()
        while current not in visited:
            visited.add(current);unused.discard(current)
            line=open_lines[current];polygon+=line
            end=boundary_position(line[-1])
            candidates=unused|{first}
            following=min(candidates,key=lambda k:(boundary_position(open_lines[k][0])-end)%perimeter)
            distance=(boundary_position(open_lines[following][0])-end)%perimeter
            polygon += [p for _,p in sorted(((t-end)%perimeter,p) for t,p in corners if 0<(t-end)%perimeter<distance)]
            current=following
            if current==first:break
        if len(polygon)>3:result.append(polygon)
    if not result and islands:
        result=[[[x0,y0],[x1,y0],[x1,y1],[x0,y1]]]
    for island in islands:
        if result and inside_feature(*island[0],result):result.append(island)
    return result


class SpatialGrid:
    def __init__(self, size=160.0):
        self.size = size
        self.cells = defaultdict(list)

    def keys(self, bounds):
        x0,y0,x1,y1 = bounds
        for i in range(math.floor(x0/self.size), math.floor(x1/self.size)+1):
            for j in range(math.floor(y0/self.size), math.floor(y1/self.size)+1):
                yield i,j

    def add(self, bounds, value):
        for key in self.keys(bounds):
            self.cells[key].append(value)

    def query(self, bounds):
        seen = set()
        for key in self.keys(bounds):
            for value in self.cells.get(key, ()):
                ident = id(value)
                if ident not in seen:
                    seen.add(ident)
                    yield value


class RoadClearance:
    """Continuous capsules use local widths, including the closing lap segment."""
    def __init__(self, track):
        self.grid = SpatialGrid()
        for points, closed, default_width in ((track.stations, True, track.track_width_px),
                                              (track.pit_stations, False, track.pit_width_px)):
            ends = points[1:]+points[:1] if closed else points[1:]
            for a,b in zip(points, ends):
                radius = max(a.get("width_px", default_width), b.get("width_px", default_width))/2+ROAD_CLEARANCE
                # Pit station width is explicitly the pit/apron width, not the race width.
                if not closed:
                    radius = default_width/2+ROAD_CLEARANCE
                pa,pb = (a["x"],a["y"]),(b["x"],b["y"])
                self.grid.add([min(pa[0],pb[0])-radius, min(pa[1],pb[1])-radius,
                               max(pa[0],pb[0])+radius, max(pa[1],pb[1])+radius], (pa,pb,radius))

    def circle_safe(self, x, y, radius):
        return all(point_segment_distance((x,y),a,b) > road_radius+radius
                   for a,b,road_radius in self.grid.query([x-radius,y-radius,x+radius,y+radius]))

    def polygon_safe(self, paths, padding=9.0):
        x0,y0,x1,y1 = feature_bounds(paths)
        for a,b,radius in self.grid.query([x0-padding,y0-padding,x1+padding,y1+padding]):
            if inside_feature(*a,paths) or inside_feature(*b,paths):
                return False
            if any(segment_distance(a,b,c,d) <= radius+padding for p in paths for c,d in zip(p,p[1:]+p[:1])):
                return False
        return True


def get_track_environment(track):
    # Geometry participates in caching, so a recompiled/edited circuit cannot reuse old placements.
    fingerprint = hash(tuple((p["x"],p["y"],p.get("width_px",track.track_width_px)) for p in track.stations)
                       + tuple((p["x"],p["y"],track.pit_width_px) for p in track.pit_stations))
    cached = _ENV_CACHE.get(track)
    if cached and cached[0] == fingerprint:
        return cached[1]
    rng = random.Random("scenery-v2:"+track.id)
    theme = CIRCUIT_THEMES.get(track.id,"parkland")
    road = RoadClearance(track)
    b = track.bounds
    margin = 320.0
    bounds = [b["min_x"]-margin,b["min_y"]-margin,b["max_x"]+margin,b["max_y"]+margin]
    if track.id == 'saudi':
        # Jeddah is unusually long and narrow. Continue the Red Sea across the
        # wide camera view rather than ending it at a narrow strip around the road.
        center=(b['min_x']+b['max_x'])/2
        half_width=(b['max_y']-b['min_y'])*1.15
        bounds[0],bounds[2]=center-half_width,center+half_width
    env = dict(theme=theme, revision=ENVIRONMENT_REVISION, bounds=bounds,
               terrain=[], water_bodies=[], buildings=[], grandstands=[], trees=[],
               landmarks=[], yachts=[], gravel_traps=[], details=[],
               attribution="© OpenStreetMap contributors · ODbL",
               accuracy_note="Mapped land cover and footprints; vegetation and spectator detail are illustrative.")
    areas, occupied = SpatialGrid(320), SpatialGrid(160)
    def reserve(feature):
        occupied.add(feature["bounds"],feature)
    def free(x,y,r):
        for f in occupied.query([x-r,y-r,x+r,y+r]):
            paths = f["paths"]
            if inside_feature(x,y,paths) or any(point_segment_distance((x,y),a,b)<r for p in paths for a,b in zip(p,p[1:]+p[:1])):
                return False
        return road.circle_safe(x,y,r)
    def world_paths(paths):
        return [[[round((x-500)*track.map_scale+500,1),round((y-325)*track.map_scale+325,1)] for x,y in path] for path in paths]
    features = _SCENERY.get(track.id,{}).get("features",[])
    coasts = [path for raw in features if raw["kind"]=="coastline" for path in world_paths(raw["paths"])]
    coast_paths=coast_water(coasts,bounds)
    if coast_paths:
        f=dict(id="coastal_water",kind="water",paths=coast_paths,bounds=feature_bounds(coast_paths),name="Coastal water",coastal=True)
        env["water_bodies"].append(f);areas.add(f["bounds"],f);reserve(f)
    for raw in features:
        if raw["kind"] == "coastline":
            continue  # Open coastlines must never be closed across a circuit.
        paths = world_paths(raw["paths"])
        if raw["kind"] not in ("building","grandstand"):
            paths = [p for path in paths if len(p := clip_path(path,bounds)) >= 3]
        if not paths:
            continue
        bb = feature_bounds(paths)
        if bb[2]<bounds[0] or bb[0]>bounds[2] or bb[3]<bounds[1] or bb[1]>bounds[3]:
            continue
        f = dict(raw, paths=paths, bounds=bb)
        kind = f["kind"]
        if kind in ("building","grandstand"):
            if not road.polygon_safe(paths):
                continue  # Includes bridges/canopies that would obscure cars in top view.
            f["roof_color"] = rng.choice(("#53616b","#64717a","#46525d","#717778"))
            if theme in ("desert","dunes","coastal"):
                f["roof_color"] = rng.choice(("#9b8d73","#b2a58b","#727d83"))
            env["grandstands" if kind == "grandstand" else "buildings"].append(f)
            reserve(f)
        else:
            env["water_bodies" if kind == "water" else "terrain"].append(f)
            areas.add(bb,f)
            if kind in ("water","parking","pitch"):
                reserve(f)

    # Main spectator facilities follow the actual garage road, not lap station 20.
    garages = track.pit_garages
    if garages:
        g = garages[len(garages)//2]
        angle = math.atan2(g["ty"],g["tx"])
        for side, key, w,h,label in ((track.pit_side,"buildings",170,45,"PADDOCK"),
                                     (-track.pit_side,"grandstands",180,35,"MAIN STAND")):
            for distance in (95,125,165,210):
                x,y = g["x"]-g["ty"]*side*distance,g["y"]+g["tx"]*side*distance
                paths = [rectangle(x,y,w,h,angle)]
                if road.polygon_safe(paths) and free(x,y,math.hypot(w,h)/2+6):
                    f = dict(id=label, paths=paths,bounds=feature_bounds(paths),kind="grandstand" if key=="grandstands" else "building",
                             name=label,roof_color="#b54237" if track.id in ("italy","austria") else "#607a87")
                    env[key].append(f);reserve(f)
                    break

    # Stratified samples spread detail across the entire view, not a few random clusters.
    # Mapped woodland gets dense canopies; lawns stay open; deserts get scrub/stone.
    sample_bounds = bounds if track.id!='saudi' else [b['min_x']-1400,bounds[1],b['max_x']+3200,bounds[3]]
    step = max(44.0, math.sqrt((sample_bounds[2]-sample_bounds[0])*(sample_bounds[3]-sample_bounds[1])/20000))
    y = sample_bounds[1]
    while y < sample_bounds[3]:
        x = sample_bounds[0]
        while x < sample_bounds[2]:
            px,py = x+rng.uniform(.12,.88)*step,y+rng.uniform(.12,.88)*step
            local = [f for f in areas.query([px,py,px,py]) if inside_feature(px,py,f["paths"])]
            kinds = {f["kind"] for f in local}
            if "water" not in kinds and "parking" not in kinds and "pitch" not in kinds:
                woodland = "wood" in kinds
                planted = bool(kinds & {"grass","scrub"})
                probability = .96 if woodland else (.16 if planted else .015)
                if track.id=='saudi' and not planted:
                    probability=.003
                elif track.id=='saudi' and planted:
                    probability=.5
                # Sparse mapped grounds get region-appropriate small details, never invented forests.
                if rng.random() < probability:
                    r = rng.uniform(18,31) if woodland else rng.uniform(13,24)
                    if free(px,py,r*1.35+3):
                        leaf = next((f.get("leaf_type") for f in local if f.get("leaf_type")),"")
                        typ = "pine" if leaf=="needleleaved" else "deciduous"
                        if track.id in ("bahrain","saudi","miami","singapore","qatar","abudhabi"):
                            typ = "palm"
                        elif track.id in ("austria","belgium") and rng.random()<.65:
                            typ = "pine"
                        env["trees"].append(dict(x=round(px,1),y=round(py,1),r=round(r,1),type=typ,shade=rng.randrange(3),rotation=round(rng.random()*6.28,2)))
                elif rng.random() < .46:
                    r = rng.uniform(3,9)
                    if free(px,py,r+3):
                        typ = "scrub" if theme in ("desert","dunes") or (track.id=='saudi' and not planted) else "grass"
                        env["details"].append(dict(x=round(px,1),y=round(py,1),r=round(r,1),type=typ,shade=rng.randrange(3)))
            x += step
        y += step

    # Boats stay wholly within mapped marina water and clear of both road routes.
    if track.id in ("monaco","miami","abudhabi"):
        for water in env["water_bodies"]:
            if not water.get("coastal") and not any(n in water.get("name","").lower() for n in ("marina","hercule")):
                continue
            x0,y0,x1,y1 = water["bounds"]
            for _ in range(160):
                if len(env["yachts"]) >= 28:
                    break
                x,y = rng.uniform(max(x0,bounds[0]),min(x1,bounds[2])),rng.uniform(max(y0,bounds[1]),min(y1,bounds[3]))
                length,width,angle = rng.uniform(32,62),rng.uniform(11,18),.4
                corners = rectangle(x,y,length+10,width+10,angle)
                if (all(inside_feature(*p,water["paths"]) for p in corners)
                    and min(point_segment_distance((x,y),a,b) for path in water["paths"] for a,b in zip(path,path[1:]+path[:1]))>length/2+8
                    and road.circle_safe(x,y,length/2+8)
                    and all(math.hypot(x-v["x"],y-v["y"])>(length+v["len"])/2+12 for v in env["yachts"])):
                    env["yachts"].append(dict(x=round(x,1),y=round(y,1),len=round(length,1),width=round(width,1),angle=angle))
    if track.id=='saudi':
        from sim.jeddah_environment import enrich_jeddah
        enrich_jeddah(track,env,_SCENERY[track.id],road,areas,free,rng,bounds,world_paths,
                      inside_feature,feature_bounds,rectangle)
    _ENV_CACHE[track] = fingerprint,env
    return env
