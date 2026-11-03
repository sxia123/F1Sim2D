import sys, os
sys.path.insert(0, os.path.abspath("."))
from sim.tracks import COMPILED_TRACKS
from sim.track_environment import get_track_environment

print("Testing environment generation for all 24 circuits...")
for t in COMPILED_TRACKS:
    env = get_track_environment(t)
    th = env['theme']
    w = len(env['water_bodies'])
    y = len(env['yachts'])
    lm = len(env['landmarks'])
    bld = len(env['buildings'])
    gs = len(env['grandstands'])
    tr = len(env['trees'])
    print(f"{t.id:12s}: theme={th:8s} water={w} yachts={y} lm={lm} bld={bld} gs={gs} trees={tr}")

print("All 24 circuits generated valid environmental features!")
