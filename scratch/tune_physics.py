with open('sim/physics.py', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Deceleration stacking guard in deficit spacing
t_dec = """                    deficit = min_long_m - ds_m
                    if deficit > 0:
                        if c.v > o.v:
                            c.v = max(o.v * 0.98, c.v - 22.0 * 0.05)"""

r_dec = """                    deficit = min_long_m - ds_m
                    if deficit > 0:
                        if c.v > o.v:
                            if c.accel > -22.0:
                                c.v = max(o.v * 0.98, c.v - 12.0 * 0.05)"""

assert t_dec in text, 't_dec not found'
text = text.replace(t_dec, r_dec, 1)

# 2. Deceleration stacking guard in mover longitudinal SAT
t_mov = """                    if sign_dir < 0.0 and not mover.dnf and mover.pit_phase != "STOPPED":
                        if mover.v > ahead.v:
                            mover.v = max(ahead.v, mover.v - 22.0 * 0.05)"""

r_mov = """                    if sign_dir < 0.0 and not mover.dnf and mover.pit_phase != "STOPPED":
                        if mover.v > ahead.v:
                            if mover.accel > -22.0:
                                mover.v = max(ahead.v, mover.v - 12.0 * 0.05)"""

assert t_mov in text, 't_mov not found'
text = text.replace(t_mov, r_mov, 1)

# 3. max_d_step in _step_car
t_step = """        steer_rate = 2.8 if (car.maneuver_pass_timer > 0.0 or car.maneuver_timer > 0.0) else 2.2
        max_d_step = 2.4 * dt
        step_d = (car.target_d - car.d) * min(1.0, dt * steer_rate)
        car.d += max(-max_d_step, min(max_d_step, step_d))"""

r_step = """        steer_rate = 2.6 if (car.maneuver_pass_timer > 0.0 or car.maneuver_timer > 0.0) else 2.0
        max_d_step = 1.6 * dt
        step_d = (car.target_d - car.d) * min(1.0, dt * steer_rate)
        car.d += max(-max_d_step, min(max_d_step, step_d))"""

assert t_step in text, 't_step not found'
text = text.replace(t_step, r_step, 1)

# 4. SAT Case B lateral budget
t_sat_b = """                    lat_budget_a = max(0.0, 0.10 - getattr(ahead, "_tick_lat_shift", 0.0))
                    lat_budget_b = max(0.0, 0.10 - getattr(behind, "_tick_lat_shift", 0.0))"""

r_sat_b = """                    lat_budget_a = max(0.0, 0.055 - getattr(ahead, "_tick_lat_shift", 0.0))
                    lat_budget_b = max(0.0, 0.055 - getattr(behind, "_tick_lat_shift", 0.0))"""

assert t_sat_b in text, 't_sat_b not found'
text = text.replace(t_sat_b, r_sat_b, 1)

with open('sim/physics.py', 'w', encoding='utf-8') as f:
    f.write(text)
print('Successfully applied decel guard and lateral budget tuning!')

