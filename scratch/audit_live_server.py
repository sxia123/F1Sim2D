"""Collect live frames from running server and verify on-track smoothness, heading, and zero SAT clipping."""
import json
import math
import time
import urllib.request

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

def main():
    print("Collecting 150 consecutive live frames from http://127.0.0.1:8080/api/tick...")
    frames = []
    last_tick_num = -1
    while len(frames) < 150:
        try:
            req = urllib.request.urlopen("http://127.0.0.1:8080/api/tick", timeout=2)
            data = json.loads(req.read().decode())
            t_num = data.get("tick", -1)
            if t_num != last_tick_num:
                frames.append(data)
                last_tick_num = t_num
        except Exception as e:
            print("Error polling:", e)
        time.sleep(0.02)

    circuit = frames[0].get('circuit_name')
    track_id = frames[0].get('track_id')
    lap = frames[0].get('lap')
    print(f"Recorded {len(frames)} frames. Circuit: {circuit} ({track_id}) | Lap: {lap}. Auditing on-track racing...")

    prev_by_id = {}
    clipping_events = []
    heading_whips = []
    speed_jumps = []

    for f_idx, f in enumerate(frames):
        cars = f.get("cars", [])
        vis = [c for c in cars if c.get("vis", True)]
        
        # 1. SAT collision check between all visible cars
        corners = {c["id"]: obb_corners(c["x"], c["y"], c["h"]) for c in vis}
        for i in range(len(vis)):
            c1 = vis[i]
            for j in range(i + 1, len(vis)):
                c2 = vis[j]
                if c1.get("in_pit") != c2.get("in_pit"):
                    continue
                dx = c2["x"] - c1["x"]
                dy = c2["y"] - c1["y"]
                if dx * dx + dy * dy > 225.0:
                    continue
                hit, pen = sat_test(corners[c1["id"]], c1["h"], corners[c2["id"]], c2["h"])
                if hit and pen > 0.05:
                    clipping_events.append((f_idx, c1["code"], c2["code"], round(pen, 3)))

        # 2. Heading and speed deltas across frames for on-track racing cars
        for c in vis:
            cid = c["id"]
            if cid in prev_by_id:
                p_c = prev_by_id[cid]
                # Only audit active on-track cars (exclude pit stops and spin states)
                if not c.get("in_pit", False) and not p_c.get("in_pit", False) and c.get("kph", 0) > 40:
                    dh = (c["h"] - p_c["h"] + math.pi) % (2.0 * math.pi) - math.pi
                    dh_deg = math.degrees(dh)
                    # Flag unnatural heading twitch if > 15.0 deg in a single 50ms tick
                    if abs(dh_deg) > 15.0:
                        heading_whips.append((f_idx, c["code"], round(dh_deg, 1), round(p_c["h"], 3), round(c["h"], 3)))

                    dv_kph = c.get("kph", 0) - p_c.get("kph", 0)
                    # Flag speed jump if > 25 km/h in 50ms
                    if abs(dv_kph) > 25.0:
                        speed_jumps.append((f_idx, c["code"], round(dv_kph, 1), p_c.get("kph"), c.get("kph")))

            prev_by_id[cid] = c

    print("\n================ LIVE AUDIT RESULTS ================")
    print(f"Total Frames Analyzed: {len(frames)}")
    print(f"SAT Drawn Box Overlaps (>0.05px): {len(clipping_events)}")
    print(f"Heading Whips (>15 deg/tick): {len(heading_whips)}")
    print(f"Speed Jumps (>25 km/h/tick): {len(speed_jumps)}")
    if clipping_events:
        print("Clipping samples:", clipping_events[:5])
    if heading_whips:
        print("Heading whip samples:", heading_whips[:5])
    if speed_jumps:
        print("Speed jump samples:", speed_jumps[:5])
    print("====================================================")

if __name__ == "__main__":
    main()
