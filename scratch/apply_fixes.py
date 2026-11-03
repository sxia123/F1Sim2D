"""Apply smoothness, heading, blue-yield and active-pass fixes."""
import pathlib

ROOT = pathlib.Path(r"c:\Coding\F1Sim2D")

# --- 1. Modify sim/physics.py ---
phys_file = ROOT / "sim" / "physics.py"
phys_text = phys_file.read_text(encoding="utf-8")

# A. Blue flag speed override removal
old_blue = """                    deficit = min_long_m - ds_m
                    if deficit > 0:
                        if is_blue_yield:
                            c.v = max(c.v, o.v * 1.02)
                        else:
                            c.v = max(4.0, max(o.v * 0.98, c.v - 22.0 * 0.05))
                        soft_shift = min(deficit * 0.30 + 0.02, 0.25)"""

new_blue = """                    deficit = min_long_m - ds_m
                    if deficit > 0:
                        c.v = max(4.0, max(o.v * 0.98, c.v - 22.0 * 0.05))
                        soft_shift = min(deficit * 0.30 + 0.02, 0.25)"""

assert old_blue in phys_text, "Failed to find old_blue in physics.py"
phys_text = phys_text.replace(old_blue, new_blue)

# B. CarState heading fields
old_carstate = """        self.x: float = 0.0
        self.y: float = 0.0
        self.heading: float = 0.0

        # 2026 Active Aero & Hybrid ERS / Overtake Mode"""

new_carstate = """        self.x: float = 0.0
        self.y: float = 0.0
        self.heading: float = 0.0
        self._heading_tick: int = -1
        self._has_initial_heading: bool = False

        # 2026 Active Aero & Hybrid ERS / Overtake Mode"""

assert old_carstate in phys_text, "Failed to find old_carstate in physics.py"
phys_text = phys_text.replace(old_carstate, new_carstate)

# C. QualifyingSession tick_count and step
old_quali_init = """        self.elapsed: float = 0.0
        self.fastest_time: float | None = None"""

new_quali_init = """        self.elapsed: float = 0.0
        self.tick_count: int = 0
        self.fastest_time: float | None = None"""

assert old_quali_init in phys_text, "Failed to find old_quali_init in physics.py"
phys_text = phys_text.replace(old_quali_init, new_quali_init)

old_quali_step = """    def step(self, dt: float, event_cb) -> None:
        if self.finished:
            return
        self.elapsed += dt"""

new_quali_step = """    def step(self, dt: float, event_cb) -> None:
        if self.finished:
            return
        self.tick_count += 1
        self.elapsed += dt"""

assert old_quali_step in phys_text, "Failed to find old_quali_step in physics.py"
phys_text = phys_text.replace(old_quali_step, new_quali_step)

