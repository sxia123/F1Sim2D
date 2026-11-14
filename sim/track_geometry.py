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
    h = min(math.dist(start, end) * 0.42, 32.0 * WORLD_UNITS_PER_M)
    a = (start[0] + start_tangent[0] * h, start[1] + start_tangent[1] * h)
    b = (end[0] - end_tangent[0] * h, end[1] - end_tangent[1] * h)
    return [tuple((1-t)**3*start[j] + 3*(1-t)**2*t*a[j] +
                  3*(1-t)*t*t*b[j] + t**3*end[j] for j in (0, 1))
            for t in (k / 24.0 for k in range(25))]


def _unit(a, b):
    d = max(math.dist(a, b), 1e-9)
    return ((b[0]-a[0])/d, (b[1]-a[1])/d)


def _smoothstep(u: float) -> float:
    u = max(0.0, min(1.0, u))
    return u * u * (3.0 - 2.0 * u)


def _clear_close_parallel_pit(track, points, min_clearance_px: float, clear_lo: float = 0.08, clear_hi: float = 0.92):
    """Smoothly keep close-parallel working pit sections outside main track asphalt/verge."""
    n = len(points)
    tun = track.pit_tunnel_u
    nudges = []
    for k, (x, y) in enumerate(points):
        u = k / max(1, n - 1)
        if tun and (tun[0] - 0.12 <= u <= tun[1] + 0.12):
            nudges.append((0.0, 0.0))
            continue
        w_in = _smoothstep(u / max(clear_lo, 0.03)) if u < clear_lo else 1.0
        w_out = _smoothstep((1.0 - u) / max(1.0 - clear_hi, 0.03)) if u > clear_hi else 1.0
        edge_w = min(w_in, w_out)
        near = min(track.stations, key=lambda s: (s['x'] - x) ** 2 + (s['y'] - y) ** 2)
        tx, ty = _unit(points[max(0, k - 1)], points[min(n - 1, k + 1)])
        if tx * near['tx'] + ty * near['ty'] < 0.60:
            nudges.append((0.0, 0.0))
            continue
        signed_d = ((x - near['x']) * near['nx'] + (y - near['y']) * near['ny']) * track.pit_side
        req_d = near['width_px'] * 0.5 + min_clearance_px
        if -near['width_px'] * 0.65 < signed_d < req_d:
            push = (req_d - signed_d) * edge_w
            nudges.append((near['nx'] * track.pit_side * push, near['ny'] * track.pit_side * push))
        else:
            nudges.append((0.0, 0.0))
    for _ in range(6):
        nxt = [(0.0, 0.0)]
        for k in range(1, n - 1):
            nxt.append((
                0.25 * nudges[k - 1][0] + 0.50 * nudges[k][0] + 0.25 * nudges[k + 1][0],
                0.25 * nudges[k - 1][1] + 0.50 * nudges[k][1] + 0.25 * nudges[k + 1][1],
            ))
        nxt.append((0.0, 0.0))
        nudges = nxt
    return [(points[k][0] + nudges[k][0], points[k][1] + nudges[k][1]) for k in range(n)]


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
    # Dual-lane FIA pit lane: fast lane (2+ cars clear of pit boxes) + working garage apron.
    track.pit_width_m = layout.get('pit_width_m', 10.0)
    track.pit_width_px = track.pit_width_m * WORLD_UNITS_PER_M
    track.pit_fast_offset_px = -1.6 * WORLD_UNITS_PER_M
    track.pit_apron_offset_px = 3.0 * WORLD_UNITS_PER_M
    entry = track.sample(track.pit_entry_s)
    exit = track.sample(track.pit_exit_s)
    points[0] = (entry['x'], entry['y'])
    exit_offset = track.lateral_to_px(.76 * track.pit_side,track.pit_exit_s)
    points[-1] = (exit['x']+exit['nx']*exit_offset, exit['y']+exit['ny']*exit_offset)

    # Mild smoothing removes digitizing corners; the endpoints remain exact.
    for _ in range(3):
        points = [points[0]] + [tuple(.2*points[k-1][j]+.6*points[k][j]+.2*points[k+1][j]
                    for j in (0, 1)) for k in range(1,len(points)-1)] + [points[-1]]
    points, raw_len = resample(points, 241)
    track.pit_tunnel_u = layout.get('pit_tunnel_u')
    if track.id == 'abudhabi' and not track.pit_tunnel_u:
        candidates = range(int(len(points) * .65), int(len(points) * .94))
        cross = min(candidates, key=lambda k: min((s['x'] - points[k][0]) ** 2 +
                    (s['y'] - points[k][1]) ** 2 for s in track.stations))
        u = cross / (len(points) - 1)
        track.pit_tunnel_u = [max(.6, u - .04), min(.98, u + .04)]
    garage_lo,garage_hi=layout.get('garage_u_range',[.275,.725])
    clear_lo = min(0.08, max(0.03, garage_lo * 0.65))
    clear_hi = max(0.88, min(0.955, garage_hi + 22.0 * WORLD_UNITS_PER_M / max(raw_len, 1.0)))
    points = _clear_close_parallel_pit(track, points, track.pit_width_px * 0.5 + 2.5, clear_lo, clear_hi)

    cum = [0.0]
    for a, b in zip(points, points[1:]):
        cum.append(cum[-1] + math.dist(a, b))
    tot = max(cum[-1], 1e-6)
    in_target = min(40.0 * WORLD_UNITS_PER_M, tot * 0.14)
    out_target = min(50.0 * WORLD_UNITS_PER_M, tot * 0.16)
    i_in = next((k for k, d in enumerate(cum) if d >= in_target), 5)
    i_in = max(5, min(i_in, int(max(0.04, garage_lo - 0.015) * (len(points) - 1)), len(points) // 4))
    i_out_len = next((k for k in range(len(cum) - 1, -1, -1) if tot - cum[k] >= out_target), len(points) - 6)
    i_out = max(i_out_len, int((garage_hi + 0.015) * (len(points) - 1)), 3 * len(points) // 4)
    i_out = min(len(points) - 6, i_out)
    first = _bridge(points[0], points[i_in], (entry['tx'], entry['ty']), _unit(points[i_in - 2], points[min(len(points) - 1, i_in + 2)]))
    last = _bridge(points[i_out], points[-1], _unit(points[max(0, i_out - 2)], points[i_out + 2]), (exit['tx'], exit['ty']))
    points = first[:-1] + points[i_in:i_out] + last
    points, track.pit_canvas_len = resample(points, 241)
    track.pit_length_m = track.pit_canvas_len / track.px_per_m
    # car.s remains the lap-distance coordinate. Convert physical pit travel to
    # this coordinate so shortcuts do not make cars visibly crawl or speed up.
    track.pit_distance_scale = track.pit_span_m / track.pit_length_m
    track.pit_px_per_m = track.pit_canvas_len / track.pit_span_m
    track.pit_stations = []
    for k, (x,y) in enumerate(points):
        if k == 0:
            tx, ty = entry['tx'], entry['ty']
        elif k == len(points) - 1:
            tx, ty = exit['tx'], exit['ty']
        else:
            tx,ty = _unit(points[max(0,k-1)],points[min(len(points)-1,k+1)])
        track.pit_stations.append({'x':x,'y':y,'tx':tx,'ty':ty})
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
    fwd_corners = sorted(((c['s_m'] - track.pit_exit_s) % L) for c in getattr(track, 'corners', []))
    next_corner_m = fwd_corners[0] if fwd_corners else 140.0
    track.pit_exit_blend_dist_m = min(115.0, max(58.0, next_corner_m * 0.78))
    track.pit_exit_blend_s = (track.pit_exit_s + track.pit_exit_blend_dist_m) % L
    track.pit_entry_blend_line = []
    track.pit_blend_line = []
    for k in range(25):
        u = k / 24.0
        s_in = track.pit_entry_s - 100.0 + 100.0 * u
        p_in = track.sample(s_in)
        off_in = track.lateral_to_px(.62 * track.pit_side, s_in)
        track.pit_entry_blend_line.append([p_in['x'] + p_in['nx'] * off_in, p_in['y'] + p_in['ny'] * off_in])
        s_out = track.pit_exit_s + track.pit_exit_blend_dist_m * u
        p_out = track.sample(s_out)
        d_out = (1.0 - _smoothstep(u)) * (0.76 * track.pit_side) + _smoothstep(u) * p_out.get('racing_line_d', 0.0)
        off_out = track.lateral_to_px(d_out, s_out)
        track.pit_blend_line.append([p_out['x'] + p_out['nx'] * off_out, p_out['y'] + p_out['ny'] * off_out])
    all_points = [(s['x'],s['y']) for s in track.stations+track.pit_stations]
    margin = max(track.track_width_px, track.pit_width_px) + 40
    track.bounds = {'min_x':min(p[0] for p in all_points)-margin,
                    'max_x':max(p[0] for p in all_points)+margin,
                    'min_y':min(p[1] for p in all_points)-margin,
                    'max_y':max(p[1] for p in all_points)+margin}


def pit_lateral_offset(track, s, apron=0.0):
    """The fast lane tapers onto both endpoints without a lateral teleport."""
    u = ((s-track.pit_entry_s) % track.length_m) / track.pit_span_m
    taper_m = min(36.0, track.pit_length_m * 0.20)
    in_u = max(0.0, u) * track.pit_length_m / max(taper_m, 1.0)
    out_u = max(0.0, 1.0 - u) * track.pit_length_m / max(taper_m, 1.0)
    fade = min(_smoothstep(in_u), _smoothstep(out_u))
    fast_off = getattr(track, 'pit_fast_offset_px', -5.12)
    apron_off = getattr(track, 'pit_apron_offset_px', 9.60)
    return (fast_off*(1-apron)+apron_off*apron)*track.pit_side*fade


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
