from pathlib import Path

# 1. Update sim/physics.py
p_phys = Path("sim/physics.py")
text_phys = p_phys.read_text(encoding="utf-8")

old_stages = """        if is_sprint_quali:
            self.stages = [("SQ1", 28.0, 16), ("SQ2", 24.0, 10), ("SQ3", 22.0, 0)]
        else:
            self.stages = [("Q1", 34.0, 16), ("Q2", 28.0, 10), ("Q3", 24.0, 0)]"""

new_stages = """        if is_sprint_quali:
            self.stages = [("SQ1", 180.0, 16), ("SQ2", 180.0, 10), ("SQ3", 180.0, 0)]
        else:
            self.stages = [("Q1", 180.0, 16), ("Q2", 180.0, 10), ("Q3", 180.0, 0)]"""

assert old_stages in text_phys, "old_stages not found in physics.py"
text_phys = text_phys.replace(old_stages, new_stages, 1)

old_advance = """    def advance_stage(self, event_cb) -> None:
        \"\"\"Fast-forward the current knockout stage (Q1, Q2, or Q3) to completion.\"\"\"
        target_stage = self.stage_idx
        guard = 0
        while not self.finished and self.stage_idx == target_stage and guard < 400:
            self.step(0.5, event_cb)
            guard += 1"""

new_advance = """    def advance_stage(self, event_cb) -> None:
        \"\"\"Fast-forward the current knockout stage (Q1, Q2, or Q3) to completion.\"\"\"
        target_stage = self.stage_idx
        guard = 0
        while not self.finished and self.stage_idx == target_stage and guard < 600:
            self.step(1.0, event_cb)
            guard += 1"""

assert old_advance in text_phys, "old_advance not found in physics.py"
text_phys = text_phys.replace(old_advance, new_advance, 1)

p_phys.write_text(text_phys, encoding="utf-8")
print("sim/physics.py successfully updated with 3-minute qualifying stages!")

# 2. Update public/app.js for mm:ss display
p_app = Path("public/app.js")
text_app = p_app.read_text(encoding="utf-8")

old_clock_fmt = """    } else if (tick.phase === "QUALIFYING" || tick.phase === "SPRINT_QUALIFYING") {
      const stg = tick.quali_stage || (tick.phase === "SPRINT_QUALIFYING" ? "SQ" : "QUALI");
      sessEl.textContent = `${stg}  00:${String(Math.floor(tick.clock)).padStart(2, "0")}`;"""

new_clock_fmt = """    } else if (tick.phase === "QUALIFYING" || tick.phase === "SPRINT_QUALIFYING") {
      const stg = tick.quali_stage || (tick.phase === "SPRINT_QUALIFYING" ? "SQ" : "QUALI");
      const m = Math.floor(tick.clock / 60);
      const s = Math.floor(tick.clock % 60);
      sessEl.textContent = `${stg}  ${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;"""

assert old_clock_fmt in text_app, "old_clock_fmt not found in app.js"
text_app = text_app.replace(old_clock_fmt, new_clock_fmt, 1)

p_app.write_text(text_app, encoding="utf-8")
print("public/app.js successfully updated with mm:ss qualifying clock formatting!")

