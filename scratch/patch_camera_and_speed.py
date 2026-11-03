from pathlib import Path

# 1. Patch sim/championship.py
p_champ = Path("sim/championship.py")
text_champ = p_champ.read_text(encoding="utf-8")

old_allowed = "allowed = [0.0, 1.0, 2.0, 4.0, 8.0, 16.0]"
new_allowed = "allowed = [0.0, 0.5, 1.0, 2.0, 4.0, 8.0, 16.0]"
if old_allowed in text_champ:
    text_champ = text_champ.replace(old_allowed, new_allowed, 1)

old_comment = "self.sim_speed: float = 1.0  # 0.0 (paused), 1.0, 2.0, 4.0, 8.0, 16.0"
new_comment = "self.sim_speed: float = 1.0  # 0.0 (paused), 0.5 (slow-mo), 1.0, 2.0, 4.0, 8.0, 16.0"
if old_comment in text_champ:
    text_champ = text_champ.replace(old_comment, new_comment, 1)

p_champ.write_text(text_champ, encoding="utf-8")
print("sim/championship.py successfully patched with 0.5x speed support!")

# 2. Patch public/index.html
p_html = Path("public/index.html")
text_html = p_html.read_text(encoding="utf-8")

old_warp = """        <div class="speed-group" role="group" aria-label="Simulation Rate">
          <button class="spd-btn" data-speed="0" title="Hold Simulation">HOLD</button>
          <button class="spd-btn active" data-speed="1">1X</button>"""

new_warp = """        <div class="speed-group" role="group" aria-label="Simulation Rate">
          <button class="spd-btn" data-speed="0" title="Hold Simulation">HOLD</button>
          <button class="spd-btn" data-speed="0.5" title="Slow Motion (0.5x)">0.5X</button>
          <button class="spd-btn active" data-speed="1">1X</button>"""

assert old_warp in text_html, "old_warp not found in index.html"
text_html = text_html.replace(old_warp, new_warp, 1)

p_html.write_text(text_html, encoding="utf-8")
print("public/index.html successfully patched with 0.5X speed button!")

# 3. Patch public/canvas.js
p_canvas = Path("public/canvas.js")
text_canvas = p_canvas.read_text(encoding="utf-8")

