"""Reference-map geometry; runtime uses only the Python standard library.

World coordinates use a common meter scale, so circuit widths, pit widths and
the car footprint have the same proportions on every circuit. Camera fitting is
separate from the geometry and never moves a corner to make a road look wider.
"""
from __future__ import annotations

import bisect
import hashlib
import json
import math
from pathlib import Path
from statistics import median

WORLD_UNITS_PER_M = 3.2
_LAYOUT_BYTES=Path(__file__).with_name('track_layouts.json').read_bytes()
GEOMETRY_REVISION=hashlib.sha256(_LAYOUT_BYTES).hexdigest()[:12]
LAYOUTS = json.loads(_LAYOUT_BYTES)


def resample(points, count, closed=False):
    pts = [tuple(p) for p in points]
    if closed:
        pts.append(pts[0])
    cum = [0.0]
    for a, b in zip(pts, pts[1:]):
        cum.append(cum[-1] + math.dist(a, b))
    result = []
    for k in range(count):
        target = cum[-1] * k / (count if closed else count - 1)
        i = min(len(pts) - 2, max(0, bisect.bisect_right(cum, target) - 1))
        f = (target - cum[i]) / max(cum[i + 1] - cum[i], 1e-9)
        result.append(tuple(pts[i][j] + f * (pts[i + 1][j] - pts[i][j]) for j in (0, 1)))
    return result, cum[-1]


def compile_centerline(track):
    layout = LAYOUTS[track.id]
    points, canvas_len = resample(layout['points'], track.NUM_STATIONS, closed=True)
    scale = track.length_m * WORLD_UNITS_PER_M / canvas_len
    track.map_scale = scale
    track.layout = layout
    track.geometry_source = layout['source']
    track.stations = [{'x': (x - 500.0) * scale + 500.0,
                       'y': (y - 325.0) * scale + 325.0} for x, y in points]
    widths=layout.get('width_profile_m')
    if widths:
        track.track_width_m=median(widths)
        track.track_width_px=track.track_width_m*WORLD_UNITS_PER_M
    for k,station in enumerate(track.stations):
        f=k*len(widths)/len(points) if widths else 0
        i=int(f)
        width=(widths[i%len(widths)]*(1-f+i)+widths[(i+1)%len(widths)]*(f-i)) if widths else track.track_width_m
        station['width_m']=width
        station['width_px']=width*WORLD_UNITS_PER_M
    return track.length_m * WORLD_UNITS_PER_M


def _bridge(start, end, start_tangent, end_tangent):
    h = min(math.dist(start, end) / 3.0, 18.0 * WORLD_UNITS_PER_M)
    a = (start[0] + start_tangent[0] * h, start[1] + start_tangent[1] * h)
    b = (end[0] - end_tangent[0] * h, end[1] - end_tangent[1] * h)
    return [tuple((1-t)**3*start[j] + 3*(1-t)**2*t*a[j] +
                  3*(1-t)*t*t*b[j] + t**3*end[j] for j in (0, 1))
            for t in (k / 12.0 for k in range(13))]


def _unit(a, b):
    d = max(math.dist(a, b), 1e-9)
    return ((b[0]-a[0])/d, (b[1]-a[1])/d)


