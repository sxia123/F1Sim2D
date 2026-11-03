"""Apply complete physics overhaul: smooth progressive braking, per-tick heading rate limiting,
authentic collision damage, clamped lateral SAT separation, and envelope clamping guards."""
import pathlib

ROOT = pathlib.Path(r"c:\Coding\F1Sim2D")
phys_file = ROOT / "sim" / "physics.py"
text = phys_file.read_text(encoding="utf-8")

# --- 1. CarState initialization additions ---
old_carstate_init = """        self.x: float = 0.0
        self.y: float = 0.0
        self.heading: float = 0.0

        # 2026 Active Aero & Hybrid ERS / Overtake Mode"""

new_carstate_init = """        self.x: float = 0.0
        self.y: float = 0.0
        self.heading: float = 0.0
        self._heading_tick: int = -1
        self._has_initial_heading: bool = False

        # 2026 Active Aero & Hybrid ERS / Overtake Mode"""

assert old_carstate_init in text, "old_carstate_init not found"
text = text.replace(old_carstate_init, new_carstate_init)

# --- 2. QualifyingSession tick_count and step ---
old_quali_init = """        self.elapsed: float = 0.0
        self.fastest_time: float | None = None"""

new_quali_init = """        self.elapsed: float = 0.0
        self.tick_count: int = 0
        self._current_dt: float = 0.05
        self.fastest_time: float | None = None"""

assert old_quali_init in text, "old_quali_init not found"
text = text.replace(old_quali_init, new_quali_init)

old_quali_step = """    def step(self, dt: float, event_cb) -> None:
        if self.finished:
            return
        self.elapsed += dt"""

new_quali_step = """    def step(self, dt: float, event_cb) -> None:
        if self.finished:
            return
        self.tick_count += 1
        self._current_dt = dt
        self.elapsed += dt"""

assert old_quali_step in text, "old_quali_step not found"
text = text.replace(old_quali_step, new_quali_step)

# --- 3. QualifyingSession _update_xy heading rate limiting ---
old_quali_xy = """        # Dynamic course and apex yaw attitude (rate-limited, no snap)
        tx, ty = smp["tx"], smp["ty"]
        nx, ny = smp["nx"], smp["ny"]
        half_usable = self.track.track_width_px * 0.39
        v_forward_px = max(6.0, car.v * self.track.px_per_m)
        v_lateral_px = (car.target_d - car.d) * 2.8 * half_usable * 0.18

        vx_course = v_forward_px * tx + v_lateral_px * nx
        vy_course = v_forward_px * ty + v_lateral_px * ny
        theta_course = math.atan2(vy_course, vx_course)

        # 2. Dynamic chassis yaw in corners (especially hairpins): car nose turns naturally into the apex
        yaw_attitude = getattr(car, "steer_angle", 0.0) * 0.24
        car.heading = round(theta_course + yaw_attitude, 4)"""

new_quali_xy = """        curr_tick = getattr(self, "tick_count", 0)
        heading_stepped = (getattr(car, "_heading_tick", -1) == curr_tick)
        if not heading_stepped:
            car._heading_tick = curr_tick
            tx, ty = smp["tx"], smp["ty"]
            half_usable = self.track.track_width_px * 0.39
            v_forward_px = max(6.0, car.v * self.track.px_per_m)
            v_lateral_px = (car.target_d - car.d) * 2.4 * half_usable * 0.18
            drift_angle = max(-0.065, min(0.065, math.atan2(v_lateral_px, v_forward_px)))
            track_heading = math.atan2(ty, tx)
            yaw_attitude = getattr(car, "steer_angle", 0.0) * 0.20
            target_heading = (track_heading + drift_angle + yaw_attitude + math.pi) % (2.0 * math.pi) - math.pi

            prev_h = getattr(car, "heading", None)
            cur_dt = getattr(self, "_current_dt", 0.05)
            if prev_h is not None and getattr(car, "_has_initial_heading", False):
                dh = (target_heading - prev_h + math.pi) % (2.0 * math.pi) - math.pi
                max_dh = 4.8 * cur_dt
                dh_clamped = max(-max_dh, min(max_dh, dh))
                car.heading = round((prev_h + dh_clamped + math.pi) % (2.0 * math.pi) - math.pi, 4)
            else:
                car.heading = round(target_heading, 4)
                car._has_initial_heading = True"""

