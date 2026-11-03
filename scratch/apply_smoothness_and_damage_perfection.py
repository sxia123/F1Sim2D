"""Apply smoothness, anti-slamming, anti-lateral-snap, and anti-backward-jump perfection."""
import pathlib

ROOT = pathlib.Path(r"c:\Coding\F1Sim2D")
phys_file = ROOT / "sim" / "physics.py"
text = phys_file.read_text(encoding="utf-8")

# 1. Reset _tick_lat_shift at start of enforce_2d_car_separation
old_sep_start = """    # 0. Sync world (x, y, heading) for all cars
    for c in cars:
        update_xy_fn(c)"""

new_sep_start = """    # 0. Sync world (x, y, heading) for all cars
    for c in cars:
        c._tick_lat_shift = 0.0
        update_xy_fn(c)"""

# 2. Smooth pre-SAT target_d guidance instead of direct c.d jump, and bounded soft_shift
old_pre_sat = """                    deficit = min_long_m - ds_m
                    if deficit > 0:
                        if c.v > o.v:
                            c.v = max(o.v * 0.98, c.v - 22.0 * 0.05)
                        soft_shift = min(deficit * 0.30 + 0.02, 0.25)
                        c.total_dist -= soft_shift
                        c.s = c.total_dist % L"""

new_pre_sat = """                    deficit = min_long_m - ds_m
                    if deficit > 0:
                        if c.v > o.v:
                            c.v = max(o.v * 0.98, c.v - 22.0 * 0.05)
                        # Shift never exceeds forward motion, preventing backwards stutter
                        soft_shift = min(deficit * 0.20, max(0.0, c.v * 0.05 * 0.70))
                        c.total_dist -= soft_shift
                        c.s = c.total_dist % L"""

# 3. Incident avoidance target guidance (no multi-pass snapping)
old_avoid = """                c1_off = c1.dnf or c1.spin_timer > 0.0
                c2_off = c2.dnf or c2.spin_timer > 0.0
                if c1_off and not c2_off:
                    avoid_side = 1.0 if c2.d >= c1.d else -1.0
                    c2.d = max(-0.93, min(0.93, c2.d + avoid_side * 0.08))
                    c2.target_d = c2.d
                    update_xy_fn(c2)
                elif c2_off and not c1_off:
                    avoid_side = 1.0 if c1.d >= c2.d else -1.0
                    c1.d = max(-0.93, min(0.93, c1.d + avoid_side * 0.08))
                    c1.target_d = c1.d
                    update_xy_fn(c1)"""

new_avoid = """                c1_off = c1.dnf or c1.spin_timer > 0.0
                c2_off = c2.dnf or c2.spin_timer > 0.0
                if c1_off and not c2_off:
                    avoid_side = 1.0 if c2.d >= c1.d else -1.0
                    c2.target_d = max(-0.93, min(0.93, c2.d + avoid_side * 0.15))
                elif c2_off and not c1_off:
                    avoid_side = 1.0 if c1.d >= c2.d else -1.0
                    c1.target_d = max(-0.93, min(0.93, c1.d + avoid_side * 0.15))"""

# 4. Pit merge alongside on-track car: budget-limited lateral shift
old_pit_merge = """                # Case A: Pit entry/exit merge alongside an on-track car -> steer on-track car clear of pit blend line
                if ahead.in_pits != behind.in_pits and not c1_off and not c2_off:
                    c_trk = behind if not behind.in_pits else ahead
                    need_d = (max(pen_w1, pen_w2) + 0.35) / half_usable
                    c_trk.d = max(-0.93, min(0.93, c_trk.d - track.pit_side * need_d))
                    c_trk.target_d = c_trk.d
                    update_xy_fn(c_trk)
                    if _sat_obb_penetration(c1, c2) is None:
                        continue"""

new_pit_merge = """                # Case A: Pit entry/exit merge alongside an on-track car -> steer on-track car clear of pit blend line
                if ahead.in_pits != behind.in_pits and not c1_off and not c2_off:
                    c_trk = behind if not behind.in_pits else ahead
                    lat_budget = max(0.0, 0.10 - getattr(c_trk, "_tick_lat_shift", 0.0))
                    need_d = min(lat_budget, (max(pen_w1, pen_w2) + 0.20) / half_usable)
                    if need_d > 0.001:
                        new_d = max(-0.93, min(0.93, c_trk.d - track.pit_side * need_d))
                        c_trk._tick_lat_shift = getattr(c_trk, "_tick_lat_shift", 0.0) + abs(new_d - c_trk.d)
                        c_trk.d = new_d
                        c_trk.target_d = c_trk.d
                        update_xy_fn(c_trk)
                        if _sat_obb_penetration(c1, c2) is None:
                            continue"""

# 5. Side-by-side SAT lateral spread: budget-limited lateral shift (guarantees |dd| <= 0.10)
old_sat_case_b = """                # Case B: Side-by-side on track -> spread laterally with full remainder transfer if one hits track edge
                min_pen_w = min(pen_w1, pen_w2)
                min_pen_l = min(pen_l1, pen_l2)
                is_lateral = (min_pen_w <= min_pen_l) or (abs(ahead.d - behind.d) > 0.14)
                if is_lateral and not ahead.in_pits and not behind.in_pits and not c1_off and not c2_off and allow_passing:
                    need_d = min(0.18, (max(pen_w1, pen_w2) + 0.15) / half_usable)
                    max_single_shift = 0.09
                    if behind.d >= ahead.d:
                        shift_a = min(max_single_shift, need_d * 0.50)
                        new_a = max(-0.93, ahead.d - shift_a)
                        shift_b = min(max_single_shift, need_d - (ahead.d - new_a))
                        new_b = min(0.93, behind.d + shift_b)
                    else:
                        shift_a = min(max_single_shift, need_d * 0.50)
                        new_a = min(0.93, ahead.d + shift_a)
                        shift_b = min(max_single_shift, need_d - (new_a - ahead.d))
                        new_b = max(-0.93, behind.d - shift_b)
                    ahead.d = new_a
                    behind.d = new_b
                    ahead.target_d = ahead.d
                    behind.target_d = behind.d
                    update_xy_fn(ahead)
                    update_xy_fn(behind)
                    continue"""