def build_pit_geometry(track):
    layout = track.layout
    L = track.length_m
    track.pit_entry_s = layout['pit_entry_fraction'] * L
    track.pit_exit_s = layout['pit_exit_fraction'] * L
    track.pit_span_m = (track.pit_exit_s - track.pit_entry_s) % L
    points = [((x-500)*track.map_scale+500, (y-325)*track.map_scale+325)
              for x, y in layout['pit_points']]

    # Infer the actual side of the garage road from the drawing, not a global
    # assumption that every circuit's pits are on the driver's right.
    signs = []
    for p in points[len(points)//3:2*len(points)//3:4]:
        near = min(track.stations, key=lambda s: (s['x']-p[0])**2+(s['y']-p[1])**2)
        signs.append((p[0]-near['x'])*near['nx']+(p[1]-near['y'])*near['ny'])
    track.pit_side = 1 if median(signs) >= 0 else -1
    track.pit_width_m = layout.get('pit_width_m',8.0)  # fast lane + working apron
    track.pit_width_px = track.pit_width_m * WORLD_UNITS_PER_M
    entry = track.sample(track.pit_entry_s)
    exit = track.sample(track.pit_exit_s)
    points[0] = (entry['x'], entry['y'])
    exit_offset = track.lateral_to_px(.76 * track.pit_side,track.pit_exit_s)
    points[-1] = (exit['x']+exit['nx']*exit_offset, exit['y']+exit['ny']*exit_offset)

    # Mild smoothing removes digitizing corners; the endpoints remain exact.
    for _ in range(3):
        points = [points[0]] + [tuple(.2*points[k-1][j]+.6*points[k][j]+.2*points[k+1][j]
                    for j in (0, 1)) for k in range(1,len(points)-1)] + [points[-1]]
    n = 5
    first = _bridge(points[0], points[n], (entry['tx'],entry['ty']), _unit(points[n-1],points[n+1]))
    last = _bridge(points[-n-1], points[-1], _unit(points[-n-2],points[-n]), (exit['tx'],exit['ty']))
    points = first[:-1] + points[n:-n-1] + last
    points, track.pit_canvas_len = resample(points, 241)
    track.pit_length_m = track.pit_canvas_len / track.px_per_m
    # car.s remains the lap-distance coordinate. Convert physical pit travel to
    # this coordinate so shortcuts do not make cars visibly crawl or speed up.
    track.pit_distance_scale = track.pit_span_m / track.pit_length_m
    track.pit_px_per_m = track.pit_canvas_len / track.pit_span_m
    track.pit_stations = []
    for k, (x,y) in enumerate(points):
        tx,ty = _unit(points[max(0,k-1)],points[min(len(points)-1,k+1)])
        track.pit_stations.append({'x':x,'y':y,'tx':tx,'ty':ty})

    garage_lo,garage_hi=layout.get('garage_u_range',[.275,.725])
    garage_middle=(garage_lo+garage_hi)*.5
    spacing_px = min(24.0*track.px_per_m, track.pit_canvas_len*(garage_hi-garage_lo)/10)
    track.pit_garage_spacing_s = spacing_px / track.pit_px_per_m
    track.pit_box_s = (track.pit_entry_s + garage_middle*track.pit_span_m + 5*track.pit_garage_spacing_s) % L
    track.pit_garages = []
    for i in range(11):
        s = (track.pit_box_s-i*track.pit_garage_spacing_s) % L
        p = track.sample_pit(s)
        track.pit_garages.append({'index':i,'s_m':s,'x':p['x'],'y':p['y'],'tx':p['tx'],'ty':p['ty']})
    track.pit_speed_entry_u = max(.02,garage_lo-20/track.pit_length_m)
    track.pit_speed_exit_u = min(.98,garage_hi+30/track.pit_length_m)
    track.pit_exit_blend_s = (track.pit_exit_s + 110.0) % L
    track.pit_entry_blend_line = []
    track.pit_blend_line = []
    for k in range(25):
        for target, s in ((track.pit_entry_blend_line, track.pit_entry_s-100+100*k/24),
                          (track.pit_blend_line, track.pit_exit_s+110*k/24)):
            p = track.sample(s)
            off = track.lateral_to_px(.62*track.pit_side,s)
            target.append([p['x']+p['nx']*off,p['y']+p['ny']*off])
    track.pit_tunnel_u = layout.get('pit_tunnel_u')
    if track.id == 'abudhabi' and not track.pit_tunnel_u:
        # Locate the T1 crossing on the traced exit road; hide the car only
        # around that crossing, not for an arbitrary fraction of the pit visit.
        candidates = range(int(len(points)*.65), int(len(points)*.94))
        cross = min(candidates, key=lambda k: min((s['x']-points[k][0])**2+
                    (s['y']-points[k][1])**2 for s in track.stations))
        u = cross/(len(points)-1)
        track.pit_tunnel_u = [max(.6,u-.04),min(.98,u+.04)]
    all_points = [(s['x'],s['y']) for s in track.stations+track.pit_stations]
    margin = track.track_width_px+40
    track.bounds = {'min_x':min(p[0] for p in all_points)-margin,
                    'max_x':max(p[0] for p in all_points)+margin,
                    'min_y':min(p[1] for p in all_points)-margin,
                    'max_y':max(p[1] for p in all_points)+margin}


def pit_lateral_offset(track, s, apron=0.0):
    """The fast lane tapers onto both endpoints without a lateral teleport."""
    u = ((s-track.pit_entry_s) % track.length_m) / track.pit_span_m
    fade = min(1.0, max(0.0,u)*track.pit_length_m/30.0,
               max(0.0,1-u)*track.pit_length_m/30.0)
    return (-2.8*(1-apron)+8.6*apron)*track.pit_side*fade


def in_pit_tunnel(track, car):
    if not car.in_pits or not track.pit_tunnel_u:
        return False
    u = ((car.s-track.pit_entry_s) % track.length_m)/track.pit_span_m
    return track.pit_tunnel_u[0] <= u <= track.pit_tunnel_u[1]


def build_start_grid(track, count=22):
    """Use the FIA start landmark and 8m stagger (16m in the same column).

    Start/control lines are independently digitized. Never move a start line
    or compress a grid to conceal a geometry error.
    """
    offset=track.layout['start_line_fraction']*track.length_m
    pitch=8.0
    slots=[track.sample(offset-10-i*pitch) for i in range(count)]
    heading=math.atan2(slots[0]['ty'],slots[0]['tx'])
    bend=max(abs((math.atan2(p['ty'],p['tx'])-heading+math.pi)%(2*math.pi)-math.pi) for p in slots)
    track.start_line_s = float(offset)
    track.grid_spacing_m = float(pitch)
    track.grid_heading_spread = bend
    track.grid_pole_side = int(track.layout['pole_side'])
    line = track.sample(track.start_line_s)
    track.start_line = {'x':line['x'],'y':line['y'],
                        'heading':math.atan2(line['ty'],line['tx']),
                        'width_px':line['width_px']}
    track.grid_boxes = []
    for i, point in enumerate(slots):
        distance = 10.0+i*pitch
        progress = offset-distance
        d = .62*track.grid_pole_side*(1 if i%2==0 else -1)
        lateral = track.lateral_to_px(d,progress)
        track.grid_boxes.append({'pos':i+1,'slot_offset':distance,
            'progress_m':progress,'s_m':progress % track.length_m,'d':d,
            'x':point['x']+point['nx']*lateral,
            'y':point['y']+point['ny']*lateral,
            'heading':math.atan2(point['ty'],point['tx'])})
