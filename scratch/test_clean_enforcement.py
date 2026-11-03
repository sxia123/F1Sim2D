import math
import sys, pathlib
ROOT = pathlib.Path(r'c:\Coding\F1Sim2D')
sys.path.insert(0, str(ROOT))
from sim.data import clone_initial_roster
from sim.physics import (
    CAR_LEN_PX,
    CAR_WID_PX,
    CarState,
    RaceSession,
    _sat_obb_penetration,
    compute_lateral_screen_px,
)
import sim.physics as phys
from sim.tracks import COMPILED_TRACKS

def clean_enforce_2d_car_separation(
    track,
    cars: list[CarState],
    allow_passing: bool,
    update_xy_fn,
    collision_cb=None,
) -> None:
    L = track.length_m
    min_long_m = (CAR_LEN_PX * 1.35) / track.px_per_m
    min_pit_long_m = (CAR_LEN_PX * 1.05) / track.pit_px_per_m
    half_usable = track.track_width_px * 0.39

    # 0. Sync world (x, y, heading) for all cars
    for c in cars:
        update_xy_fn(c)

    # 1. Pit Fast-Lane longitudinal queue spacing
    fast_pit_cars = [c for c in cars if c.in_pits and not c.dnf and c.pit_phase != "STOPPED"]
    if len(fast_pit_cars) > 1:
        pit_ref = track.pit_entry_s * 0.96
        fast_pit_cars.sort(key=lambda c: (c.s - pit_ref) % L, reverse=True)
        for i in range(1, len(fast_pit_cars)):
            ahead = fast_pit_cars[i - 1]
            behind = fast_pit_cars[i]
            ds_m = (ahead.s - behind.s) % L
            if 0.0 <= ds_m < min_pit_long_m and abs(ahead.pit_apron - behind.pit_apron) < 0.75:
                deficit = min_pit_long_m - ds_m
                soft_shift = min(deficit * 0.40 + 0.02, 0.30)
                behind.total_dist -= soft_shift
                behind.s = behind.total_dist % L
                behind.v = min(behind.v, ahead.v)

    # 2. On-track multi-lane selection & spline separation
    on_track = [c for c in cars if not c.in_pits and not c.dnf and c.spin_timer <= 0.0]
    n_on = len(on_track)
    if n_on > 1:
        lane_candidates = [0.0, -0.74, 0.74, -0.46, 0.46, -0.86, 0.86]

        for c in on_track:
            blockers = []
            for o in on_track:
                if o is c:
                    continue
                ds_m = (o.s - c.s) % L
                if 0.0 < ds_m < min_long_m * 1.85 and (c.lap > o.lap or getattr(o, "blue_flag", False) or c.total_dist > o.total_dist):
                    blockers.append((ds_m, o))
            if blockers and c.battle_with is None and c.maneuver_timer <= 0.0 and c.maneuver_pass_timer <= 0.0:
                best_lane = None
                best_cost = 999.0
                for cand in lane_candidates:
                    cand_px = compute_lateral_screen_px(track, cand)
                    if all(
                        abs(cand_px - compute_lateral_screen_px(track, b.d)) >= CAR_WID_PX * 1.03
                        for _, b in blockers
                    ):
                        cost = abs(cand - c.d) + abs(cand) * 0.15
                        if cost < best_cost:
                            best_cost = cost
                            best_lane = cand
                if best_lane is not None:
                    c.target_d = best_lane

        on_track.sort(key=lambda c: c.total_dist, reverse=True)
        for _ in range(2):
            for i in range(n_on):
                c = on_track[i]
                for j in range(n_on):
                    if i == j:
                        continue
                    o = on_track[j]
                    ds_m = (o.s - c.s) % L
                    if ds_m >= min_long_m or ds_m > L * 0.45:
                        continue
                    if ds_m < 0.02 and c.total_dist > o.total_dist:
                        continue
                    lat_o = compute_lateral_screen_px(track, o.d)
                    lat_c = compute_lateral_screen_px(track, c.d)
                    lat_sep = abs(lat_o - lat_c)

                    is_blue_yield = (c.lap > o.lap or getattr(o, "blue_flag", False))
                    req_lat = CAR_WID_PX * 0.70 if is_blue_yield else CAR_WID_PX * 0.84
                    is_passing = (
                        c.maneuver_pass_timer > 0.0
                        or getattr(o, "maneuver_pass_timer", 0.0) > 0.0
                        or c.maneuver_timer > 0.0
                    )
                    if (lat_sep >= req_lat or is_passing) and allow_passing:
                        if lat_sep < CAR_WID_PX:
                            need_d = (CAR_WID_PX - lat_sep) / half_usable + 0.04
                            if c.d >= o.d:
                                c.d = min(0.92, c.d + need_d * 0.50)
                                o.d = max(-0.92, o.d - need_d * 0.30)
                            else:
                                c.d = max(-0.92, c.d - need_d * 0.50)
                                o.d = min(0.92, o.d + need_d * 0.30)
                            c.target_d = c.d
                            o.target_d = o.d
                        new_sep = abs(compute_lateral_screen_px(track, o.d) - compute_lateral_screen_px(track, c.d))
                        if new_sep >= CAR_WID_PX - 0.05 or is_passing:
                            continue

                    deficit = min_long_m - ds_m
                    if deficit > 0:
                        if is_blue_yield:
                            c.v = max(c.v, o.v * 1.02)
                        else:
                            c.v = min(c.v, max(o.v * 0.988, 4.0))
                        soft_shift = min(deficit * 0.35 + 0.02, 0.28)
                        c.total_dist -= soft_shift
                        c.s = c.total_dist % L

    # 3. Update world (x, y) and run exact 4-axis SAT OBB verification pass
    for c in cars:
        update_xy_fn(c)

    vis_cars = [c for c in cars if (not c.dnf) or (c.dnf_timer > 0.0)]
    n_vis = len(vis_cars)
    for pass_idx in range(12):
        any_overlap = False
        for i in range(n_vis):
            c1 = vis_cars[i]
            for j in range(i + 1, n_vis):
                c2 = vis_cars[j]
                dx = c2.x - c1.x
                dy = c2.y - c1.y
                if dx * dx + dy * dy >= 245.0:
                    continue

                arc_fwd = (c1.s - c2.s) % L
                arc_bwd = L - arc_fwd
                if track.has_overpass and min(arc_fwd, arc_bwd) > 250.0:
                    continue

                c1_off = c1.dnf or c1.spin_timer > 0.0
                c2_off = c2.dnf or c2.spin_timer > 0.0
                if c1_off and not c2_off:
                    avoid_side = 1.0 if c2.d >= c1.d else -1.0
                    c2.d = max(-0.93, min(0.93, c2.d + avoid_side * 0.06))
                    c2.target_d = c2.d
                    update_xy_fn(c2)
                elif c2_off and not c1_off:
                    avoid_side = 1.0 if c1.d >= c2.d else -1.0
                    c1.d = max(-0.93, min(0.93, c1.d + avoid_side * 0.06))
                    c1.target_d = c1.d
                    update_xy_fn(c1)

                sat = _sat_obb_penetration(c1, c2)
                if sat is None:
                    continue

                in_active_pass = (
                    (c1.maneuver_pass_timer > 0.0 and c1.maneuver_target_id == c2.driver_id)
                    or (c2.maneuver_pass_timer > 0.0 and c2.maneuver_target_id == c1.driver_id)
                    or (c1.battle_with == c2.driver_id and c2.battle_with == c1.driver_id)
                )
                severe_impact = (
                    abs(c1.v - c2.v) > 6.5
                    and min(sat[0], sat[2]) > 2.2
                    and min(sat[1], sat[3]) > 1.8
                )
                if pass_idx == 0 and severe_impact and collision_cb is not None and not in_active_pass and not c1.in_pits and not c2.in_pits and not c1.dnf and not c2.dnf:
                    collision_cb(c1, c2, sat)

                any_overlap = True
                pen_l1, pen_w1, pen_l2, pen_w2 = sat

                if arc_fwd < arc_bwd or (abs(arc_fwd - arc_bwd) < 0.05 and c1.total_dist >= c2.total_dist):
                    ahead, behind = c1, c2
                else:
                    ahead, behind = c2, c1

                # Case A: Pit entry/exit merge alongside an on-track car
                if ahead.in_pits != behind.in_pits and not c1_off and not c2_off:
                    c_trk = behind if not behind.in_pits else ahead
                    need_d = (max(pen_w1, pen_w2) + 0.35) / half_usable
                    c_trk.d = max(-0.93, min(0.93, c_trk.d - track.pit_side * need_d))
                    c_trk.target_d = c_trk.d
                    update_xy_fn(c_trk)
                    if _sat_obb_penetration(c1, c2) is None:
                        continue

                # Case B: Side-by-side on track -> spread laterally
                min_pen_w = min(pen_w1, pen_w2)
                min_pen_l = min(pen_l1, pen_l2)
                is_lateral = (min_pen_w <= min_pen_l) or (abs(ahead.d - behind.d) > 0.16)
                if is_lateral and not ahead.in_pits and not behind.in_pits and not c1_off and not c2_off and allow_passing:
                    need_d = (max(pen_w1, pen_w2) + 0.28) / half_usable
                    if behind.d >= ahead.d:
                        new_a = max(-0.93, ahead.d - need_d * 0.40)
                        used_a = ahead.d - new_a
                        new_b = min(0.93, behind.d + (need_d - used_a))
                        used_b = new_b - behind.d
                        if used_a + used_b < need_d:
                            new_a = max(-0.93, new_a - (need_d - used_a - used_b))
                    else:
                        new_a = min(0.93, ahead.d + need_d * 0.40)
                        used_a = new_a - ahead.d
                        new_b = max(-0.93, behind.d - (need_d - used_a))
                        used_b = behind.d - new_b
                        if used_a + used_b < need_d:
                            new_a = min(0.93, new_a + (need_d - used_a - used_b))
                    ahead.d = new_a
                    behind.d = new_b
                    ahead.target_d = ahead.d
                    behind.target_d = behind.d
                    update_xy_fn(ahead)
                    update_xy_fn(behind)
                    if _sat_obb_penetration(c1, c2) is None:
                        continue

                # Case C: Soft longitudinal spline deceleration & damping (NO TELEPORTATION!)
                if c1.in_pits and c2.in_pits:
                    if (c1.pit_phase == "STOPPED" and c2.pit_phase != "STOPPED") or (c2.pit_phase == "STOPPED" and c1.pit_phase != "STOPPED"):
                        moving = c1 if c2.pit_phase == "STOPPED" else c2
                        moving.v = max(moving.v, 18.0)
                        continue

                mover = behind
                sign_dir = -1.0
                if behind.pit_phase == "STOPPED" and ahead.pit_phase != "STOPPED":
                    mover = ahead
                    sign_dir = -1.0 if ahead.pit_phase == "ENTRY" else 1.0

                sat_now = _sat_obb_penetration(c1, c2)
                if sat_now is not None:
                    pl1, _pw1, pl2, _pw2 = sat_now
                    loc_px_m = max(0.18, track.px_per_m)
                    pen_l = min(max(pl1, pl2), 2.5)
                    # Soft, bounded shift: at most 0.28m per pass!
                    shift_m = min((pen_l + 0.15) / loc_px_m, 0.28)
                    mover.total_dist += sign_dir * shift_m
                    mover.s = mover.total_dist % L
                    if sign_dir < 0.0 and not mover.dnf and mover.pit_phase != "STOPPED":
                        mover.v = min(mover.v, max(ahead.v * 0.985, 4.0))
                    update_xy_fn(mover)

        if not any_overlap:
            break

    # 4. Exact Minimum-Translation-Vector (MTV) failsafe
    for _ in range(4):
        mtv_hit = False
        for i in range(n_vis):
            c1 = vis_cars[i]
            for j in range(i + 1, n_vis):
                c2 = vis_cars[j]
                dx = c2.x - c1.x
                dy = c2.y - c1.y
                if dx * dx + dy * dy >= 245.0:
                    continue
                if track.has_overpass and min((c1.s - c2.s) % L, (c2.s - c1.s) % L) > 250.0:
                    continue
                sat = _sat_obb_penetration(c1, c2, half_l=6.20, half_w=2.95)
                if sat is None:
                    continue
                mtv_hit = True
                pl1, pw1, pl2, pw2 = sat
                ch1, sh1 = math.cos(c1.heading), math.sin(c1.heading)
                ch2, sh2 = math.cos(c2.heading), math.sin(c2.heading)
                cx_d = (c2.x + ch2 * 0.255) - (c1.x + ch1 * 0.255)
                cy_d = (c2.y + sh2 * 0.255) - (c1.y + sh1 * 0.255)
                candidates = [
                    (pl1, ch1, sh1),
                    (pw1, -sh1, ch1),
                    (pl2, ch2, sh2),
                    (pw2, -sh2, ch2),
                ]
                pen_min, ax, ay = min(candidates, key=lambda item: item[0])
                if cx_d * ax + cy_d * ay < 0.0:
                    ax, ay = -ax, -ay
                push = 0.5 * (pen_min + 0.35)
                c1.x = round(c1.x - ax * push, 2)
                c1.y = round(c1.y - ay * push, 2)
                c2.x = round(c2.x + ax * push, 2)
                c2.y = round(c2.y + ay * push, 2)
        if not mtv_hit:
            break

phys.enforce_2d_car_separation = clean_enforce_2d_car_separation

tracks = {t.id: t for t in COMPILED_TRACKS}
trk = tracks['australia']
teams_list, drivers_list = clone_initial_roster()
teams_by_id = {t['id']: t for t in teams_list}
drivers = [d for d in drivers_list if d.get('team_id')]

race = RaceSession(trk, teams_by_id, drivers, 0.0, 0.1, 'mercedes', is_sprint=False)
dt = 0.05

shunts = []
for tick in range(300):
    prev_td = {c.driver_id: c.total_dist for c in race.cars}
    race.step(dt, lambda *_: None)
    if race.lights_out:
        for c in race.cars:
            dtd = c.total_dist - prev_td[c.driver_id]
            if dtd < -0.5:
                shunts.append((race.race_clock, c.code, dtd, c.v))

print(f"Total backward shunts (< -0.5m) with clean enforcement: {len(shunts)}")
if shunts:
    for s in shunts[:10]:
        print(f"  t={s[0]:.2f}s | {s[1]} delta={s[2]:.2f}m v={s[3]:.1f}")
