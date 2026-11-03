import sys

with open("public/canvas.js", "r", encoding="utf-8") as f:
    text = f.read()

# 1. Update pushTick
old_push_tick_start = """  pushTick(tick) {
    const now = performance.now();
    this.tick = tick;
    if (!tick || !tick.cars) return;

    const seen = new Set();
    for (const c of tick.cars) {
      seen.add(c.id);
      const prev = this.carInterp.get(c.id);
      if (!prev || Math.hypot(c.x - prev.cx, c.y - prev.cy) > 65) {
        this.carInterp.set(c.id, {
          sx: c.x, sy: c.y, sh: c.h,
          tx: c.x, ty: c.y, th: c.h,
          cx: c.x, cy: c.y, ch: c.h,
          t0: now,
          spanMs: 50.0,
          data: c,
        });
      } else {
        prev.sx = prev.cx;
        prev.sy = prev.cy;
        prev.sh = prev.ch;
        prev.tx = c.x;
        prev.ty = c.y;
        prev.th = c.h;
        const delta = Math.max(25.0, Math.min(120.0, now - prev.t0));
        prev.spanMs = prev.spanMs ? (prev.spanMs * 0.75 + delta * 0.25) : delta;
        prev.t0 = now;
        prev.data = c;
      }"""

new_push_tick_start = """  pushTick(tick) {
    const now = performance.now();
    this.tick = tick;
    if (!tick || !tick.cars) return;

    // Snapshot stream clock synchronization:
    // Maintains a stable 65ms playback buffer against server simulation ticks.
    // Completely eliminates inter-packet velocity jitter and micro-stutters.
    const tickTime = tick.sim_time != null ? tick.sim_time * 1000 : now;
    if (!this.renderTimeInitialized) {
      this.renderTime = tickTime - 65.0;
      this.renderTimeInitialized = true;
    } else {
      const targetRenderTime = tickTime - 65.0;
      const timeDiff = targetRenderTime - this.renderTime;
      if (Math.abs(timeDiff) > 350) {
        this.renderTime = targetRenderTime;
      } else {
        this.renderTime += timeDiff * 0.08;
      }
    }

    const seen = new Set();
    for (const c of tick.cars) {
      seen.add(c.id);
      let st = this.carInterp.get(c.id);
      if (!st || Math.hypot(c.x - st.cx, c.y - st.cy) > 75) {
        st = {
          cx: c.x,
          cy: c.y,
          ch: c.h,
          buffer: [{ t: tickTime, x: c.x, y: c.y, h: c.h }],
          data: c,
        };
        this.carInterp.set(c.id, st);
      } else {
        st.data = c;
        st.buffer.push({ t: tickTime, x: c.x, y: c.y, h: c.h });
        if (st.buffer.length > 8) {
          st.buffer.shift();
        }
      }"""

assert old_push_tick_start in text, "Could not find old_push_tick_start"
text = text.replace(old_push_tick_start, new_push_tick_start, 1)

# 2. Update Safety Car in pushTick
old_sc = """    if (tick.sc) {
      if (!this.scInterp || Math.hypot(tick.sc.x - this.scInterp.cx, tick.sc.y - this.scInterp.cy) > 65) {
        this.scInterp = {
          sx: tick.sc.x, sy: tick.sc.y, sh: tick.sc.h,
          tx: tick.sc.x, ty: tick.sc.y, th: tick.sc.h,
          cx: tick.sc.x, cy: tick.sc.y, ch: tick.sc.h,
          t0: now,
          spanMs: 50.0,
        };
      } else {
        this.scInterp.sx = this.scInterp.cx;
        this.scInterp.sy = this.scInterp.cy;
        this.scInterp.sh = this.scInterp.ch;
        this.scInterp.tx = tick.sc.x;
        this.scInterp.ty = tick.sc.y;
        this.scInterp.th = tick.sc.h;
        const delta = Math.max(25.0, Math.min(120.0, now - this.scInterp.t0));
        this.scInterp.spanMs = this.scInterp.spanMs ? (this.scInterp.spanMs * 0.75 + delta * 0.25) : delta;
        this.scInterp.t0 = now;
      }
    } else {
      this.scInterp = null;
    }"""

new_sc = """    if (tick.sc) {
      if (!this.scInterp || Math.hypot(tick.sc.x - this.scInterp.cx, tick.sc.y - this.scInterp.cy) > 75) {
        this.scInterp = {
          cx: tick.sc.x,
          cy: tick.sc.y,
          ch: tick.sc.h,
          buffer: [{ t: tickTime, x: tick.sc.x, y: tick.sc.y, h: tick.sc.h }],
        };
      } else {
        this.scInterp.buffer.push({ t: tickTime, x: tick.sc.x, y: tick.sc.y, h: tick.sc.h });
        if (this.scInterp.buffer.length > 8) {
          this.scInterp.buffer.shift();
        }
      }
    } else {
      this.scInterp = null;
    }"""

assert old_sc in text, "Could not find old_sc"
text = text.replace(old_sc, new_sc, 1)

