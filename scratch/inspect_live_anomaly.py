"""Collect live frames with full telemetry debug."""
import json
import math
import time
import urllib.request

def main():
    print("Collecting 100 live frames...")
    frames = []
    last_tick_num = -1
    while len(frames) < 100:
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

    prev_by_id = {}
    for f_idx, f in enumerate(frames):
        cars = f.get("cars", [])
        for c in cars:
            cid = c["id"]
            if cid in prev_by_id:
                p_c = prev_by_id[cid]
                dh = (c["h"] - p_c["h"] + math.pi) % (2.0 * math.pi) - math.pi
                dh_deg = math.degrees(dh)
                dv_kph = c.get("kph", 0) - p_c.get("kph", 0)
                
                if abs(dh_deg) > 16.0 or (abs(dv_kph) > 30.0 and p_c.get("kph", 0) > 30):
                    print(f"ANOMALY f={f_idx} tick={f.get('tick')} {c['code']}:")
                    print(f"  h: {p_c['h']:.4f} -> {c['h']:.4f} (dh={dh_deg:+.1f} deg)")
                    print(f"  kph: {p_c.get('kph')} -> {c.get('kph')} (dv={dv_kph:+.1f} km/h)")
                    print(f"  pos: ({p_c.get('x')}, {p_c.get('y')}) -> ({c.get('x')}, {c.get('y')})")
                    print(f"  prev: {p_c}")
                    print(f"  curr: {c}")
                    print("-" * 50)
            prev_by_id[cid] = c

if __name__ == "__main__":
    main()

