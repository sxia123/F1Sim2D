text = open('sim/physics.py', encoding='utf-8').read()

t1 = """    # 0. Sync world (x, y, heading) for all cars
    for c in cars:
        update_xy_fn(c)"""

t2 = """                    deficit = min_long_m - ds_m
                    if deficit > 0:
                        if c.v > o.v:
                            c.v = max(o.v * 0.98, c.v - 22.0 * 0.05)
                        soft_shift = min(deficit * 0.30 + 0.02, 0.25)
                        c.total_dist -= soft_shift
                        c.s = c.total_dist % L"""

t3 = """                c1_off = c1.dnf or c1.spin_timer > 0.0
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

t4 = """                # Case A: Pit entry/exit merge alongside an on-track car -> steer on-track car clear of pit blend line
                if ahead.in_pits != behind.in_pits and not c1_off and not c2_off:
                    c_trk = behind if not behind.in_pits else ahead
                    need_d = (max(pen_w1, pen_w2) + 0.35) / half_usable
                    c_trk.d = max(-0.93, min(0.93, c_trk.d - track.pit_side * need_d))
                    c_trk.target_d = c_trk.d
                    update_xy_fn(c_trk)
                    if _sat_obb_penetration(c1, c2) is None:
                        continue"""

t5 = """                # Case B: Side-by-side on track -> spread laterally with full remainder transfer if one hits track edge
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

t6 = """                    pen_l = min(max(pl1, pl2), 4.2)
                    shift_m = (pen_l + 0.35) / loc_px_m
                    mover.total_dist += sign_dir * shift_m
                    mover.s = mover.total_dist % L
                    if sign_dir < 0.0 and not mover.dnf and mover.pit_phase != "STOPPED":
                        mover.v = min(mover.v, max(ahead.v * 0.98, 4.0))"""

t7 = """                for c in self.cars:
                    c.lap_start_time = 0.0
                    launch = 7.5 + (c.skills["racecraft"] - 80) * 0.14 + (c.car_perf_index - 80.0) * 0.09 + random.uniform(-1.1, 1.1)
                    c.v = max(4.0, launch)"""

t8 = """                else:
                    defender.maneuver = "DEFEND"
                    defender.maneuver_timer = 2.0
                    attacker.v = min(attacker.v, defender.v * 0.96)
                    attacker.maneuver_timer = 0.0"""

for i, t in enumerate([t1, t2, t3, t4, t5, t6, t7, t8]):
    print(f't{i+1}: {t in text}')