new_sat_case_b = """                # Case B: Side-by-side on track -> spread laterally with strict per-tick shift budgeting
                min_pen_w = min(pen_w1, pen_w2)
                min_pen_l = min(pen_l1, pen_l2)
                is_lateral = (min_pen_w <= min_pen_l) or (abs(ahead.d - behind.d) > 0.14)
                if is_lateral and not ahead.in_pits and not behind.in_pits and not c1_off and not c2_off and allow_passing:
                    lat_budget_a = max(0.0, 0.10 - getattr(ahead, "_tick_lat_shift", 0.0))
                    lat_budget_b = max(0.0, 0.10 - getattr(behind, "_tick_lat_shift", 0.0))
                    need_d = min(0.14, (max(pen_w1, pen_w2) + 0.15) / half_usable)
                    max_shift_a = min(lat_budget_a, need_d * 0.50)
                    max_shift_b = min(lat_budget_b, need_d * 0.50)
                    if max_shift_a > 0.001 or max_shift_b > 0.001:
                        if behind.d >= ahead.d:
                            new_a = max(-0.93, ahead.d - max_shift_a)
                            new_b = min(0.93, behind.d + max_shift_b)
                        else:
                            new_a = min(0.93, ahead.d + max_shift_a)
                            new_b = max(-0.93, behind.d - max_shift_b)
                        ahead._tick_lat_shift = getattr(ahead, "_tick_lat_shift", 0.0) + abs(new_a - ahead.d)
                        behind._tick_lat_shift = getattr(behind, "_tick_lat_shift", 0.0) + abs(new_b - behind.d)
                        ahead.d = new_a
                        behind.d = new_b
                        ahead.target_d = ahead.d
                        behind.target_d = behind.d
                        update_xy_fn(ahead)
                        update_xy_fn(behind)
                        continue"""

# 6. Longitudinal SAT shift & progressive speed matching
old_sat_long = """                    pen_l = min(max(pl1, pl2), 4.2)
                    shift_m = (pen_l + 0.35) / loc_px_m
                    mover.total_dist += sign_dir * shift_m
                    mover.s = mover.total_dist % L
                    if sign_dir < 0.0 and not mover.dnf and mover.pit_phase != "STOPPED":
                        mover.v = min(mover.v, max(ahead.v * 0.98, 4.0))"""

new_sat_long = """                    pen_l = min(max(pl1, pl2), 4.2)
                    shift_m = min((pen_l + 0.25) / loc_px_m, max(0.0, mover.v * 0.05 * 0.70))
                    mover.total_dist += sign_dir * shift_m
                    mover.s = mover.total_dist % L
                    if sign_dir < 0.0 and not mover.dnf and mover.pit_phase != "STOPPED":
                        if mover.v > ahead.v:
                            mover.v = max(ahead.v, mover.v - 22.0 * 0.05)"""

# 7. Smooth Standing Start Launch (Authentic reaction & acceleration)
old_launch = """                for c in self.cars:
                    c.lap_start_time = 0.0
                    launch = 7.5 + (c.skills["racecraft"] - 80) * 0.14 + (c.car_perf_index - 80.0) * 0.09 + random.uniform(-1.1, 1.1)
                    c.v = max(4.0, launch)"""

new_launch = """                for c in self.cars:
                    c.lap_start_time = 0.0
                    launch = 7.5 + (c.skills["racecraft"] - 80) * 0.14 + (c.car_perf_index - 80.0) * 0.09 + random.uniform(-1.1, 1.1)
                    c.v = 0.6
                    c.accel = launch * 1.5"""

# 8. Stout Defense throttle ease (Eliminates the 30 m/s slamming deceleration on defended attacks)
old_def_slam = """                else:
                    defender.maneuver = "DEFEND"
                    defender.maneuver_timer = 2.0
                    attacker.v = min(attacker.v, defender.v * 0.96)
                    attacker.maneuver_timer = 0.0"""

new_def_slam = """                else:
                    defender.maneuver = "DEFEND"
                    defender.maneuver_timer = 2.0
                    if attacker.v > defender.v * 0.96:
                        attacker.v = max(defender.v * 0.96, attacker.v - 18.0 * dt)
                    attacker.maneuver_timer = 0.0"""

pairs = [
    ("sep_start", old_sep_start, new_sep_start),
    ("pre_sat", old_pre_sat, new_pre_sat),
    ("avoid", old_avoid, new_avoid),
    ("pit_merge", old_pit_merge, new_pit_merge),
    ("sat_case_b", old_sat_case_b, new_sat_case_b),
    ("sat_long", old_sat_long, new_sat_long),
    ("launch", old_launch, new_launch),
    ("def_slam", old_def_slam, new_def_slam),
]

for name, o, n in pairs:
    assert o in text, f"Missing: {name}"
    text = text.replace(o, n, 1)

phys_file.write_text(text, encoding="utf-8")
print("SUCCESS: Smoothness and anti-slamming perfection applied to sim/physics.py!")