# A. Continuous velocity glide in _updateInterpolation
old_interp = """  _updateInterpolation(now, dt) {
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

new_interp = """  _updateInterpolation(now, dt) {
    for (const st of this.carInterp.values()) {
      const span = st.spanMs || 50.0;
      const elapsed = now - st.t0;
      const alpha = elapsed / span;
      if (alpha <= 1.0) {
        st.cx = st.sx + (st.tx - st.sx) * alpha;
        st.cy = st.sy + (st.ty - st.sy) * alpha;
        st.ch = lerpAngle(st.sh, st.th, alpha);
      } else if (alpha <= 1.5) {
        // Continuous smooth velocity glide between server ticks (eliminates micro-freezes and hitching)
        const extra = Math.min(0.5, alpha - 1.0);
        st.cx = st.tx + (st.tx - st.sx) * extra;
        st.cy = st.ty + (st.ty - st.sy) * extra;
        st.ch = st.th;
      }
    }
    if (this.scInterp) {
      const span = this.scInterp.spanMs || 50.0;
      const elapsed = now - this.scInterp.t0;
      const alpha = elapsed / span;
      if (alpha <= 1.0) {
        this.scInterp.cx = this.scInterp.sx + (this.scInterp.tx - this.scInterp.sx) * alpha;
        this.scInterp.cy = this.scInterp.sy + (this.scInterp.ty - this.scInterp.sy) * alpha;
        this.scInterp.ch = lerpAngle(this.scInterp.sh, this.scInterp.th, alpha);
      } else if (alpha <= 1.5) {
        const extra = Math.min(0.5, alpha - 1.0);
        this.scInterp.cx = this.scInterp.tx + (this.scInterp.tx - this.scInterp.sx) * extra;
        this.scInterp.cy = this.scInterp.ty + (this.scInterp.ty - this.scInterp.sy) * extra;
        this.scInterp.ch = this.scInterp.th;
      }
    }"""

assert old_interp in text_canvas, "old_interp not found in canvas.js"
text_canvas = text_canvas.replace(old_interp, new_interp, 1)

# B. Responsive critically damped camera tracking with smooth forward lookahead
old_cam = """  _updateCamera(dt) {
    const bounds = this.track?.bounds;
    let targetX = bounds ? (bounds.min_x + bounds.max_x) * .5 : 500;
    let targetY = bounds ? (bounds.min_y + bounds.max_y) * .5 : 325;
    const zoomRatio = bounds ? Math.max((bounds.max_x-bounds.min_x)/880, (bounds.max_y-bounds.min_y)/545) : 1;
    let targetZoom = 1.0;

    if (this.tick && this.carInterp.size > 0 && this.cameraMode !== "full") {
      if (this.cameraMode === "leader") {
        const ldr = this.tick.cars[0];
        const st = ldr && this.carInterp.get(ldr.id);
        if (st) {
          targetX = st.cx;
          targetY = st.cy;
          targetZoom = 2.35 * zoomRatio;
        }
      } else if (this.cameraMode === "selected" && this.selectedDriverId) {
        const st = this.carInterp.get(this.selectedDriverId);
        if (st) {
          targetX = st.cx;
          targetY = st.cy;
          targetZoom = 2.75 * zoomRatio;
        }
      } else if (this.cameraMode === "team") {
        const myCars = this.tick.cars.filter((c) => c.tid === this.tick.player_team_id && !c.dnf);
        if (myCars.length > 0) {
          const st = this.carInterp.get(myCars[0].id);
          if (st) {
            targetX = st.cx;
            targetY = st.cy;
            targetZoom = 2.25 * zoomRatio;
          }
        }
      } else if (this.cameraMode === "battle") {
        const battling =
          this.tick.cars.find((c) => c.battle && c.ovt && !c.dnf) ||
          this.tick.cars.find((c) => c.battle && !c.dnf) ||
          this.tick.cars[0];
        if (battling) {
          const st = this.carInterp.get(battling.id);
          if (st) {
            targetX = st.cx;
            targetY = st.cy;
            targetZoom = 2.45 * zoomRatio;
          }
        }
      }
    }

    const k = Math.min(1.0, dt * 4.5);
    this.camX += (targetX - this.camX) * k;
    this.camY += (targetY - this.camY) * k;
    this.camZoom += (targetZoom - this.camZoom) * k;
  }"""

new_cam = """  _updateCamera(dt) {
    const bounds = this.track?.bounds;
    let targetX = bounds ? (bounds.min_x + bounds.max_x) * .5 : 500;
    let targetY = bounds ? (bounds.min_y + bounds.max_y) * .5 : 325;
    const zoomRatio = bounds ? Math.max((bounds.max_x-bounds.min_x)/880, (bounds.max_y-bounds.min_y)/545) : 1;
    let targetZoom = 1.0;
    let isTrackingCar = false;

    if (this.tick && this.carInterp.size > 0 && this.cameraMode !== "full") {
      let targetCarSt = null;
      if (this.cameraMode === "leader") {
        const ldr = this.tick.cars[0];
        targetCarSt = ldr && this.carInterp.get(ldr.id);
        if (targetCarSt) targetZoom = 2.35 * zoomRatio;
      } else if (this.cameraMode === "selected" && this.selectedDriverId) {
        targetCarSt = this.carInterp.get(this.selectedDriverId);
        if (targetCarSt) targetZoom = 2.75 * zoomRatio;
      } else if (this.cameraMode === "team") {
        const myCars = this.tick.cars.filter((c) => c.tid === this.tick.player_team_id && !c.dnf);
        if (myCars.length > 0) {
          targetCarSt = this.carInterp.get(myCars[0].id);
          if (targetCarSt) targetZoom = 2.25 * zoomRatio;
        }
      } else if (this.cameraMode === "battle") {
        const battling =
          this.tick.cars.find((c) => c.battle && c.ovt && !c.dnf) ||
          this.tick.cars.find((c) => c.battle && !c.dnf) ||
          this.tick.cars[0];
        if (battling) {
          targetCarSt = this.carInterp.get(battling.id);
          if (targetCarSt) targetZoom = 2.45 * zoomRatio;
        }
      }

      if (targetCarSt) {
        isTrackingCar = true;
        // Subtle forward lookahead along car velocity/heading direction to keep the racing line ahead in view
        const leadDist = 10.0;
        targetX = targetCarSt.cx + Math.cos(targetCarSt.ch) * leadDist;
        targetY = targetCarSt.cy + Math.sin(targetCarSt.ch) * leadDist;
      }
    }

    // Critically damped frame-rate independent camera tracking
    // Fast tight tracking (rate 16.0) eliminates sluggish drag-lag when focused on a car
    // Smooth cinematic ease (rate 5.0) for full-track overview & zoom transitions
    const posRate = isTrackingCar ? 16.0 : 5.0;
    const zoomRate = 5.0;
    const kPos = 1.0 - Math.exp(-dt * posRate);
    const kZoom = 1.0 - Math.exp(-dt * zoomRate);

    this.camX += (targetX - this.camX) * kPos;
    this.camY += (targetY - this.camY) * kPos;
    this.camZoom += (targetZoom - this.camZoom) * kZoom;
  }"""

assert old_cam in text_canvas, "old_cam not found in canvas.js"
text_canvas = text_canvas.replace(old_cam, new_cam, 1)

p_canvas.write_text(text_canvas, encoding="utf-8")
print("public/canvas.js successfully patched with smooth focused camera tracking and inter-tick extrapolation!")