assert old_quali_xy in text, "old_quali_xy not found"
text = text.replace(old_quali_xy, new_quali_xy)

# --- 4. RaceSession tick_count, _current_dt, and step ---
old_race_init = """        self.race_clock: float = 0.0
        self.lights_countdown: float = 5.5"""

new_race_init = """        self.race_clock: float = 0.0
        self.tick_count: int = 0
        self._current_dt: float = 0.05
        self.lights_countdown: float = 5.5"""

assert old_race_init in text, "old_race_init not found"
text = text.replace(old_race_init, new_race_init)

old_race_step = """    def step(self, dt: float, event_cb) -> None:
        if self.finished:
            return

        if not self.lights_out:"""

new_race_step = """    def step(self, dt: float, event_cb) -> None:
        if self.finished:
            return
        self.tick_count += 1
        self._current_dt = dt

        if not self.lights_out:"""

assert old_race_step in text, "old_race_step not found"
text = text.replace(old_race_step, new_race_step)

# --- 5. RaceSession _update_xy heading rate limiting ---
old_race_xy = """        # 1. Course trajectory angle combining longitudinal speed and lateral maneuver velocity
        tx, ty = smp["tx"], smp["ty"]
        nx, ny = smp["nx"], smp["ny"]
        half_usable = self.track.track_width_px * 0.39
        v_forward_px = max(6.0, car.v * self.track.px_per_m)
        steer_rate = 5.8 if (car.maneuver_pass_timer > 0.0 or car.maneuver_timer > 0.0) else 2.8
        v_lateral_px = (car.target_d - car.d) * steer_rate * half_usable * 0.18

        vx_course = v_forward_px * tx + v_lateral_px * nx
        vy_course = v_forward_px * ty + v_lateral_px * ny
        theta_course = math.atan2(vy_course, vx_course)

        # 2. Dynamic chassis yaw in corners (especially hairpins): car nose turns naturally into the apex
        yaw_attitude = getattr(car, "steer_angle", 0.0) * 0.24
        car.heading = round(theta_course + yaw_attitude, 4)"""

new_race_xy = """        # Heading is integrated at most once per 50ms simulation tick to prevent multi-pass SAT multiplier artifacts
        curr_tick = getattr(self, "tick_count", 0)
        heading_stepped = (getattr(car, "_heading_tick", -1) == curr_tick)
        if not heading_stepped:
            car._heading_tick = curr_tick
            tx, ty = smp["tx"], smp["ty"]
            half_usable = self.track.track_width_px * 0.39
            v_forward_px = max(6.0, car.v * self.track.px_per_m)
            steer_rate = 2.8 if (car.maneuver_pass_timer > 0.0 or car.maneuver_timer > 0.0) else 2.2
            v_lateral_px = (car.target_d - car.d) * steer_rate * half_usable * 0.18

            drift_angle = max(-0.065, min(0.065, math.atan2(v_lateral_px, v_forward_px)))
            track_heading = math.atan2(ty, tx)

            # Dynamic chassis yaw in corners: car nose turns naturally into apex
            yaw_attitude = getattr(car, "steer_angle", 0.0) * 0.20
            target_heading = (track_heading + drift_angle + yaw_attitude + math.pi) % (2.0 * math.pi) - math.pi

            prev_h = getattr(car, "heading", None)
            cur_dt = getattr(self, "_current_dt", 0.05)
            if prev_h is not None and getattr(car, "_has_initial_heading", False):
                dh = (target_heading - prev_h + math.pi) % (2.0 * math.pi) - math.pi
                max_dh = 4.8 * cur_dt
                dh_clamped = max(-max_dh, min(max_dh, dh))
                car.heading = round((prev_h + dh_clamped + math.pi) % (2.0 * math.pi) - math.pi, 4)
            else:
                car.heading = round(target_heading, 4)
                car._has_initial_heading = True"""

assert old_race_xy in text, "old_race_xy not found"
text = text.replace(old_race_xy, new_race_xy)

# --- 6. Progressive Smooth Braking in _step_car ---
old_brake = """        else:
            brake_decel = 43.5 * (0.85 + 0.15 * grip_mult)
            car.accel = -brake_decel
            car.braking = (car.v - target_v) > 4.0
            car.v = max(target_v, car.v - brake_decel * dt)"""

