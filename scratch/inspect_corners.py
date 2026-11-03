import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sim.tracks import get_track
from sim.physics import build_speed_envelope

for tid in ['monza', 'monaco', 'spa', 'silverstone', 'bahrain', 'montreal']:
    trk = get_track(tid)
    v_env, is_braking = build_speed_envelope(trk)
    print(f"=== {trk.name} ({len(trk.corners)} corners) ===")
    for c in trk.corners:
        st = c['station']
        k = trk.stations[st]['curv']
        v = v_env[st]
        is_hp = (k >= 0.012 or v <= 38.0)
        is_cn = (k >= 0.0062 and v <= 65.0)
        tag = "HAIRPIN" if is_hp else ("CORNER" if is_cn else "SWEEPER/KINK")
        if is_hp or c['number'] <= 4:
            print(f"  Turn {c['number']}: s={c['s_m']}m, curv={k:.5f}, v_apex={v:.1f} m/s ({v*3.6:.0f} km/h) -> {tag}")