# D. QualifyingSession _update_xy
old_quali_xy = """        # Dynamic course and apex yaw attitude (rate-limited, no snap)
        tx, ty = smp["tx"], smp["ty"]
        nx, ny = smp["nx"], smp["ny"]
        half_usable = self.track.track_width_px * 0.39
        v_forward_px = max(6.0, car.v * self.track.px_per_m)
        v_lateral_px = (car.target_d - car.d) * 2.8 * half_usable * 0.18
        drift_angle = max(-0.065, min(0.065, math.atan2(v_lateral_px, v_forward_px)))
        track_heading = math.atan2(ty, tx)
        yaw_attitude = getattr(car, "steer_angle", 0.0) * 0.20
        target_heading = (track_heading + drift_angle + yaw_attitude + math.pi) % (2.0 * math.pi) - math.pi

        prev_h = getattr(car, "heading", None)
        if prev_h is not None and getattr(car, "_has_initial_heading", False):
            dh = (target_heading - prev_h + math.pi) % (2.0 * math.pi) - math.pi
            max_dh = 8.5 * 0.05
            dh_clamped = max(-max_dh, min(max_dh, dh))
            car.heading = round((prev_h + dh_clamped + math.pi) % (2.0 * math.pi) - math.pi, 4)
        else:
            car.heading = round(target_heading, 4)
            car._has_initial_heading = True"""

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
            if prev_h is not None and getattr(car, "_has_initial_heading", False):
                dh = (target_heading - prev_h + math.pi) % (2.0 * math.pi) - math.pi
                max_dh = 5.5 * 0.05
                dh_clamped = max(-max_dh, min(max_dh, dh))
                car.heading = round((prev_h + dh_clamped + math.pi) % (2.0 * math.pi) - math.pi, 4)
            else:
                car.heading = round(target_heading, 4)
                car._has_initial_heading = True"""

assert old_quali_xy in phys_text, "Failed to find old_quali_xy in physics.py"
phys_text = phys_text.replace(old_quali_xy, new_quali_xy)

# E. RaceSession tick_count and step
old_race_init = """        self.race_clock: float = 0.0
        self.lights_countdown: float = 5.5"""

new_race_init = """        self.race_clock: float = 0.0
        self.tick_count: int = 0
        self.lights_countdown: float = 5.5"""

assert old_race_init in phys_text, "Failed to find old_race_init in physics.py"
phys_text = phys_text.replace(old_race_init, new_race_init)

old_race_step = """    def step(self, dt: float, event_cb) -> None:
        if self.finished:
            return

        if not self.lights_out:"""

new_race_step = """    def step(self, dt: float, event_cb) -> None:
        if self.finished:
            return
        self.tick_count += 1

        if not self.lights_out:"""

assert old_race_step in phys_text, "Failed to find old_race_step in physics.py"
phys_text = phys_text.replace(old_race_step, new_race_step)

# F. RaceSession _update_xy
old_race_xy = """        # 1. Course trajectory angle combining longitudinal speed and lateral maneuver velocity
        tx, ty = smp["tx"], smp["ty"]
        nx, ny = smp["nx"], smp["ny"]
        half_usable = self.track.track_width_px * 0.39
        v_forward_px = max(6.0, car.v * self.track.px_per_m)
        steer_rate = 5.8 if (car.maneuver_pass_timer > 0.0 or car.maneuver_timer > 0.0) else 2.8
        v_lateral_px = (car.target_d - car.d) * steer_rate * half_usable * 0.18

        drift_angle = max(-0.065, min(0.065, math.atan2(v_lateral_px, v_forward_px)))
        track_heading = math.atan2(ty, tx)

        # 2. Dynamic chassis yaw in corners (especially hairpins): car nose turns naturally into the apex
        yaw_attitude = getattr(car, "steer_angle", 0.0) * 0.20
        target_heading = (track_heading + drift_angle + yaw_attitude + math.pi) % (2.0 * math.pi) - math.pi

        prev_h = getattr(car, "heading", None)
        if prev_h is not None and getattr(car, "_has_initial_heading", False):
            dh = (target_heading - prev_h + math.pi) % (2.0 * math.pi) - math.pi
            max_dh = 8.5 * 0.05
            dh_clamped = max(-max_dh, min(max_dh, dh))
            car.heading = round((prev_h + dh_clamped + math.pi) % (2.0 * math.pi) - math.pi, 4)
        else:
            car.heading = round(target_heading, 4)
            car._has_initial_heading = True"""

new_race_xy = """        # Heading is integrated at most once per 50ms simulation tick to prevent multi-pass SAT multiplier artifacts
        curr_tick = getattr(self, "tick_count", 0)
        heading_stepped = (getattr(car, "_heading_tick", -1) == curr_tick)
        if not heading_stepped:
            car._heading_tick = curr_tick
            tx, ty = smp["tx"], smp["ty"]
            half_usable = self.track.track_width_px * 0.39
            v_forward_px = max(6.0, car.v * self.track.px_per_m)
            steer_rate = 3.2 if (car.maneuver_pass_timer > 0.0 or car.maneuver_timer > 0.0) else 2.4
            v_lateral_px = (car.target_d - car.d) * steer_rate * half_usable * 0.18

            drift_angle = max(-0.065, min(0.065, math.atan2(v_lateral_px, v_forward_px)))
            track_heading = math.atan2(ty, tx)

            # Dynamic chassis yaw in corners: car nose turns naturally into apex
            yaw_attitude = getattr(car, "steer_angle", 0.0) * 0.20
            target_heading = (track_heading + drift_angle + yaw_attitude + math.pi) % (2.0 * math.pi) - math.pi

            prev_h = getattr(car, "heading", None)
            if prev_h is not None and getattr(car, "_has_initial_heading", False):
                dh = (target_heading - prev_h + math.pi) % (2.0 * math.pi) - math.pi
                max_dh = 5.5 * 0.05
                dh_clamped = max(-max_dh, min(max_dh, dh))
                car.heading = round((prev_h + dh_clamped + math.pi) % (2.0 * math.pi) - math.pi, 4)
            else:
                car.heading = round(target_heading, 4)
                car._has_initial_heading = True"""

assert old_race_xy in phys_text, "Failed to find old_race_xy in physics.py"
phys_text = phys_text.replace(old_race_xy, new_race_xy)

# G. Active pass envelope clamping in _resolve_battles_and_incidents
old_env1 = """                        if lat_sep >= CAR_WID_PX * 0.86:
                            st_c = self.track.sample(c.s)["station"]
                            v_env_c = self.v_env[st_c]
                            c.v = min(v_env_c, c.v + 16.0 * dt)"""

new_env1 = """                        if lat_sep >= CAR_WID_PX * 0.86:
                            st_c = self.track.sample(c.s)["station"]
                            v_env_c = self.v_env[st_c]
                            if c.v < v_env_c:
                                c.v = min(v_env_c, c.v + 16.0 * dt)"""

assert old_env1 in phys_text, "Failed to find old_env1 in physics.py"
phys_text = phys_text.replace(old_env1, new_env1)

old_env2 = """                    if attacker.overtake_active:
                        # Slingshot punch: attacker surges past defender with smooth envelope-bounded velocity
                        attacker.v = min(self.v_env[st], attacker.v + 1.2)"""

new_env2 = """                    if attacker.overtake_active:
                        # Slingshot punch: attacker surges past defender with smooth envelope-bounded velocity
                        if attacker.v < self.v_env[st]:
                            attacker.v = min(self.v_env[st], attacker.v + 1.2)"""

assert old_env2 in phys_text, "Failed to find old_env2 in physics.py"
phys_text = phys_text.replace(old_env2, new_env2)

phys_file.write_text(phys_text, encoding="utf-8")
print("Successfully updated sim/physics.py")

# --- 2. Modify public/canvas.js ---
canvas_file = ROOT / "public" / "canvas.js"
canvas_text = canvas_file.read_text(encoding="utf-8")

old_canvas_interp = """  _updateInterpolation(now, dt) {
    for (const st of this.carInterp.values()) {
      const span = st.spanMs || 50.0;
      const elapsed = now - st.t0;
      if (elapsed <= span) {
        // Uniform linear glide between periodic network updates (zero 20Hz micro-stutter)
        const alpha = Math.max(0.0, Math.min(1.0, elapsed / span));
        st.cx = st.sx + (st.tx - st.sx) * alpha;
        st.cy = st.sy + (st.ty - st.sy) * alpha;
        st.ch = lerpAngle(st.sh, st.th, alpha);
      } else {
        // Continuous forward extrapolation during minor network jitter (never freezes!)
        const overSec = Math.min(0.09, (elapsed - span) / 1000.0);
        const kph = (st.data && st.data.kph != null) ? st.data.kph : 180.0;
        const pxPerM = (this.track && this.track.px_per_m) ? this.track.px_per_m : 0.28;
        const vPxSec = (kph / 3.6) * pxPerM;
        st.cx = st.tx + Math.cos(st.th) * vPxSec * overSec;
        st.cy = st.ty + Math.sin(st.th) * vPxSec * overSec;
        st.ch = st.th;
      }
    }
    if (this.scInterp) {
      const span = this.scInterp.spanMs || 50.0;
      const elapsed = now - this.scInterp.t0;
      if (elapsed <= span) {
        const alpha = Math.max(0.0, Math.min(1.0, elapsed / span));
        this.scInterp.cx = this.scInterp.sx + (this.scInterp.tx - this.scInterp.sx) * alpha;
        this.scInterp.cy = this.scInterp.sy + (this.scInterp.ty - this.scInterp.sy) * alpha;
        this.scInterp.ch = lerpAngle(this.scInterp.sh, this.scInterp.th, alpha);
      } else {
        const overSec = Math.min(0.09, (elapsed - span) / 1000.0);
        const pxPerM = (this.track && this.track.px_per_m) ? this.track.px_per_m : 0.28;
        const vPxSec = 22.2 * pxPerM;
        this.scInterp.cx = this.scInterp.tx + Math.cos(this.scInterp.th) * vPxSec * overSec;
        this.scInterp.cy = this.scInterp.ty + Math.sin(this.scInterp.th) * vPxSec * overSec;
        this.scInterp.ch = this.scInterp.th;
      }
    }"""

new_canvas_interp = """  _updateInterpolation(now, dt) {
    for (const st of this.carInterp.values()) {
      const span = st.spanMs || 50.0;
      const elapsed = now - st.t0;
      // Butter-smooth monotonic glide between server network ticks (no extrapolation snapping/stuttering)
      const alpha = Math.max(0.0, Math.min(1.0, elapsed / span));
      st.cx = st.sx + (st.tx - st.sx) * alpha;
      st.cy = st.sy + (st.ty - st.sy) * alpha;
      st.ch = lerpAngle(st.sh, st.th, alpha);
    }
    if (this.scInterp) {
      const span = this.scInterp.spanMs || 50.0;
      const elapsed = now - this.scInterp.t0;
      const alpha = Math.max(0.0, Math.min(1.0, elapsed / span));
      this.scInterp.cx = this.scInterp.sx + (this.scInterp.tx - this.scInterp.sx) * alpha;
      this.scInterp.cy = this.scInterp.sy + (this.scInterp.ty - this.scInterp.sy) * alpha;
      this.scInterp.ch = lerpAngle(this.scInterp.sh, this.scInterp.th, alpha);
    }"""

assert old_canvas_interp in canvas_text, "Failed to find old_canvas_interp in canvas.js"
canvas_text = canvas_text.replace(old_canvas_interp, new_canvas_interp)

canvas_file.write_text(canvas_text, encoding="utf-8")
print("Successfully updated public/canvas.js")