new_brake = """        else:
            v_diff = car.v - target_v
            max_brake = 42.0 * (0.85 + 0.15 * grip_mult)
            if v_diff <= 1.5:
                # Smooth throttle lift & aerodynamic coasting (zero slamming!)
                brake_decel = min(10.0, v_diff / max(dt, 0.001))
            elif v_diff < 7.0:
                # Progressive brake pedal modulation ramping smoothly from coasting to heavy braking
                blend = (v_diff - 1.5) / 5.5
                brake_decel = 10.0 + blend * (max_brake - 10.0)
            else:
                # Full threshold braking in deep corner braking zones
                brake_decel = max_brake
            car.accel = -brake_decel
            car.braking = v_diff > 4.5
            car.v = max(target_v, car.v - brake_decel * dt)"""

assert old_brake in text, "old_brake not found"
text = text.replace(old_brake, new_brake)

# --- 7. Soften steer_rate in _step_car ---
old_steer = """        steer_rate = 5.8 if (car.maneuver_pass_timer > 0.0 or car.maneuver_timer > 0.0) else 2.8
        step_d = (car.target_d - car.d) * min(1.0, dt * steer_rate)
        car.d += step_d"""

new_steer = """        steer_rate = 2.8 if (car.maneuver_pass_timer > 0.0 or car.maneuver_timer > 0.0) else 2.2
        max_d_step = 2.4 * dt
        step_d = (car.target_d - car.d) * min(1.0, dt * steer_rate)
        car.d += max(-max_d_step, min(max_d_step, step_d))"""

assert old_steer in text, "old_steer not found"
text = text.replace(old_steer, new_steer)

# --- 8. Enforce 2D car separation: Blue yield boost removal, smooth braking, clamped lateral shift ---
old_blue_yield = """                    deficit = min_long_m - ds_m
                    if deficit > 0:
                        if is_blue_yield:
                            c.v = max(c.v, o.v * 1.02)
                        else:
                            c.v = max(4.0, max(o.v * 0.98, c.v - 22.0 * 0.05))
                        soft_shift = min(deficit * 0.30 + 0.02, 0.25)
                        c.total_dist -= soft_shift
                        c.s = c.total_dist % L"""

new_blue_yield = """                    deficit = min_long_m - ds_m
                    if deficit > 0:
                        if c.v > o.v:
                            c.v = max(o.v * 0.98, c.v - 22.0 * 0.05)
                        soft_shift = min(deficit * 0.30 + 0.02, 0.25)
                        c.total_dist -= soft_shift
                        c.s = c.total_dist % L"""

assert old_blue_yield in text, "old_blue_yield not found"
text = text.replace(old_blue_yield, new_blue_yield)

# Clamped SAT lateral spread
old_sat_spread = """                if is_lateral and not ahead.in_pits and not behind.in_pits and not c1_off and not c2_off and allow_passing:
                    need_d = (max(pen_w1, pen_w2) + 0.45) / half_usable
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
                    behind.d = new_b"""

new_sat_spread = """                if is_lateral and not ahead.in_pits and not behind.in_pits and not c1_off and not c2_off and allow_passing:
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
                    behind.d = new_b"""

assert old_sat_spread in text, "old_sat_spread not found"
text = text.replace(old_sat_spread, new_sat_spread)

# Smooth pit fast lane queue
old_pit_q = """                behind.total_dist -= soft_shift
                behind.s = behind.total_dist % L
                behind.v = min(behind.v, ahead.v)"""

new_pit_q = """                behind.total_dist -= soft_shift
                behind.s = behind.total_dist % L
                if behind.v > ahead.v:
                    behind.v = max(ahead.v, behind.v - 22.0 * 0.05)"""

assert old_pit_q in text, "old_pit_q not found"
text = text.replace(old_pit_q, new_pit_q)

# --- 9. Guard envelope clamping in _resolve_battles_and_incidents ---
old_env1 = """                        if lat_sep >= CAR_WID_PX * 0.86:
                            st_c = self.track.sample(c.s)["station"]
                            v_env_c = self.v_env[st_c]
                            c.v = min(v_env_c, c.v + 16.0 * dt)
                            if tgt.v > c.v - 1.2:
                                tgt.v = max(4.0, tgt.v - 8.0 * dt)"""

new_env1 = """                        if lat_sep >= CAR_WID_PX * 0.86:
                            st_c = self.track.sample(c.s)["station"]
                            v_env_c = self.v_env[st_c]
                            if c.v < v_env_c:
                                c.v = min(v_env_c, c.v + 16.0 * dt)
                            if tgt.v > c.v - 1.2:
                                tgt.v = max(4.0, tgt.v - 8.0 * dt)"""

