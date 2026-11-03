"""Comprehensive multi-track full-lap audit script."""
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

DRAWN_HALF_L = 11.866 * 0.5
DRAWN_HALF_W = 5.712 * 0.5
DRAWN_CENTER_FWD = 0.255

def obb_corners(x: float, y: float, heading: float):
    ch, sh = math.cos(heading), math.sin(heading)
    cx, cy = x + ch * DRAWN_CENTER_FWD, y + sh * DRAWN_CENTER_FWD
    ux, uy = ch * DRAWN_HALF_L, sh * DRAWN_HALF_L
    vx, vy = -sh * DRAWN_HALF_W, ch * DRAWN_HALF_W
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

def audit_track(track_id: str, ticks: int = 1800):
    tracks = {t.id: t for t in COMPILED_TRACKS}
    trk = tracks[track_id]
    t_list, d_list = clone_initial_roster()
    race = RaceSession(trk, {t['id']: t for t in t_list}, [d for d in d_list if d.get('team_id')], 0.0, 0.1, 'mercedes')

    events = []
    def on_ev(cat, msg):
        events.append((race.race_clock, cat, msg))

    prev = {}
    clipping_count = 0
    lateral_snaps = 0
    heading_snaps = 0
    backward_jumps = 0
    slamming_oscillations = 0
    overtake_count = 0
    incident_count = 0

    accel_history = {}  # driver_id -> list of float

    dt = 0.05
    for tick in range(ticks):
        race.step(dt, on_ev)
        vis = [c for c in race.cars if (not c.dnf) or (c.dnf_timer > 0.0)]

        # 1. 2D SAT OBB non-overlap check
        corners = {c.driver_id: obb_corners(c.x, c.y, c.heading) for c in vis}
        for i in range(len(vis)):
            c1 = vis[i]
            for j in range(i + 1, len(vis)):
                c2 = vis[j]
                dx, dy = c2.x - c1.x, c2.y - c1.y
                if dx * dx + dy * dy > 225.0:
                    continue
                arc_fwd = (c1.s - c2.s) % trk.length_m
                if trk.has_overpass and min(arc_fwd, trk.length_m - arc_fwd) > 250.0:
                    continue
                hit, pen = sat_test(corners[c1.driver_id], c1.heading, corners[c2.driver_id], c2.heading)
                if hit and pen > 0.05:
                    clipping_count += 1

        # 2. Smoothness and kinematics checks
        for c in vis:
            if c.driver_id in prev:
                ps, pd, pv, ph, px, py = prev[c.driver_id]
                ds = (c.s - ps + 0.5 * trk.length_m) % trk.length_m - 0.5 * trk.length_m
                dd = c.d - pd
                dv = c.v - pv
                dh = (c.heading - ph + math.pi) % (2.0 * math.pi) - math.pi
                accel = dv / dt

                # Anomaly: Backward jump
                if ds < -0.05 and c.pit_phase != "STOPPED" and not c.dnf and c.spin_timer <= 0.0:
                    backward_jumps += 1

                # Anomaly: Lateral snap on active car
                if abs(dd) > 0.15 and not c.dnf and c.spin_timer <= 0.0 and not c.in_pits:
                    lateral_snaps += 1

                # Anomaly: Heading snap
                if abs(dh) > 0.25 and not c.dnf and c.spin_timer <= 0.0:
                    heading_snaps += 1

                # Anomaly: Ping-pong slamming oscillation (rapid alternating between heavy acceleration and heavy braking)
                hist = accel_history.setdefault(c.driver_id, [])
                hist.append(accel)
                if len(hist) > 5:
                    hist.pop(0)
                    # Check for sign reversals: accel > 8 -> brake < -25 -> accel > 8
                    has_osc = False
                    for k in range(len(hist) - 2):
                        if (hist[k] > 8.0 and hist[k+1] < -25.0 and hist[k+2] > 8.0) or \
                           (hist[k] < -25.0 and hist[k+1] > 8.0 and hist[k+2] < -25.0):
                            has_osc = True
                            break
                    if has_osc and not c.dnf and c.spin_timer <= 0.0:
                        slamming_oscillations += 1

            prev[c.driver_id] = (c.s, c.d, c.v, c.heading, c.x, c.y)

    for ev in events:
        cat = ev[1]
        msg = ev[2]
        if cat == "OVERTAKE":
            overtake_count += 1
        elif cat in ("INCIDENT", "CRASH"):
            incident_count += 1

    total_damaged_cars = sum(1 for c in race.cars if c.wing_damage > 0.001 or c.repair_cost_m > 0.0)

    return {
        "track": track_id,
        "ticks": ticks,
        "seconds": round(ticks * 0.05, 1),
        "overtakes": overtake_count,
        "incidents": incident_count,
        "damaged_cars": total_damaged_cars,
        "clipping_overlaps": clipping_count,
        "lateral_snaps": lateral_snaps,
        "heading_snaps": heading_snaps,
        "backward_jumps": backward_jumps,
        "slamming_oscillations": slamming_oscillations,
    }

if __name__ == "__main__":
    tracks_to_audit = ["japan", "canada", "britain", "belgium", "monaco"]
    print("=" * 90)
    print("STARTING FULL-LAP MULTI-TRACK COMPREHENSIVE PHYSICS AUDIT")
    print("=" * 90)
    results = []
    for t in tracks_to_audit:
        res = audit_track(t, 1800)
        results.append(res)
        print(f"Track: {res['track'].upper():<9} | Overtakes: {res['overtakes']:<3} | Incidents: {res['incidents']:<2} | Clips: {res['clipping_overlaps']:<2} | LatSnaps: {res['lateral_snaps']:<2} | HeadingSnaps: {res['heading_snaps']:<2} | BackJumps: {res['backward_jumps']:<2} | SlammingOsc: {res['slamming_oscillations']:<2} | DamagedCars: {res['damaged_cars']}")
    print("=" * 90)
    print("ALL FULL-LAP TRACK AUDITS COMPLETED!")
    print("=" * 90)
