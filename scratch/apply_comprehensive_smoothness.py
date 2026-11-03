"""Apply comprehensive velocity smoothing and exact dt-scaled heading rate limiting."""
import pathlib

ROOT = pathlib.Path(r"c:\Coding\F1Sim2D")
phys_file = ROOT / "sim" / "physics.py"
text = phys_file.read_text(encoding="utf-8")

# 1. Store _current_dt in RaceSession.step and QualifyingSession.step
old_step_r = """    def step(self, dt: float, event_cb) -> None:
        if self.finished:
            return
        self.tick_count += 1

        if not self.lights_out:"""

new_step_r = """    def step(self, dt: float, event_cb) -> None:
        if self.finished:
            return
        self.tick_count += 1
        self._current_dt = dt

        if not self.lights_out:"""

assert old_step_r in text, "old_step_r not found"
text = text.replace(old_step_r, new_step_r)

old_step_q = """    def step(self, dt: float, event_cb) -> None:
        if self.finished:
            return
        self.tick_count += 1
        self.elapsed += dt"""

new_step_q = """    def step(self, dt: float, event_cb) -> None:
        if self.finished:
            return
        self.tick_count += 1
        self._current_dt = dt
        self.elapsed += dt"""

assert old_step_q in text, "old_step_q not found"
text = text.replace(old_step_q, new_step_q)

# 2. Scale max_dh by cur_dt in both _update_xy methods
old_xy_block = """            prev_h = getattr(car, "heading", None)
            if prev_h is not None and getattr(car, "_has_initial_heading", False):
                dh = (target_heading - prev_h + math.pi) % (2.0 * math.pi) - math.pi
                max_dh = 5.5 * 0.05
                dh_clamped = max(-max_dh, min(max_dh, dh))
                car.heading = round((prev_h + dh_clamped + math.pi) % (2.0 * math.pi) - math.pi, 4)
            else:
                car.heading = round(target_heading, 4)
                car._has_initial_heading = True"""

new_xy_block = """            prev_h = getattr(car, "heading", None)
            cur_dt = getattr(self, "_current_dt", 0.05)
            if prev_h is not None and getattr(car, "_has_initial_heading", False):
                dh = (target_heading - prev_h + math.pi) % (2.0 * math.pi) - math.pi
                max_dh = 4.8 * cur_dt
                dh_clamped = max(-max_dh, min(max_dh, dh))
                car.heading = round((prev_h + dh_clamped + math.pi) % (2.0 * math.pi) - math.pi, 4)
            else:
                car.heading = round(target_heading, 4)
                car._has_initial_heading = True"""

assert old_xy_block in text, "old_xy_block not found"
text = text.replace(old_xy_block, new_xy_block)

# 4. Smooth pit fast-lane queue deceleration
old_pit_q = """                behind.total_dist -= soft_shift
                behind.s = behind.total_dist % L
                behind.v = min(behind.v, ahead.v)"""

new_pit_q = """                behind.total_dist -= soft_shift
                behind.s = behind.total_dist % L
                if behind.v > ahead.v:
                    behind.v = max(ahead.v, behind.v - 24.0 * 0.05)"""

assert old_pit_q in text, "old_pit_q not found"
text = text.replace(old_pit_q, new_pit_q)

# 5. Smooth team order hold & yellow flag speed matching in _resolve_battles_and_incidents
old_team_hold = """            if attacker.team_id == defender.team_id and attacker.team_order == "HOLD":
                attacker.v = min(attacker.v, defender.v * 0.995)
                continue"""

new_team_hold = """            if attacker.team_id == defender.team_id and attacker.team_order == "HOLD":
                if attacker.v > defender.v * 0.995:
                    attacker.v = max(defender.v * 0.995, attacker.v - 24.0 * dt)
                continue"""

assert old_team_hold in text, "old_team_hold not found"
text = text.replace(old_team_hold, new_team_hold)

old_yellow_speed = """                    attacker.v = min(attacker.v, defender.v)
                    continue"""

new_yellow_speed = """                    if attacker.v > defender.v:
                        attacker.v = max(defender.v, attacker.v - 28.0 * dt)
                    continue"""

assert old_yellow_speed in text, "old_yellow_speed not found"
text = text.replace(old_yellow_speed, new_yellow_speed)

phys_file.write_text(text, encoding="utf-8")
print("Successfully applied comprehensive smoothness updates to sim/physics.py")