assert old_env1 in text, "old_env1 not found"
text = text.replace(old_env1, new_env1)

old_env2 = """                    if attacker.overtake_active:
                        # Slingshot punch: attacker surges past defender with smooth envelope-bounded velocity
                        attacker.v = min(self.v_env[st], attacker.v + 1.2)"""

new_env2 = """                    if attacker.overtake_active:
                        # Slingshot punch: attacker surges past defender with smooth envelope-bounded velocity
                        if attacker.v < self.v_env[st]:
                            attacker.v = min(self.v_env[st], attacker.v + 1.2)"""

assert old_env2 in text, "old_env2 not found"
text = text.replace(old_env2, new_env2)

# Smooth team order hold & yellow flag speed
old_team_hold = """            if attacker.team_id == defender.team_id and attacker.team_order == "HOLD":
                attacker.v = min(attacker.v, defender.v * 0.995)
                continue"""

new_team_hold = """            if attacker.team_id == defender.team_id and attacker.team_order == "HOLD":
                if attacker.v > defender.v * 0.995:
                    attacker.v = max(defender.v * 0.995, attacker.v - 22.0 * dt)
                continue"""

assert old_team_hold in text, "old_team_hold not found"
text = text.replace(old_team_hold, new_team_hold)

old_yellow = """                    attacker.v = min(attacker.v, defender.v)
                    continue"""

new_yellow = """                    if attacker.v > defender.v:
                        attacker.v = max(defender.v, attacker.v - 24.0 * dt)
                    continue"""

assert old_yellow in text, "old_yellow not found"
text = text.replace(old_yellow, new_yellow)

# Smooth throttle ease on stout defense
old_stout = """                    # Attacker eases throttle smoothly without instant deceleration crash
                    attacker.v = max(4.0, max(defender.v * 0.96, attacker.v - 14.0 * dt))"""

new_stout = """                    # Attacker eases throttle smoothly without instant deceleration crash
                    if attacker.v > defender.v * 0.96:
                        attacker.v = max(4.0, attacker.v - 14.0 * dt)"""

assert old_stout in text, "old_stout not found"
text = text.replace(old_stout, new_stout)

# --- 10. AUTHENTIC COLLISION DAMAGE SYSTEM (Fix "collsion but no damage") ---
# A. In _handle_collision:
old_handle_col = """        is_lap1 = attacker.lap == 1
        if roll < 0.62 or is_lap1:
            victim.v *= 0.90
            deflect_dir = 1.0 if victim.d >= culprit.d else -1.0
            victim.d = max(-1.15, min(1.15, victim.d + deflect_dir * 0.28))
            culprit.d = max(-1.15, min(1.15, culprit.d - deflect_dir * 0.14))
            self._update_xy(victim)
            self._update_xy(culprit)
            victim.smoke = 1.4
            attacker.sparks = True
            defender.sparks = True
            culprit.repair_cost_m += 0.12
            if random.random() < 0.35:
                culprit.wing_damage = min(0.35, culprit.wing_damage + random.uniform(0.06, 0.12))
            event_cb(
                "INCIDENT",
                f"WHEEL-TO-WHEEL! Contact between #{attacker.number} {attacker.code} and #{defender.number} {defender.code} at Turn {turn}!",
            )"""

new_handle_col = """        is_lap1 = attacker.lap == 1
        if roll < 0.62 or is_lap1:
            victim.v = max(8.0, victim.v - 8.0)
            deflect_dir = 1.0 if victim.d >= culprit.d else -1.0
            victim.target_d = max(-1.05, min(1.05, victim.d + deflect_dir * 0.22))
            culprit.target_d = max(-1.05, min(1.05, culprit.d - deflect_dir * 0.12))
            victim.smoke = 1.4
            attacker.sparks = True
            defender.sparks = True
            # Authentic damage on EVERY collision contact: both cars suffer physical damage
            culprit_dmg = random.uniform(0.14, 0.26)
            culprit.wing_damage = min(0.85, culprit.wing_damage + culprit_dmg)
            culprit.wing_damage_side = "RIGHT" if culprit.d < victim.d else "LEFT"
            culprit.repair_cost_m += round(culprit_dmg * 0.75, 2)
            culprit.tire_wear = min(0.99, culprit.tire_wear + 0.02)

            victim_dmg = random.uniform(0.10, 0.20)
            victim.wing_damage = min(0.85, victim.wing_damage + victim_dmg)
            victim.wing_damage_side = "LEFT" if victim.d > culprit.d else "RIGHT"
            victim.repair_cost_m += round(victim_dmg * 0.65, 2)
            victim.tire_wear = min(0.99, victim.tire_wear + 0.02)

            if culprit.wing_damage >= 0.35:
                culprit.box_this_lap = True
            if victim.wing_damage >= 0.35:
                victim.box_this_lap = True

            event_cb(
                "INCIDENT",
                f"WHEEL-TO-WHEEL! Contact between #{attacker.number} {attacker.code} and #{defender.number} {defender.code} at Turn {turn} (Wing Damage)!",
            )"""