# 3. Update _updateInterpolation and _updateCamera
old_interp_and_cam = """  _updateInterpolation(now, dt) {
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
    }

    const nextP = [];
    for (const p of this.particles) {
      p.life -= dt;
      if (p.life > 0) {
        p.x += p.vx * dt;
        p.y += p.vy * dt;
        nextP.push(p);
      }
    }
    this.particles = nextP;
  }

  _updateCamera(dt) {
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

new_interp_and_cam = """  _updateInterpolation(now, dt) {
    if (!this.renderTimeInitialized) return;

    // Advance continuous client render timeline smoothly at display refresh rate
    const clampedDt = Math.max(0.001, Math.min(0.05, dt));
    this.renderTime += clampedDt * 1000;

    const interpolateEntity = (st) => {
      const buf = st.buffer;
      if (!buf || buf.length === 0) return;

      if (buf.length >= 2) {
        let idx = -1;
        for (let i = 0; i < buf.length - 1; i++) {
          if (buf[i].t <= this.renderTime && this.renderTime <= buf[i + 1].t) {
            idx = i;
            break;
          }
        }

        if (idx !== -1) {
          const s0 = buf[idx];
          const s1 = buf[idx + 1];
          const span = Math.max(1.0, s1.t - s0.t);
          const alpha = Math.max(0.0, Math.min(1.0, (this.renderTime - s0.t) / span));
          st.cx = s0.x + (s1.x - s0.x) * alpha;
          st.cy = s0.y + (s1.y - s0.y) * alpha;
          st.ch = lerpAngle(s0.h, s1.h, alpha);
        } else if (this.renderTime < buf[0].t) {
          st.cx = buf[0].x;
          st.cy = buf[0].y;
          st.ch = buf[0].h;
        } else {
          // If network tick arrived late, glide forward with last observed velocity
          const last = buf[buf.length - 1];
          const prev = buf[buf.length - 2];
          const dtSnap = Math.max(1.0, last.t - prev.t);
          const vx = (last.x - prev.x) / dtSnap;
          const vy = (last.y - prev.y) / dtSnap;
          const extraMs = Math.min(60.0, this.renderTime - last.t);
          st.cx = last.x + vx * extraMs;
          st.cy = last.y + vy * extraMs;
          st.ch = last.h;
        }
      } else {
        st.cx = buf[0].x;
        st.cy = buf[0].y;
        st.ch = buf[0].h;
      }
    };

    for (const st of this.carInterp.values()) {
      interpolateEntity(st);
    }
    if (this.scInterp) {
      interpolateEntity(this.scInterp);
    }

    const nextP = [];
    for (const p of this.particles) {
      p.life -= dt;
      if (p.life > 0) {
        p.x += p.vx * dt;
        p.y += p.vy * dt;
        nextP.push(p);
      }
    }
    this.particles = nextP;
  }

  _updateCamera(dt) {
    const bounds = this.track?.bounds;
    let targetX = bounds ? (bounds.min_x + bounds.max_x) * .5 : 500;
    let targetY = bounds ? (bounds.min_y + bounds.max_y) * .5 : 325;
    const zoomRatio = bounds ? Math.max((bounds.max_x - bounds.min_x) / 880, (bounds.max_y - bounds.min_y) / 545) : 1;
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
        // Firmly centered on the focused car - eliminates corner lookahead swinging
        targetX = targetCarSt.cx;
        targetY = targetCarSt.cy;
      }
    }

    if (isTrackingCar) {
      const dist = Math.hypot(targetX - this.camX, targetY - this.camY);
      if (dist > 35.0) {
        // Smooth cinematic pan from previous car or full view
        const kFly = 1.0 - Math.exp(-dt * 6.5);
        this.camX += (targetX - this.camX) * kFly;
        this.camY += (targetY - this.camY) * kFly;
      } else if (dist > 0.05) {
        // Fast asymptotic settle onto car center (eliminates braking/accel rubber-banding)
        const kSettle = 1.0 - Math.exp(-dt * 24.0);
        this.camX += (targetX - this.camX) * kSettle;
        this.camY += (targetY - this.camY) * kSettle;
      } else {
        // Perfectly locked to car center
        this.camX = targetX;
        this.camY = targetY;
      }
    } else {
      // Full circuit view
      const kFull = 1.0 - Math.exp(-dt * 5.0);
      this.camX += (targetX - this.camX) * kFull;
      this.camY += (targetY - this.camY) * kFull;
    }

    const zoomRate = 5.0;
    const kZoom = 1.0 - Math.exp(-dt * zoomRate);
    this.camZoom += (targetZoom - this.camZoom) * kZoom;
  }"""

assert old_interp_and_cam in text, "Could not find old_interp_and_cam"
text = text.replace(old_interp_and_cam, new_interp_and_cam, 1)

with open("public/canvas.js", "w", encoding="utf-8") as f:
    f.write(text)

print("Successfully patched public/canvas.js with smooth snapshot buffer and lock camera system!")

