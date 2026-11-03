"""Watch and audit a race segment for smoothness, clipping, and bumping."""
import math
import pathlib
import sys

ROOT = pathlib.Path(r"c:\Coding\F1Sim2D")
sys.path.insert(0, str(ROOT))

from sim.data import clone_initial_roster
from sim.physics import (
    CAR_LEN_PX,
    CAR_WID_PX,
    RaceSession,
    _sat_obb_penetration,
)
from sim.tracks import COMPILED_TRACKS

# Drawn car dimensions at carScale 0.68
DRAWN_HALF_L = 11.866 * 0.5
DRAWN_HALF_W = 5.712 * 0.5
DRAWN_CENTER_FWD = 0.255

def obb_corners(x: float, y: float, heading: float, half_l=DRAWN_HALF_L, half_w=DRAWN_HALF_W, fwd_off=DRAWN_CENTER_FWD):
    ch, sh = math.cos(heading), math.sin(heading)
    cx, cy = x + ch * fwd_off, y + sh * fwd_off
    ux, uy = ch * half_l, sh * half_l
    vx, vy = -sh * half_w, ch * half_w
    return [
        (cx + ux + vx, cy + uy + vy),
        (cx + ux - vx, cy + uy - vy),
        (cx - ux - vx, cy - uy - vy),
        (cx - ux + vx, cy - uy + vy),
    ]

def sat_test(pts1, h1, pts2, h2):
    axes = [
        (math.cos(h1), math.sin(h1)),
        (-math.sin(h1), math.cos(h1)),
        (math.cos(h2), math.sin(h2)),
        (-math.sin(h2), math.cos(h2)),
    ]
    min_pen = 999.0
    for ax, ay in axes:
        p1 = [px * ax + py * ay for px, py in pts1]
        p2 = [px * ax + py * ay for px, py in pts2]
        pen = min(max(p1), max(p2)) - max(min(p1), min(p2))
        if pen <= 0.0:
            return False, 0.0
        if pen < min_pen:
            min_pen = pen
    return True, min_pen