assert old_handle_col in text, "old_handle_col not found"
text = text.replace(old_handle_col, new_handle_col)

# B. Remove teleportation in severe spin collision (lines 2459-2472)
old_spin_teleport = """            victim.d = 1.42 if victim.d >= 0.0 else -1.42
            self._update_xy(victim)"""

new_spin_teleport = """            victim.target_d = 1.35 if victim.d >= 0.0 else -1.35"""

assert old_spin_teleport in text, "old_spin_teleport not found"
text = text.replace(old_spin_teleport, new_spin_teleport)

# C. In _on_physical_contact: authentic damage for on-track bumping
old_contact_side = """        if is_side_by_side:
            # Physical lateral separation impulse
            d_diff = c1.d - c2.d
            side_norm = 1.0 if d_diff >= 0.0 else -1.0
            c1.d = max(-1.12, min(1.12, c1.d + side_norm * 0.14))
            c2.d = max(-1.12, min(1.12, c2.d - side_norm * 0.14))
            self._update_xy(c1)
            self._update_xy(c2)
            c1.sparks = True
            c2.sparks = True

            # Clean F1 wheel-to-wheel racing: zero wing damage and zero false alerts
            # Only trigger an incident on severe, violent speed mismatch (> 9.4 m/s / 34 km/h)
            if speed_gap > 9.4:"""

new_contact_side = """        if is_side_by_side:
            # Physical lateral separation impulse (smooth target guidance, zero snap!)
            d_diff = c1.d - c2.d
            side_norm = 1.0 if d_diff >= 0.0 else -1.0
            c1.target_d = max(-1.05, min(1.05, c1.d + side_norm * 0.18))
            c2.target_d = max(-1.05, min(1.05, c2.d - side_norm * 0.18))
            c1.sparks = True
            c2.sparks = True
            # Authentic sidepod/endplate abrasion damage whenever physical contact occurs
            contact_dmg = random.uniform(0.04, 0.09)
            c1.wing_damage = min(0.85, c1.wing_damage + contact_dmg)
            c2.wing_damage = min(0.85, c2.wing_damage + contact_dmg)
            c1.tire_wear = min(0.99, c1.tire_wear + 0.008)
            c2.tire_wear = min(0.99, c2.tire_wear + 0.008)

            if speed_gap > 5.5:"""

assert old_contact_side in text, "old_contact_side not found"
text = text.replace(old_contact_side, new_contact_side)

# D. In _on_physical_contact rear-end collision: authentic damage threshold
old_contact_rear = """            # High closing speed (> 7.4 m/s / 27 km/h) damages front wing
            if delta_v > 7.4:"""

new_contact_rear = """            # Authentic damage: trailing car front wing takes real damage on closing contact (> 2.2 m/s / 8 km/h)
            rear_dmg = min(0.35, max(0.08, delta_v * 0.038))
            behind.wing_damage = min(0.85, behind.wing_damage + rear_dmg)
            behind.wing_damage_side = "RIGHT" if behind.d > ahead.d else "LEFT"
            behind.repair_cost_m += round(rear_dmg * 0.65, 2)
            ahead.tire_wear = min(0.99, ahead.tire_wear + 0.012)
            if behind.wing_damage >= 0.35 and not behind.box_this_lap:
                behind.box_this_lap = True

            if delta_v > 6.0:"""

assert old_contact_rear in text, "old_contact_rear not found"
text = text.replace(old_contact_rear, new_contact_rear)

phys_file.write_text(text, encoding="utf-8")
print("Successfully applied full physics overhaul to sim/physics.py")

