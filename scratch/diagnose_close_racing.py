"""Measure contact corrections without loading or writing a saved career."""
import json
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sim.data import clone_initial_roster
from sim.physics import RaceSession, _sat_obb_penetration
from sim.track_geometry import in_pit_tunnel
from sim.tracks import COMPILED_TRACKS


for track_id in ("australia", "monaco", "italy"):
    random.seed(87)
    teams, drivers = clone_initial_roster()
    track = next(t for t in COMPILED_TRACKS if t.id == track_id)
    race = RaceSession(track, {t["id"]: t for t in teams},
                       [d for d in drivers if d.get("team_id")], 0, 0, "mclaren")
    previous = {}
    metrics = dict(world_only_corrections=0, max_world_reset_m=0, backward_steps=0,
                   lane_reversals=0, max_lateral_step=0, max_backward_m=0,
                   unresolved_overlaps=0, max_abs_lane=0)
    for tick in range(750):
        race.step(.05, lambda *_: None)
        if not race.lights_out:
            continue
        for c in race.cars:
            if c.in_pits or c.dnf or c.spin_timer > 0:
                previous.pop(c.driver_id, None)
                continue
            sample = track.sample(c.s)
            metrics["max_abs_lane"] = max(metrics["max_abs_lane"], abs(c.d))
            lateral = track.lateral_to_px(c.d, c.s)
            reset = math.hypot(c.x - sample["x"] - sample["nx"] * lateral,
                               c.y - sample["y"] - sample["ny"] * lateral) / track.px_per_m
            if reset > .025:
                metrics["world_only_corrections"] += 1
                metrics["max_world_reset_m"] = max(metrics["max_world_reset_m"], reset)
            if c.driver_id in previous:
                dist, lane, target, last_delta = previous[c.driver_id]
                ds = c.total_dist - dist
                delta = c.target_d - target
                if ds < -.01:
                    metrics["backward_steps"] += 1
                    metrics["max_backward_m"] = max(metrics["max_backward_m"], -ds)
                if delta * last_delta < -.01:
                    metrics["lane_reversals"] += 1
                metrics["max_lateral_step"] = max(metrics["max_lateral_step"], abs(c.d - lane))
            else:
                delta = 0
            previous[c.driver_id] = c.total_dist, c.d, c.target_d, delta
        active = [c for c in race.cars if not c.dnf and not c.in_pits and c.spin_timer <= 0]
        for i, c in enumerate(active):
            for other in active[i + 1:]:
                if in_pit_tunnel(track, c) != in_pit_tunnel(track, other):
                    continue
                gap = min((c.s - other.s) % track.length_m, (other.s - c.s) % track.length_m)
                if track.has_overpass and gap > 250:
                    continue
                if _sat_obb_penetration(c, other) is not None:
                    metrics["unresolved_overlaps"] += 1
    print(track_id, json.dumps(metrics), flush=True)