def audit_race(track_id: str, num_ticks: int = 1200):
    tracks = {t.id: t for t in COMPILED_TRACKS}
    trk = tracks[track_id]
    teams_list, drivers_list = clone_initial_roster()
    teams_by_id = {t["id"]: t for t in teams_list}
    drivers = [d for d in drivers_list if d.get("team_id")]

    race = RaceSession(trk, teams_by_id, drivers, 0.0, 0.1, "mercedes", is_sprint=False)

    events = []
    def on_ev(cat, msg):
        events.append((race.race_clock, cat, msg))

    # Telemetry history to inspect smoothness:
    # prev_state[driver_id] = (s, d, v, heading, x, y)
    prev = {}
    
    clipping_records = []
    bumping_records = []
    smoothness_records = []

    dt = 0.05
    for tick in range(num_ticks):
        race.step(dt, on_ev)
        vis = [c for c in race.cars if (not c.dnf) or (c.dnf_timer > 0.0)]

        # 1. Check for CLIPPING (exact 2D SAT OBB overlap)
        corners = {c.driver_id: obb_corners(c.x, c.y, c.heading) for c in vis}
        for i in range(len(vis)):
            c1 = vis[i]
            for j in range(i + 1, len(vis)):
                c2 = vis[j]
                dx, dy = c2.x - c1.x, c2.y - c1.y
                if dx * dx + dy * dy > 225.0:
                    continue
                # Overpass check (Suzuka)
                arc_fwd = (c1.s - c2.s) % trk.length_m
                if trk.has_overpass and min(arc_fwd, trk.length_m - arc_fwd) > 250.0:
                    continue
                hit, pen = sat_test(corners[c1.driver_id], c1.heading, corners[c2.driver_id], c2.heading)
                if hit and pen > 0.05:
                    clipping_records.append({
                        "t": round(race.race_clock, 2),
                        "tick": tick,
                        "c1": c1.code,
                        "c2": c2.code,
                        "pen": round(pen, 3),
                        "c1_d": round(c1.d, 2),
                        "c2_d": round(c2.d, 2),
                        "c1_s": round(c1.s, 1),
                        "c2_s": round(c2.s, 1),
                        "in_pits": f"{c1.in_pits}/{c2.in_pits}",
                    })

        # 2. Check for SMOOTHNESS & BUMPING across consecutive ticks for each car
        for c in vis:
            if c.driver_id in prev:
                ps, pd, pv, ph, px, py = prev[c.driver_id]
                ds = (c.s - ps + 0.5 * trk.length_m) % trk.length_m - 0.5 * trk.length_m
                dd = c.d - pd
                dv = c.v - pv
                # Angle delta normalized to [-pi, pi]
                dh = (c.heading - ph + math.pi) % (2.0 * math.pi) - math.pi
                d_dist = math.hypot(c.x - px, c.y - py)

                # Anomaly A: Negative longitudinal jump (backwards snap / stutter)
                if ds < -0.05 and c.pit_phase != "STOPPED":
                    smoothness_records.append({
                        "type": "BACKWARD_JUMP",
                        "t": round(race.race_clock, 2),
                        "code": c.code,
                        "ds": round(ds, 3),
                        "v": round(c.v, 1),
                        "s": round(c.s, 1),
                    })

                # Anomaly B: Sudden lateral jerk / snap (delta d > 0.15 in a single 50ms tick = > 3.0 units/sec)
                if abs(dd) > 0.15 and c.spin_timer <= 0.0 and not c.in_pits:
                    bumping_records.append({
                        "type": "LATERAL_SNAP",
                        "tick": tick,
                        "t": round(race.race_clock, 2),
                        "code": c.code,
                        "dd": round(dd, 3),
                        "d": round(c.d, 2),
                        "s": round(c.s, 1),
                    })

                # Anomaly C: Sudden heading jerk (delta heading > 0.25 rad (~14 deg) in 50ms)
                if abs(dh) > 0.25 and c.spin_timer <= 0.0:
                    smoothness_records.append({
                        "type": "HEADING_SNAP",
                        "t": round(race.race_clock, 2),
                        "code": c.code,
                        "dh_deg": round(math.degrees(dh), 1),
                        "heading": round(c.heading, 3),
                        "s": round(c.s, 1),
                    })

                # Anomaly D: Acceleration / braking jerk (|dv / dt| > 60 m/s^2)
                accel = dv / dt
                if abs(accel) > 60.0 and c.pit_phase != "STOPPED" and c.spin_timer <= 0.0:
                    smoothness_records.append({
                        "type": "ACCEL_JERK",
                        "t": round(race.race_clock, 2),
                        "code": c.code,
                        "accel": round(accel, 1),
                        "v": round(c.v, 1),
                        "s": round(c.s, 1),
                    })

            prev[c.driver_id] = (c.s, c.d, c.v, c.heading, c.x, c.y)

    print(f"\n========================================================")
    print(f"RACE AUDIT REPORT: {track_id.upper()} ({num_ticks} ticks = {num_ticks*0.05:.1f}s)")
    print(f"========================================================")
    print(f"Total Events: {len(events)} (Overtakes: {sum(1 for e in events if e[1] == 'OVERTAKE')}, Incidents: {sum(1 for e in events if e[1] == 'INCIDENT')})")
    print(f"Clipping Overlaps (>0.05px): {len(clipping_records)}")
    print(f"Bumping Lateral Snaps (|dd|>0.15): {len(bumping_records)}")
    print(f"Smoothness Anomalies: {len(smoothness_records)}")

    if clipping_records:
        print("\n--- SAMPLE CLIPPING OVERLAPS ---")
        for r in clipping_records[:10]:
            print(f"  t={r['t']}s: {r['c1']} vs {r['c2']} | pen={r['pen']}px | s=({r['c1_s']}, {r['c2_s']}) | d=({r['c1_d']}, {r['c2_d']}) | pits={r['in_pits']}")

    if bumping_records:
        print("\n--- SAMPLE BUMPING LATERAL SNAPS ---")
        for r in bumping_records[:10]:
            print(f"  tick={r.get('tick')} t={r['t']}s: {r['code']} | dd={r['dd']} | new_d={r['d']} | s={r['s']}")

    if smoothness_records:
        print("\n--- SAMPLE SMOOTHNESS ANOMALIES ---")
        for r in smoothness_records[:10]:
            print(f"  t={r['t']}s [{r['type']}]: {r['code']} | {r}")

if __name__ == "__main__":
    track = sys.argv[1] if len(sys.argv) > 1 else "monaco"
    ticks = int(sys.argv[2]) if len(sys.argv) > 2 else 1200
    audit_race(track, ticks)

