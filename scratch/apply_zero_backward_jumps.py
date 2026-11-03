with open('sim/physics.py', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Initialize _tick_long_shift
t_init = """    # 0. Sync world (x, y, heading) for all cars
    for c in cars:
        c._tick_lat_shift = 0.0
        update_xy_fn(c)"""

r_init = """    # 0. Sync world (x, y, heading) for all cars
    for c in cars:
        c._tick_lat_shift = 0.0
        c._tick_long_shift = 0.0
        update_xy_fn(c)"""

assert t_init in text, 't_init not found'
text = text.replace(t_init, r_init, 1)

# 2. Pit fast lane soft_shift budget
t_pit = """                deficit = min_pit_long_m - ds_m
                soft_shift = min(deficit * 0.40 + 0.02, 0.30)
                behind.total_dist -= soft_shift
                behind.s = behind.total_dist % L"""

r_pit = """                deficit = min_pit_long_m - ds_m
                budget_long = max(0.0, behind.v * 0.05 * 0.60 - getattr(behind, "_tick_long_shift", 0.0))
                soft_shift = min(deficit * 0.30, budget_long)
                behind._tick_long_shift = getattr(behind, "_tick_long_shift", 0.0) + soft_shift
                behind.total_dist -= soft_shift
                behind.s = behind.total_dist % L"""

assert t_pit in text, 't_pit not found'
text = text.replace(t_pit, r_pit, 1)

# 3. On-track pre-SAT deficit spacing budget
t_presat = """                    deficit = min_long_m - ds_m
                    if deficit > 0:
                        if c.v > o.v:
                            if c.accel > -22.0:
                                c.v = max(o.v * 0.98, c.v - 12.0 * 0.05)
                        # Shift never exceeds forward motion, preventing backwards stutter
                        soft_shift = min(deficit * 0.20, max(0.0, c.v * 0.05 * 0.70))
                        c.total_dist -= soft_shift
                        c.s = c.total_dist % L"""

r_presat = """                    deficit = min_long_m - ds_m
                    if deficit > 0:
                        if c.v > o.v:
                            if c.accel > -22.0:
                                c.v = max(o.v * 0.98, c.v - 12.0 * 0.05)
                        # Strict budget guarantee: cumulative shift never causes negative forward displacement
                        budget_long = max(0.0, c.v * 0.05 * 0.60 - getattr(c, "_tick_long_shift", 0.0))
                        soft_shift = min(deficit * 0.20, budget_long)
                        c._tick_long_shift = getattr(c, "_tick_long_shift", 0.0) + soft_shift
                        c.total_dist -= soft_shift
                        c.s = c.total_dist % L"""

assert t_presat in text, 't_presat not found'
text = text.replace(t_presat, r_presat, 1)

# 4. SAT Case C shift_m budget
t_sat_c = """                    pen_l = min(max(pl1, pl2), 4.2)
                    shift_m = min((pen_l + 0.25) / loc_px_m, max(0.0, mover.v * 0.05 * 0.70))
                    mover.total_dist += sign_dir * shift_m
                    mover.s = mover.total_dist % L"""

r_sat_c = """                    pen_l = min(max(pl1, pl2), 4.2)
                    budget_long = max(0.0, mover.v * 0.05 * 0.60 - getattr(mover, "_tick_long_shift", 0.0))
                    shift_m = min((pen_l + 0.20) / loc_px_m, budget_long)
                    if shift_m > 0.0001:
                        mover._tick_long_shift = getattr(mover, "_tick_long_shift", 0.0) + shift_m
                        mover.total_dist += sign_dir * shift_m
                        mover.s = mover.total_dist % L"""

assert t_sat_c in text, 't_sat_c not found'
text = text.replace(t_sat_c, r_sat_c, 1)

with open('sim/physics.py', 'w', encoding='utf-8') as f:
    f.write(text)
print('Successfully applied zero backward jumps overhaul!')

