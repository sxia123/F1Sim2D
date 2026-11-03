// High-DPI 60fps 2D Real-GPS Circuit & Detailed 2026 F1 Car Renderer
import { getTeamLogoImage } from "/logos.js";
import { SceneryLayer } from "/scenery.js";
import { getCarSurfaces, getCarbonPaint } from "/car-materials.js";

const TIRE_COLORS = {
  SOFT: "#ff2800",
  MEDIUM: "#ffd200",
  HARD: "#f0f2f5",
  INTER: "#38b000",
  WET: "#0096ff",
};

const GARAGE_TEAM_IDS = [
  "mercedes",
  "ferrari",
  "redbull",
  "mclaren",
  "racingbulls",
  "alpine",
  "audi",
  "haas",
  "williams",
  "aston",
  "cadillac",
];

const GARAGE_TEAM_CODES = [
  "MER",
  "FER",
  "RBR",
  "MCL",
  "RB",
  "ALP",
  "AUD",
  "HAA",
  "WIL",
  "AMR",
  "CAD",
];

const TEAM_LIVERY = {
  mercedes: { body: "#141920", pod: "#bfc7d1", noseTip: "#00d2be", stripe: "#00d2be" },
  ferrari:  { body: "#dc0028", pod: "#c40022", noseTip: "#dc0028", stripe: "#ffffff" },
  redbull:  { body: "#131e3a", pod: "#17254a", noseTip: "#ffd200", stripe: "#e10600" },
  mclaren:  { body: "#15171e", pod: "#ff8000", noseTip: "#ff8000", stripe: "#ff8000" },
  racingbulls: { body: "#f4f6fa", pod: "#1d4ed8", noseTip: "#f4f6fa", stripe: "#6692ff" },
  alpine:   { body: "#0c2348", pod: "#0093cc", noseTip: "#ff87bc", stripe: "#ff87bc" },
  audi:     { body: "#b8c0c8", pod: "#181a20", noseTip: "#b8c0c8", stripe: "#f50537" },
  haas:     { body: "#eef2f6", pod: "#1b1e26", noseTip: "#eef2f6", stripe: "#e6002b" },
  williams: { body: "#0d2b6b", pod: "#1868db", noseTip: "#1868db", stripe: "#64c4ff" },
  aston:    { body: "#0f5c48", pod: "#229971", noseTip: "#229971", stripe: "#cedc00" },
  cadillac: { body: "#161922", pod: "#1e3f8f", noseTip: "#d4af37", stripe: "#d4af37" },
};

function lerpAngle(a, b, t) {
  const diff = ((b - a + Math.PI * 3) % (Math.PI * 2)) - Math.PI;
  return a + diff * t;
}

export class CircuitRenderer {
  constructor(canvas, onSelectDriver) {
    this.canvas = canvas;
    this.ctx = canvas.getContext("2d");
    this.onSelectDriver = onSelectDriver;

    this.track = null;
    this.scenery = new SceneryLayer();
    this.tick = null;
    this.cameraMode = "full";
    this.selectedDriverId = null;

    this.camX = 500;
    this.camY = 325;
    this.camZoom = 1.0;

    this.renderTime = 0;
    this.renderTimeInitialized = false;
    this.renderTick = 0;
    this.renderTickInitialized = false;
    this.playbackRate = 1.0;
    this.carInterp = new Map();
    this.scInterp = null;
    this.particles = [];
    this.rainDrops = Array.from({ length: 90 }, () => ({
      x: Math.random() * 1100,
      y: Math.random() * 720,
      spd: 9 + Math.random() * 6,
    }));

    this._lastFrameTs = performance.now();
    this._viewTransform = { scale: 1, ox: 0, oy: 0 };

    this._isPointerDown = false;
    this._pointerStartX = 0;
    this._pointerStartY = 0;
    this._lastPointerX = 0;
    this._lastPointerY = 0;
    this._hasDragged = false;
    this._activeTargetKey = null;
    this._camLocked = false;
    this._camTransitElapsed = 0;
    this._prevTargetX = 500;
    this._prevTargetY = 325;

    window.addEventListener("resize", () => this.resize());
    this.canvas.addEventListener("click", (e) => this._handleClick(e));

    this.canvas.addEventListener("pointerdown", (e) => {
      this._isPointerDown = true;
      this._pointerStartX = e.clientX;
      this._pointerStartY = e.clientY;
      this._lastPointerX = e.clientX;
      this._lastPointerY = e.clientY;
      this._hasDragged = false;
      try { this.canvas.setPointerCapture(e.pointerId); } catch (_) {}
    });

    this.canvas.addEventListener("pointermove", (e) => {
      if (!this._isPointerDown) return;
      const dx = e.clientX - this._lastPointerX;
      const dy = e.clientY - this._lastPointerY;
      this._lastPointerX = e.clientX;
      this._lastPointerY = e.clientY;

      const totalDist = Math.hypot(e.clientX - this._pointerStartX, e.clientY - this._pointerStartY);
      if (totalDist > 5) {
        this._hasDragged = true;
        this.cameraMode = "manual";
        this._camLocked = false;
        const scale = this._viewTransform.scale || 1;
        this.camX -= dx / scale;
        this.camY -= dy / scale;
      }
    });

    const finishPointer = (e) => {
      if (!this._isPointerDown) return;
      this._isPointerDown = false;
      try { this.canvas.releasePointerCapture(e.pointerId); } catch (_) {}
    };

    this.canvas.addEventListener("pointerup", finishPointer);
    this.canvas.addEventListener("pointercancel", finishPointer);

    this.canvas.addEventListener("wheel", (e) => {
      e.preventDefault();
      const zoomFactor = e.deltaY < 0 ? 1.15 : 0.87;
      const oldZoom = this.camZoom;
      const newZoom = Math.max(0.4, Math.min(6.5, oldZoom * zoomFactor));
      if (newZoom !== oldZoom) {
        this.cameraMode = "manual";
        this._camLocked = false;
        this.camZoom = newZoom;
      }
    }, { passive: false });

    this.resize();
    requestAnimationFrame((ts) => this._loop(ts));
  }

  resize() {
    const rect = this.canvas.parentElement.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    this.canvas.width = Math.max(300, Math.floor(rect.width * dpr));
    this.canvas.height = Math.max(220, Math.floor(rect.height * dpr));
    this.dpr = dpr;
    this.width = rect.width;
    this.height = rect.height;
  }

  setTrack(track) {
    if (!this.track || this.track.id !== track.id || this.track.geometry_revision !== track.geometry_revision) {
      this.carInterp.clear();
      this.scInterp = null;
      this.renderTimeInitialized = false;
      this.renderTickInitialized = false;
      this.renderTick = 0;
      this.playbackRate = 1.0;
      this.particles = [];
      this._activeTargetKey = null;
      this._camLocked = false;
      this._camTransitElapsed = 0;
      this._prevTargetX = 500;
      this._prevTargetY = 325;
      if (track.bounds) {
        this.camX = (track.bounds.min_x + track.bounds.max_x) * .5;
        this.camY = (track.bounds.min_y + track.bounds.max_y) * .5;
        this.camZoom = 1;
      }
    }
    this.track = track;
  }

  setCameraMode(mode) {
    this.cameraMode = mode;
    this._camLocked = false;
    this._camTransitElapsed = 0;
  }

  setSelectedDriver(driverId) {
    this.selectedDriverId = driverId;
    if (this.cameraMode === "selected") {
      this._camLocked = false;
      this._camTransitElapsed = 0;
    }
  }

  pushTick(tick) {
    const now = performance.now();
    this.tick = tick;
    if (!tick || !tick.cars) return;

    // Tick-Based Phase-Locked Loop (PLL) stream synchronization:
    // Decouples client rendering from network packet delivery jitter and timer irregularities.
    // Maintains a stable 2.2-tick (110ms) playback cushion behind server simulation.
    const currentTick = typeof tick.tick === "number" ? tick.tick : 0;
    const TARGET_BUFFER_TICKS = 2.2;
    if (!this.renderTickInitialized) {
      this.renderTick = currentTick - TARGET_BUFFER_TICKS;
      this.renderTickInitialized = true;
      this.renderTimeInitialized = true;
      this.renderTime = this.renderTick * 50.0;
      this.playbackRate = 1.0;
    } else {
      const targetTick = currentTick - TARGET_BUFFER_TICKS;
      const tickDiff = targetTick - this.renderTick;
      if (Math.abs(tickDiff) > 8.0) {
        // Hard resync only on tab refocus or massive network hitch
        this.renderTick = targetTick;
        this.renderTime = this.renderTick * 50.0;
        this.playbackRate = 1.0;
      } else {
        // Continuous time-dilation: gently nudge playback rate by +/- 4% max.
        // Never jump renderTick abruptly; guarantees 100% frame-to-frame continuity.
        this.playbackRate = 1.0 + Math.max(-0.05, Math.min(0.05, tickDiff * 0.08));
      }
    }

    const seen = new Set();
    for (const c of tick.cars) {
      seen.add(c.id);
      let st = this.carInterp.get(c.id);
      if (!st || Math.hypot(c.x - st.cx, c.y - st.cy) > 350.0) {
        st = {
          cx: c.x,
          cy: c.y,
          ch: c.h,
          buffer: [{ tick: currentTick, x: c.x, y: c.y, h: c.h }],
          data: c,
        };
        this.carInterp.set(c.id, st);
      } else {
        st.data = c;
        st.buffer.push({ tick: currentTick, x: c.x, y: c.y, h: c.h });
        if (st.buffer.length > 10) {
          st.buffer.shift();
        }
      }

      if (c.vis && c.kph > 40) {
        if (c.sparks) {
          for (let i = 0; i < 2; i++) {
            this.particles.push({
              x: c.x - Math.cos(c.h) * 6 + (Math.random() - 0.5) * 2.5,
              y: c.y - Math.sin(c.h) * 6 + (Math.random() - 0.5) * 2.5,
              vx: -Math.cos(c.h) * 18 + (Math.random() - 0.5) * 10,
              vy: -Math.sin(c.h) * 18 + (Math.random() - 0.5) * 10,
              life: 0.22,
              maxLife: 0.22,
              color: "#ff9e00",
              size: 1.5,
            });
          }
        }
        if (c.dmg > 15 && c.kph > 70 && Math.random() < 0.22) {
          this.particles.push({
            x: c.x + Math.cos(c.h) * 4.5 + (Math.random() - 0.5) * 3,
            y: c.y + Math.sin(c.h) * 4.5 + (Math.random() - 0.5) * 3,
            vx: -Math.cos(c.h) * 12 + (Math.random() - 0.5) * 8,
            vy: -Math.sin(c.h) * 12 + (Math.random() - 0.5) * 8,
            life: 0.36,
            maxLife: 0.36,
            color: "#181a20",
            size: 1.9,
          });
        }
        if (c.smoke > 0.2) {
          this.particles.push({
            x: c.x + (Math.random() - 0.5) * 4,
            y: c.y + (Math.random() - 0.5) * 4,
            vx: (Math.random() - 0.5) * 7,
            vy: (Math.random() - 0.5) * 7,
            life: 0.6,
            maxLife: 0.6,
            color: "rgba(210, 216, 224, 0.5)",
            size: 4.0 + Math.min(4.5, c.smoke * 1.3),
          });
        } else if (tick.wetness >= 22 && !c.in_pit && c.kph > 110 && Math.random() < 0.5) {
          this.particles.push({
            x: c.x - Math.cos(c.h) * 7.5,
            y: c.y - Math.sin(c.h) * 7.5,
            vx: -Math.cos(c.h) * 8 + (Math.random() - 0.5) * 4,
            vy: -Math.sin(c.h) * 8 + (Math.random() - 0.5) * 4,
            life: 0.32,
            maxLife: 0.32,
            color: "rgba(180, 215, 255, 0.28)",
            size: 3.1,
          });
        }
      }
    }

    for (const key of this.carInterp.keys()) {
      if (!seen.has(key)) this.carInterp.delete(key);
    }

    if (tick.sc) {
      if (!this.scInterp || Math.hypot(tick.sc.x - this.scInterp.cx, tick.sc.y - this.scInterp.cy) > 350.0) {
        this.scInterp = {
          cx: tick.sc.x,
          cy: tick.sc.y,
          ch: tick.sc.h,
          buffer: [{ tick: currentTick, x: tick.sc.x, y: tick.sc.y, h: tick.sc.h }],
        };
      } else {
        this.scInterp.buffer.push({ tick: currentTick, x: tick.sc.x, y: tick.sc.y, h: tick.sc.h });
        if (this.scInterp.buffer.length > 10) {
          this.scInterp.buffer.shift();
        }
      }
    } else {
      this.scInterp = null;
    }
  }

  _handleClick(e) {
    if (this._hasDragged) return;
    if (!this.tick) return;
    const rect = this.canvas.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;
    const { scale, ox, oy } = this._viewTransform;
    const wx = (mx - ox) / scale;
    const wy = (my - oy) / scale;

    let bestId = null;
    let bestDist = 14 / Math.max(scale, 0.001);
    for (const [id, st] of this.carInterp.entries()) {
      if (!st.data.vis) continue;
      const d = Math.hypot(st.cx - wx, st.cy - wy);
      if (d < bestDist) {
        bestDist = d;
        bestId = id;
      }
    }
    if (bestId && this.onSelectDriver) {
      this.onSelectDriver(bestId);
    }
  }

  _loop(ts) {
    const dt = Math.min(0.05, (ts - this._lastFrameTs) / 1000);
    this._lastFrameTs = ts;
    try {
      this._render(ts, dt);
    } catch (err) {
      console.error("Canvas render error:", err);
    }
    requestAnimationFrame((nextTs) => this._loop(nextTs));
  }

  _updateInterpolation(now, dt) {
    if (!this.renderTickInitialized) return;

    // Advance render timeline smoothly with continuous time dilation
    const clampedDt = Math.max(0.001, Math.min(0.05, dt));
    this.renderTick += (clampedDt / 0.050) * this.playbackRate;
    this.renderTime = this.renderTick * 50.0;

    const interpolateEntity = (st) => {
      const buf = st.buffer;
      if (!buf || buf.length === 0) return;

      if (buf.length >= 2) {
        let idx = -1;
        for (let i = 0; i < buf.length - 1; i++) {
          if (buf[i].tick <= this.renderTick && this.renderTick <= buf[i + 1].tick) {
            idx = i;
            break;
          }
        }

        if (idx !== -1) {
          const s1 = buf[idx];
          const s2 = buf[idx + 1];
          const span = Math.max(1, s2.tick - s1.tick);
          const t = Math.max(0.0, Math.min(1.0, (this.renderTick - s1.tick) / span));

          // Catmull-Rom cubic spline interpolation for C1 position & velocity continuity.
          // Guarantees cars trace continuous racetrack curves instead of discrete chords.
          const p0 = idx > 0 ? buf[idx - 1] : { x: 2 * s1.x - s2.x, y: 2 * s1.y - s2.y };
          const p1 = s1;
          const p2 = s2;
          const p3 = idx + 2 < buf.length ? buf[idx + 2] : { x: 2 * s2.x - s1.x, y: 2 * s2.y - s1.y };

          const t2 = t * t;
          const t3 = t2 * t;

          st.cx = 0.5 * (
            (2 * p1.x) +
            (-p0.x + p2.x) * t +
            (2 * p0.x - 5 * p1.x + 4 * p2.x - p3.x) * t2 +
            (-p0.x + 3 * p1.x - 3 * p2.x + p3.x) * t3
          );

          st.cy = 0.5 * (
            (2 * p1.y) +
            (-p0.y + p2.y) * t +
            (2 * p0.y - 5 * p1.y + 4 * p2.y - p3.y) * t2 +
            (-p0.y + 3 * p1.y - 3 * p2.y + p3.y) * t3
          );

          // Smoothstep angular lerp for C1 rotational continuity
          const smoothT = t * t * (3 - 2 * t);
          st.ch = lerpAngle(s1.h, s2.h, smoothT);
        } else if (this.renderTick < buf[0].tick) {
          st.cx = buf[0].x;
          st.cy = buf[0].y;
          st.ch = buf[0].h;
        } else {
          // If network tick arrived late, glide forward with last observed velocity
          const last = buf[buf.length - 1];
          const prev = buf[buf.length - 2];
          const dtTicks = Math.max(1, last.tick - prev.tick);
          const vx = (last.x - prev.x) / dtTicks;
          const vy = (last.y - prev.y) / dtTicks;
          const extraTicks = Math.min(3.0, this.renderTick - last.tick);
          st.cx = last.x + vx * extraTicks;
          st.cy = last.y + vy * extraTicks;
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
    let currentTargetKey = "full";

    if (this.cameraMode === "manual") {
      // Manual pan/zoom active - keep camera steady
      return;
    }

    if (this.tick && this.carInterp.size > 0 && this.cameraMode !== "full") {
      let targetCarSt = null;
      if (this.cameraMode === "leader") {
        const ldr = this.tick.cars[0];
        targetCarSt = ldr && this.carInterp.get(ldr.id);
        if (targetCarSt) {
          isTrackingCar = true;
          targetX = targetCarSt.cx;
          targetY = targetCarSt.cy;
          targetZoom = 2.45 * zoomRatio;
          currentTargetKey = "leader:" + ldr.id;
        }
      } else if (this.cameraMode === "selected" && this.selectedDriverId) {
        targetCarSt = this.carInterp.get(this.selectedDriverId);
        if (targetCarSt) {
          isTrackingCar = true;
          targetX = targetCarSt.cx;
          targetY = targetCarSt.cy;
          targetZoom = 2.75 * zoomRatio;
          currentTargetKey = "selected:" + this.selectedDriverId;
        }
      } else if (this.cameraMode === "team") {
        const myCars = this.tick.cars.filter((c) => c.tid === this.tick.player_team_id && !c.dnf);
        if (myCars.length > 0) {
          targetCarSt = this.carInterp.get(myCars[0].id);
          if (targetCarSt) {
            isTrackingCar = true;
            targetX = targetCarSt.cx;
            targetY = targetCarSt.cy;
            targetZoom = 2.35 * zoomRatio;
            currentTargetKey = "team:" + myCars[0].id;
          }
        }
      } else if (this.cameraMode === "battle") {
        const now = performance.now();
        if (
          !this._battleTargetA ||
          now > (this._battleLockUntil || 0) ||
          !this.tick.cars.some((c) => c.id === this._battleTargetA && !c.dnf)
        ) {
          const battling =
            this.tick.cars.find((c) => c.battle && c.ovt && !c.dnf) ||
            this.tick.cars.find((c) => c.battle && !c.dnf) ||
            this.tick.cars[0];
          if (battling) {
            this._battleTargetA = battling.id;
            const rival = this.tick.cars.find((c) => c.code === battling.battle && !c.dnf);
            this._battleTargetB = rival ? rival.id : null;
            this._battleLockUntil = now + 6500;
          }
        }

        const stA = this._battleTargetA && this.carInterp.get(this._battleTargetA);
        const stB = this._battleTargetB && this.carInterp.get(this._battleTargetB);
        if (stA && stB) {
          isTrackingCar = true;
          targetX = (stA.cx + stB.cx) * 0.5;
          targetY = (stA.cy + stB.cy) * 0.5;
          const battleDist = Math.hypot(stA.cx - stB.cx, stA.cy - stB.cy);
          targetZoom = Math.max(1.6, Math.min(2.7, 2.45 * zoomRatio * (65 / Math.max(45, battleDist))));
          currentTargetKey = "battle:" + this._battleTargetA + "-" + this._battleTargetB;
        } else if (stA) {
          isTrackingCar = true;
          targetX = stA.cx;
          targetY = stA.cy;
          targetZoom = 2.45 * zoomRatio;
          currentTargetKey = "battle:" + this._battleTargetA;
        }
      }
    }

    // Detect target entity or mode switch
    if (this._activeTargetKey !== currentTargetKey) {
      this._activeTargetKey = currentTargetKey;
      this._camLocked = false;
      this._camTransitElapsed = 0.0;
    }

    const dist = Math.hypot(targetX - this.camX, targetY - this.camY);

    if (dist > 350.0) {
      // Discontinuity / session teleport: immediate snap
      this.camX = targetX;
      this.camY = targetY;
      this._camLocked = true;
    } else if (!this._camLocked) {
      // Smooth, responsive cinematic pan towards the car
      this._camTransitElapsed = (this._camTransitElapsed || 0) + dt;
      const kPan = 1.0 - Math.exp(-dt * 9.0);
      this.camX += (targetX - this.camX) * kPan;
      this.camY += (targetY - this.camY) * kPan;

      // Lock once within 0.8 meters or after 0.40s transit
      if (dist < 0.8 || this._camTransitElapsed > 0.40) {
        this.camX = targetX;
        this.camY = targetY;
        this._camLocked = true;
      }
    } else {
      // Direct rock-solid tracking of Catmull-Rom smooth position:
      // Zero lag, zero wobble, zero camera oscillation.
      // The car is locked directly to screen center, and the track scrolls
      // past with fluid sub-pixel continuity.
      this.camX = targetX;
      this.camY = targetY;
    }

    // Responsive camera zoom
    const zoomRate = 8.0;
    const kZoom = 1.0 - Math.exp(-dt * zoomRate);
    this.camZoom += (targetZoom - this.camZoom) * kZoom;
    if (Math.abs(targetZoom - this.camZoom) < 0.002) {
      this.camZoom = targetZoom;
    }
  }

  _render(now, dt) {
    this._updateInterpolation(now, dt);
    this._updateCamera(dt);

    const ctx = this.ctx;
    ctx.save();
    ctx.scale(this.dpr, this.dpr);
    ctx.clearRect(0, 0, this.width, this.height);

    // Subtle dark broadcast carbon telemetry crosshair grid
    ctx.strokeStyle = "rgba(255, 255, 255, 0.025)";
    ctx.lineWidth = 1;
    for (let x = 0; x < this.width; x += 48) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, this.height);
      ctx.stroke();
    }
    for (let y = 0; y < this.height; y += 48) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(this.width, y);
      ctx.stroke();
    }

    if (!this.track) {
      ctx.restore();
      return;
    }

    const b = this.track.bounds;
    const baseScale = b
      ? Math.min((this.width-54)/(b.max_x-b.min_x), (this.height-50)/(b.max_y-b.min_y))
      : Math.min((this.width-54)/880, (this.height-50)/545);
    const scale = baseScale * this.camZoom;
    const ox = this.width * 0.5 - this.camX * scale;
    const oy = this.height * 0.51 - this.camY * scale;
    this._viewTransform = { scale, ox, oy };

    ctx.translate(ox, oy);
    ctx.scale(scale, scale);

    this._drawEnvironment(ctx, now);
    this._drawTrack(ctx, now);
    this._drawParticles(ctx);
    this._drawCars(ctx, now);
    if (this.tick && this.tick.wetness >= 15) {
      this._drawRain(ctx, dt, this.tick.wetness);
    }

    ctx.restore();
  }

  _drawEnvironment(ctx, now) {
    this.scenery.draw(ctx, this.track, this._viewTransform, this.width, this.height, this.dpr);
  }

  _drawTrack(ctx, now) {
    const sts = this.track.stations;
    const n = sts.length;
    const wPx = this.track.track_width_px || 24.5;

    // Reference pit route, including shortcuts, rather than an offset lap.
    const ppts = this.track.pit_points || [];
    const pitWidth = this.track.pit_width_px || 14;
    if (ppts.length > 1) {
      ctx.beginPath();
      ctx.moveTo(...ppts[0]);
      for (const pt of ppts.slice(1)) ctx.lineTo(...pt);
      ctx.lineCap = "round";
      ctx.lineJoin = "round";
      ctx.strokeStyle = "rgba(255,255,255,.45)";
      ctx.lineWidth = pitWidth + 1.6;
      ctx.stroke();
      ctx.strokeStyle = "#161b26";
      ctx.lineWidth = pitWidth;
      ctx.stroke();
      for (const u of [this.track.pit_speed_entry_u ?? .1, this.track.pit_speed_exit_u ?? .9]) {
        const i = Math.min(ppts.length-2, Math.floor(u*(ppts.length-1)));
        const a=ppts[i],b=ppts[i+1],len=Math.hypot(b[0]-a[0],b[1]-a[1])||1;
        const nx=-(b[1]-a[1])/len,ny=(b[0]-a[0])/len;
        ctx.beginPath();
        ctx.moveTo(a[0]-nx*pitWidth*.48,a[1]-ny*pitWidth*.48);
        ctx.lineTo(a[0]+nx*pitWidth*.48,a[1]+ny*pitWidth*.48);
        ctx.strokeStyle="#ffd700";ctx.lineWidth=1.5;ctx.stroke();
      }
      // Team Pit Stall locations with Constructor Logos & Gantry Graphics
      const side = this.track.pit_side || 1;
      const geom = this.track.car_geometry || { length_m: 5.4, width_m: 2.0, front_axle_m: 1.8, world_units_per_m: 3.5 };
      const ppm = geom.world_units_per_m || 3.5;
      const stallLen = (geom.length_m + 0.9) * ppm;
      const stallWid = (geom.width_m + 0.45) * ppm;

      for (const g of this.track.pit_garages || []) {
        const teamId = GARAGE_TEAM_IDS[g.index] || "williams";
        const teamCode = GARAGE_TEAM_CODES[g.index] || "F1";
        const teamColor = TEAM_LIVERY[teamId]?.stripe || "#00d2be";

        const nx = -g.ty * side, ny = g.tx * side;
        const gx = g.x + nx * 8.6, gy = g.y + ny * 8.6;
        const angle = Math.atan2(g.ty, g.tx);

        ctx.save();
        ctx.translate(gx, gy);
        ctx.rotate(angle);

        // 1. Pit Box Floor Surface with Subtle Team Livery Tint
        ctx.fillStyle = teamColor + "24";
        ctx.fillRect(-stallLen * 0.5, -stallWid * 0.5, stallLen, stallWid);

        // 2. Clean Box Outline in Team Livery Color
        ctx.strokeStyle = teamColor;
        ctx.lineWidth = 0.9;
        ctx.strokeRect(-stallLen * 0.5, -stallWid * 0.5, stallLen, stallWid);

        // 3. Official Yellow FIA Wheel Stop Gantry Line
        ctx.strokeStyle = "#ffd700";
        ctx.lineWidth = 1.1;
        ctx.beginPath();
        ctx.moveTo(stallLen * 0.32, -stallWid * 0.5);
        ctx.lineTo(stallLen * 0.32, stallWid * 0.5);
        ctx.stroke();

        // 4. Circular Team Emblem Disc & Official Constructor Logo
        const badgeR = Math.min(stallLen * 0.28, stallWid * 0.44);
        ctx.beginPath();
        ctx.arc(0, 0, badgeR, 0, Math.PI * 2);
        ctx.fillStyle = "#0c0d14";
        ctx.fill();
        ctx.strokeStyle = teamColor;
        ctx.lineWidth = 0.8;
        ctx.stroke();

        const img = getTeamLogoImage(teamId);
        if (img && img.complete && img.naturalWidth > 0) {
          ctx.drawImage(img, -badgeR * 0.82, -badgeR * 0.82, badgeR * 1.64, badgeR * 1.64);
        } else {
          ctx.fillStyle = teamColor;
          ctx.font = `900 ${badgeR * 0.9}px 'Titillium Web', Inter, sans-serif`;
          ctx.textAlign = "center";
          ctx.textBaseline = "middle";
          ctx.fillText(teamCode, 0, 0);
        }

        // 5. Pit Wall / Garage Gantry Nameplate Tag on Apron
        ctx.fillStyle = "rgba(12, 14, 20, 0.88)";
        const tagW = Math.max(stallLen * 0.38, 14);
        const tagH = Math.max(stallWid * 0.38, 5.5);
        const tagY = -stallWid * 0.5 - tagH * 0.65;
        ctx.fillRect(-tagW * 0.5, tagY, tagW, tagH);
        ctx.strokeStyle = teamColor;
        ctx.lineWidth = 0.6;
        ctx.strokeRect(-tagW * 0.5, tagY, tagW, tagH);

        ctx.fillStyle = "#ffffff";
        ctx.font = `800 ${tagH * 0.72}px 'Titillium Web', Inter, sans-serif`;
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(teamCode, 0, tagY + tagH * 0.5);

        ctx.restore();
      }
    }

    // 2. Track Outer Verge / Barrier Shadow (scaled to real circuit width)
    this._traceRoadRibbon(ctx, sts, 7.6);
    ctx.fillStyle = "#060609";
    ctx.lineJoin = "round";
    ctx.fill();

    // 3. FIA Red & White Corner Kerbs
    for (let i = 0; i < n; i++) {
      if (sts[i].curv > 0.012) {
        const s0 = sts[i];
        const s1 = sts[(i + 1) % n];
        ctx.beginPath();
        ctx.moveTo(s0.x, s0.y);
        ctx.lineTo(s1.x, s1.y);
        ctx.strokeStyle = i % 2 === 0 ? "#e10600" : "#e8ecf2";
        ctx.lineWidth = (s0.width_px || wPx) + 4.4;
        ctx.stroke();
      }
    }

    // 4. White FIA Track Edge Lines + Wide Dark Racing Asphalt
    this._traceRoadRibbon(ctx, sts, .96);
    ctx.fillStyle = "rgba(255, 255, 255, 0.46)";
    ctx.fill();

    const wet = this.tick ? this.tick.wetness : 0;
    this._traceRoadRibbon(ctx, sts);
    ctx.fillStyle = wet > 20 ? "#1b2230" : "#22232c";
    ctx.fill();

    // Dual-tier rubbered geometric racing groove (sweeps from outside entry to apex kerb to exit kerb)
    if (this.track.racing_line_points && this.track.racing_line_points.length > 2) {
      const rpts = this.track.racing_line_points;
      ctx.save();
      ctx.lineJoin = "round";
      ctx.lineCap = "round";

      // 1. Soft wide rubbered track foundation
      ctx.beginPath();
      ctx.moveTo(rpts[0][0], rpts[0][1]);
      for (let i = 1; i < rpts.length; i++) {
        ctx.lineTo(rpts[i][0], rpts[i][1]);
      }
      ctx.closePath();
      ctx.strokeStyle = wet > 25 ? "rgba(8, 10, 14, 0.18)" : "rgba(10, 10, 14, 0.32)";
      ctx.lineWidth = Math.max(6.5, wPx * 0.38);
      ctx.stroke();

      // 2. High-grip dark central rubber groove
      ctx.beginPath();
      ctx.moveTo(rpts[0][0], rpts[0][1]);
      for (let i = 1; i < rpts.length; i++) {
        ctx.lineTo(rpts[i][0], rpts[i][1]);
      }
      ctx.closePath();
      ctx.strokeStyle = wet > 25 ? "rgba(6, 8, 12, 0.32)" : "rgba(6, 6, 10, 0.58)";
      ctx.lineWidth = Math.max(3.6, wPx * 0.20);
      ctx.stroke();
      ctx.restore();
    } else {
      this._traceClosedSpline(ctx, sts);
      ctx.strokeStyle = "rgba(10, 10, 14, 0.32)";
      ctx.lineWidth = Math.max(6.0, wPx * 0.34);
      ctx.stroke();
    }

    // 5. Suzuka Figure-8 Bridge Overpass Deck (if circuit has crossover)
    if (this.track.has_overpass && this.track.overpass_station != null) {
      const ov = this.track.overpass_station;
      const span = Math.max(2, Math.ceil(12 / (this.track.length_m / n)));
      const bridgeWidth = sts[ov].width_px || wPx;
      ctx.save();
      ctx.beginPath();
      for (let k = -span; k <= span; k++) {
        const pt = sts[(ov + k + n) % n];
        if (k === -span) ctx.moveTo(pt.x, pt.y);
        else ctx.lineTo(pt.x, pt.y);
      }
      ctx.shadowColor = "rgba(0, 0, 0, 0.92)";
      ctx.shadowBlur = 9;
      ctx.strokeStyle = "#4b5563";
      ctx.lineWidth = bridgeWidth + 4.2;
      ctx.lineCap = "butt";
      ctx.stroke();

      ctx.shadowBlur = 0;
      ctx.strokeStyle = wet > 20 ? "#1b2230" : "#242630";
      ctx.lineWidth = bridgeWidth;
      ctx.stroke();
      ctx.restore();
    }

    // 6. 2026 Active Aero Straight-Mode Zones (Trackside Indicator Line)
    ctx.lineWidth = 1.6;
    ctx.strokeStyle = "rgba(0, 210, 190, 0.68)";
    for (let i = 0; i < n; i++) {
      if (sts[i].straight_mode) {
        const a = sts[i];
        const b = sts[(i + 1) % n];
        const aeroOff = (a.width_px || wPx) * .5 + 2.6;
        ctx.beginPath();
        ctx.moveTo(a.x + a.nx * aeroOff, a.y + a.ny * aeroOff);
        ctx.lineTo(b.x + b.nx * aeroOff, b.y + b.ny * aeroOff);
        ctx.stroke();
      }
    }

    // 7. Yellow Flag Sector Overlay
    if (this.tick && this.tick.flag === "YELLOW" && this.tick.yellow_sector) {
      const pulse = 0.4 + 0.3 * Math.sin(now * 0.01);
      ctx.strokeStyle = `rgba(255, 208, 0, ${pulse})`;
      ctx.lineWidth = wPx + 4.0;
      for (let i = 0; i < n; i++) {
        if (sts[i].sector === this.tick.yellow_sector) {
          const a = sts[i];
          const b = sts[(i + 1) % n];
          ctx.beginPath();
          ctx.moveTo(a.x, a.y);
          ctx.lineTo(b.x, b.y);
          ctx.stroke();
        }
      }
    }

    // 8. Multi-DRS Zones & Detection Gates
    const drsZones = this.track.drs_zones || [
      {
        id: 1,
        detection_station: this.track.detection_station || Math.floor(n * 0.81),
        activation_station: Math.floor(n * 0.85),
      },
    ];

    for (const z of drsZones) {
      const detStation = z.detection_station != null ? z.detection_station : Math.floor(n * 0.81);
      const det = sts[detStation];
      const detHalf = (det?.width_px || wPx) * 0.5 + 2.2;
      if (det) {
        ctx.save();
        ctx.strokeStyle = "#00d26a";
        ctx.lineWidth = 1.8;
        ctx.beginPath();
        ctx.moveTo(det.x - det.nx * detHalf, det.y - det.ny * detHalf);
        ctx.lineTo(det.x + det.nx * detHalf, det.y + det.ny * detHalf);
        ctx.stroke();

        ctx.fillStyle = "#00d26a";
        ctx.font = "800 7.5px 'Titillium Web', Inter, sans-serif";
        const detLabel = drsZones.length > 1 ? `DET ${z.id}` : "DET";
        ctx.fillText(detLabel, det.x + det.nx * (detHalf + 4.5) - 9, det.y + det.ny * (detHalf + 4.5) + 2.5);
        ctx.restore();
      }

      if (z.activation_station != null) {
        const act = sts[z.activation_station];
        if (act) {
          ctx.save();
          ctx.strokeStyle = "#10b981";
          ctx.lineWidth = 1.6;
          ctx.setLineDash([3, 2]);
          ctx.beginPath();
          ctx.moveTo(act.x - act.nx * detHalf, act.y - act.ny * detHalf);
          ctx.lineTo(act.x + act.nx * detHalf, act.y + act.ny * detHalf);
          ctx.stroke();

          const isV8 = this.tick && this.tick.regulations && this.tick.regulations.era_id === "V8_DRS";
          ctx.fillStyle = "#10b981";
          ctx.font = "800 7.0px 'Titillium Web', Inter, sans-serif";
          ctx.fillText(isV8 ? "DRS" : "OVT", act.x - act.nx * (detHalf + 4.5) - 7, act.y - act.ny * (detHalf + 4.5) + 2.5);
          ctx.restore();
        }
      }
    }

    // 8b. 22 FIA Staggered Starting Grid Boxes (P1 through P22)
    if (this.track.grid_boxes && this.track.grid_boxes.length > 0) {
      const geom=this.track.car_geometry,ppm=geom.world_units_per_m;
      const boxLen = (geom.length_m+.6)*ppm;
      const boxWid = (geom.width_m+.4)*ppm;
      ctx.save();
      for (const gb of this.track.grid_boxes) {
        ctx.save();
        ctx.translate(gb.x, gb.y);
        ctx.rotate(gb.heading);

        // White FIA slot outline rectangle
        ctx.strokeStyle = "rgba(255, 255, 255, 0.50)";
        ctx.lineWidth = 0.9;
        ctx.strokeRect(-boxLen * 0.5, -boxWid * 0.5, boxLen, boxWid);

        // Bright yellow front-wheel stop marker line across the front of the box
        ctx.strokeStyle = "#ffd700";
        ctx.lineWidth = .8;
        ctx.beginPath();
        ctx.moveTo(geom.front_axle_m*ppm, -boxWid * 0.5);
        ctx.lineTo(geom.front_axle_m*ppm, boxWid * 0.5);
        ctx.stroke();

        // Position number label beside the grid box
        ctx.fillStyle = "rgba(255, 255, 255, 0.45)";
        ctx.font = "700 6px 'Titillium Web', Inter, sans-serif";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(`${gb.pos}`, -boxLen * 0.5 - 4.5, 0);

        ctx.restore();
      }
      ctx.restore();
    }

    // 9. Start / Finish Line & Gantry (spanning full wide circuit width)
    const sf = sts[0];
    const finishWidth = sf.width_px || wPx;
    const halfRows = Math.max(3, Math.floor(finishWidth / 5.2));
    ctx.save();
    ctx.translate(sf.x, sf.y);
    ctx.rotate(Math.atan2(sf.ty, sf.tx));
    for (let r = -halfRows; r < halfRows; r++) {
      for (let c = 0; c < 2; c++) {
        ctx.fillStyle = (r + c) % 2 === 0 ? "#ffffff" : "#0b0b0f";
        ctx.fillRect(c * 2.5 - 2.5, r * 2.5, 2.5, 2.5);
      }
    }
    ctx.restore();

    // The launch line may be ahead of the circuit timing/finish line.
    const start = this.track.start_line || {x:sf.x,y:sf.y,heading:Math.atan2(sf.ty,sf.tx)};
    const startWidth = start.width_px || wPx;
    ctx.save();
    ctx.translate(start.x,start.y);
    ctx.rotate(start.heading);
    ctx.fillStyle = "#ffffff";
    ctx.fillRect(-.24,-startWidth*.5,.48,startWidth);
    ctx.restore();
    const gridLabelScale = Math.max(1,1/this._viewTransform.scale);
    const snx=-Math.sin(start.heading),sny=Math.cos(start.heading);
    ctx.font=`700 ${7*gridLabelScale}px 'Titillium Web', Inter, sans-serif`;
    ctx.textAlign="center";ctx.textBaseline="middle";ctx.fillStyle="#ffffff";
    ctx.fillText("START",start.x+snx*(startWidth*.5+12*gridLabelScale),start.y+sny*(startWidth*.5+12*gridLabelScale));
    if (Math.abs(this.track.start_line_s||0)>1) {
      ctx.fillStyle="rgba(255,255,255,.55)";
      ctx.fillText("FINISH",sf.x+sf.nx*(finishWidth*.5+12*gridLabelScale),sf.y+sf.ny*(finishWidth*.5+12*gridLabelScale));
    }

    // 10. Official F1 Broadcast Style Corner Numbers
    const annotationScale = Math.max(1, 1 / this._viewTransform.scale);
    ctx.font = `700 ${7.5 * annotationScale}px 'Titillium Web', Inter, sans-serif`;
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    for (const c of this.track.corners) {
      const st = sts[c.station];
      const cornerOff = (st.width_px || wPx) * .5 + 9.2 * annotationScale;
      const bx = c.x - st.nx * cornerOff;
      const by = c.y - st.ny * cornerOff;
      ctx.fillStyle = "#15151e";
      ctx.beginPath();
      ctx.arc(bx, by, 6.2 * annotationScale, 0, Math.PI * 2);
      ctx.fill();
      ctx.strokeStyle = "#3b3b4f";
      ctx.lineWidth = 0.9;
      ctx.stroke();
      ctx.fillStyle = "#d4d4e0";
      ctx.fillText(`${c.number}`, bx, by + 0.4);
    }
  }

  _traceClosedSpline(ctx, sts) {
    ctx.beginPath();
    ctx.moveTo(sts[0].x, sts[0].y);
    for (let i = 1; i < sts.length; i++) {
      ctx.lineTo(sts[i].x, sts[i].y);
    }
    ctx.closePath();
  }

  _traceRoadRibbon(ctx, sts, extraWidth = 0) {
    // One continuous polygon: the same per-station metre widths as physics.
    // Separate strokes would leave gaps or inflate the narrow corners.
    ctx.beginPath();
    for (const [side, reverse] of [[1, false], [-1, true]]) {
      for (let j = 0; j < sts.length; j++) {
        const i = reverse ? sts.length - 1 - j : j;
        const p = sts[i], h = ((p.width_px || this.track.track_width_px) + extraWidth) * .5;
        const x = p.x + side * p.nx * h, y = p.y + side * p.ny * h;
        if (side === 1 && j === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
      }
      // Explicitly close each edge loop; even-odd fill preserves the infield.
      const p = sts[reverse ? sts.length - 1 : 0];
      const h = ((p.width_px || this.track.track_width_px) + extraWidth) * .5;
      ctx.lineTo(p.x + side * p.nx * h, p.y + side * p.ny * h);
    }
    ctx.closePath();
  }

  _drawParticles(ctx) {
    for (const p of this.particles) {
      const alpha = Math.max(0, p.life / p.maxLife);
      ctx.save();
      ctx.globalAlpha = alpha;
      ctx.fillStyle = p.color;
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.size * (1.2 - alpha * 0.4), 0, Math.PI * 2);
      ctx.fill();
      ctx.restore();
    }
  }

  _drawCars(ctx, now) {
    if (!this.tick) return;

    if (this.scInterp) {
      this._drawSafetyCar(ctx, this.scInterp, now);
    }

    // Pass 1: Draw all visible 2026 F1 chassis (back-to-front so leaders sit cleanly on top of wakes)
    const ordered = [...this.tick.cars].reverse();
    for (const c of ordered) {
      if (!c.vis || c.pit_tunnel) continue;
      const st = this.carInterp.get(c.id);
      if (!st) continue;
      this._drawSingleCar(ctx, st.cx, st.cy, st.ch, c, now);
      if (this._viewTransform.scale < .45) {
        ctx.beginPath();ctx.arc(st.cx,st.cy,2.1/this._viewTransform.scale,0,Math.PI*2);
        ctx.fillStyle=c.tcol;ctx.fill();
      }
    }

    // Pass 2: Draw collision-free F1 TV broadcast driver tags above/around cars
    this._drawDriverTags(ctx);
  }

  _drawSafetyCar(ctx, sc, now) {
    ctx.save();
    ctx.translate(sc.cx, sc.cy);
    ctx.rotate(sc.ch);
    const geom=this.track.car_geometry,ppm=geom.world_units_per_m;
    ctx.scale(geom.safety_car_length_m*ppm/14.4,geom.safety_car_width_m*ppm/7.6);

    // Mercedes/Aston Safety Car GT silhouette
    ctx.fillStyle = "#0b0d12";
    ctx.beginPath();
    ctx.roundRect(-7.2, -3.8, 14.4, 7.6, 2);
    ctx.fill();

    ctx.fillStyle = "#dce2ec";
    ctx.beginPath();
    ctx.roundRect(-6.6, -3.2, 13.2, 6.4, 1.8);
    ctx.fill();

    // Windshield & rear glass
    ctx.fillStyle = "#111622";
    ctx.fillRect(-3.0, -2.5, 6.2, 5.0);

    // Amber FIA Safety Car roof light bar
    const flash = Math.floor(now / 110) % 2 === 0;
    ctx.fillStyle = flash ? "#ffd000" : "#ff6a00";
    ctx.fillRect(-0.9, -2.9, 1.8, 5.8);
    ctx.restore();

    ctx.save();
    ctx.font = "800 7.5px 'Titillium Web', Inter, sans-serif";
    ctx.fillStyle = "#ffd000";
    ctx.fillText("SC", sc.cx - 5, sc.cy - 8.5);
    ctx.restore();
  }

  _drawSingleCar(ctx, x, y, heading, c, now) {
    const isMyTeam = this.tick && c.tid === this.tick.player_team_id;
    const isSelected = c.id === this.selectedDriverId;
    const liv = TEAM_LIVERY[c.tid] || { body: c.tcol, pod: c.tcol, noseTip: c.tcol, stripe: c.scol };
    const viewTransform = ctx.getTransform();
    const pixelScale = Math.max(Math.hypot(viewTransform.a,viewTransform.b),Math.hypot(viewTransform.c,viewTransform.d));
    const surfaces = getCarSurfaces(liv, c.tid, c.num, c.dnf, c.comp, c.wear, pixelScale);
    const carbonPaint = getCarbonPaint(ctx,surfaces.carbon);

    ctx.save();
    if (c.elim) {
      ctx.globalAlpha = 0.52;
    }
    ctx.translate(x, y);
    ctx.rotate(heading);

    // Artwork envelope: rear light -8.35 to nose 9.1, endplates +/-4.2.
    // Chassis, axles and tyres use the same metres as collision and track widths.
    const geom=this.track.car_geometry,ppm=geom.world_units_per_m;
    const scaleX=geom.length_m*ppm/17.45,scaleY=geom.width_m*ppm/8.4;
    const artworkCenter=.375;
    ctx.scale(scaleX,scaleY);
    ctx.translate(-artworkCenter,0);
    const frontAxle=geom.front_axle_m*ppm/scaleX+artworkCenter;
    const rearAxle=geom.rear_axle_m*ppm/scaleX+artworkCenter;
    const frontHub=geom.front_track_m*ppm/(2*scaleY);
    const rearHub=geom.rear_track_m*ppm/(2*scaleY);

    // Dynamic Chassis Roll, Lateral Weight Transfer & Longitudinal Pitch Ground Shadow
    const gLat = c.g_lat || 0.0;
    const rollOffset = Math.max(-1.8, Math.min(1.8, gLat * 0.45));
    const pitchShift = c.braking ? 0.75 : (c.ovt || c.boost ? -0.55 : 0.0);
    const pitchScale = c.braking ? 0.94 : (c.ovt || c.boost ? 1.05 : 1.0);
    ctx.fillStyle = "rgba(0, 0, 0, 0.42)";
    ctx.beginPath();
    ctx.ellipse(0.2 + pitchShift, -rollOffset * 0.75, 8.8 * pitchScale, 4.4 + Math.abs(rollOffset) * 0.25, 0, 0, Math.PI * 2);
    ctx.fill();

    // 1. Dynamic Overtake Mode & Slipstream Wake Vortices
    if ((c.ovt || c.boost || c.man === "SLIPSTREAM") && !c.dnf) {
      const isOvt = c.ovt || c.man === "SLIPSTREAM";
      const colA = isOvt ? "rgba(0, 230, 118, 0.45)" : "rgba(0, 210, 190, 0.40)";
      const colB = isOvt ? "rgba(0, 230, 118, 0)" : "rgba(0, 210, 190, 0)";
      const grad = ctx.createLinearGradient(4, 0, -18, 0);
      grad.addColorStop(0, colA);
      grad.addColorStop(1, colB);
      ctx.fillStyle = grad;
      ctx.beginPath();
      ctx.ellipse(-5.5, 0, 14, 5.2, 0, 0, Math.PI * 2);
      ctx.fill();

      // Twin trailing aerodynamic wingtip vortex wisps
      if (c.kph > 180) {
        ctx.strokeStyle = "rgba(255, 255, 255, 0.25)";
        ctx.lineWidth = 0.55;
        ctx.beginPath();
        ctx.moveTo(-7.8, -3.2);
        ctx.lineTo(-15.5 - (c.kph * 0.03), -3.4);
        ctx.moveTo(-7.8, 3.2);
        ctx.lineTo(-15.5 - (c.kph * 0.03), 3.4);
        ctx.stroke();
      }
    }

    // Selected / Player Team Ground Reticle
    if (isSelected) {
      ctx.strokeStyle = "#ffffff";
      ctx.lineWidth = 0.9;
      ctx.beginPath();
      ctx.ellipse(0, 0, 10.2, 5.2, 0, 0, Math.PI * 2);
      ctx.stroke();
    } else if (isMyTeam && !c.dnf) {
      ctx.strokeStyle = "rgba(255, 255, 255, 0.38)";
      ctx.lineWidth = 0.7;
      ctx.beginPath();
      ctx.ellipse(0, 0, 9.8, 4.9, 0, 0, Math.PI * 2);
      ctx.stroke();
    }

    // 2. Woven Carbon Underfloor, Plank & Diffuser Edge Wings
    ctx.drawImage(surfaces.floor, -8.5, -4.2, 18, 8.4);

    // 3. Carbon Double-Wishbone Suspension Arms (Front & Rear)
    ctx.strokeStyle = "#181a22";
    ctx.lineWidth = 0.85;
    ctx.beginPath();
    // Front wishbones
    ctx.moveTo(5.4, -1.0); ctx.lineTo(frontAxle+.1, -frontHub);
    ctx.moveTo(3.4, -1.2); ctx.lineTo(frontAxle-.1, -frontHub);
    ctx.moveTo(5.4, 1.0);  ctx.lineTo(frontAxle+.1, frontHub);
    ctx.moveTo(3.4, 1.2);  ctx.lineTo(frontAxle-.1, frontHub);
    // Rear wishbones
    ctx.moveTo(-4.2, -1.2); ctx.lineTo(rearAxle, -rearHub);
    ctx.moveTo(-6.0, -1.0); ctx.lineTo(rearAxle, -rearHub);
    ctx.moveTo(-4.2, 1.2);  ctx.lineTo(rearAxle, rearHub);
    ctx.moveTo(-6.0, 1.0);  ctx.lineTo(rearAxle, rearHub);
    ctx.stroke();

    // 4. Four Sculpted Pirelli F1 Wheels + Steerable Front Hubs + Sidewall Rings
    const tyreCol = TIRE_COLORS[c.comp] || "#ffffff";
    const wheelSpecs = [
      [frontAxle,-frontHub,geom.front_tyre_diameter_m*ppm,geom.front_tyre_width_m*ppm,true],
      [frontAxle, frontHub,geom.front_tyre_diameter_m*ppm,geom.front_tyre_width_m*ppm,true],
      [rearAxle,-rearHub,geom.rear_tyre_diameter_m*ppm,geom.rear_tyre_width_m*ppm,false],
      [rearAxle, rearHub,geom.rear_tyre_diameter_m*ppm,geom.rear_tyre_width_m*ppm,false],
    ];
    const steerRad = c.steer || 0.0;
    for (const [wx, wy, ww, wh, isFront] of wheelSpecs) {
      ctx.save();
      ctx.translate(wx,wy);
      // Undo the artwork stretch so tyre size and steering stay physical.
      ctx.scale(1/scaleX,1/scaleY);
      if (isFront && Math.abs(steerRad) > 0.001) {
        ctx.rotate(steerRad);
      }
      ctx.fillStyle = "#090a0d";
      ctx.beginPath();
      ctx.roundRect(-ww * 0.5, -wh * 0.5, ww, wh, wh*.2);
      ctx.fill();
      // Texture the contact surface inside the original rounded tyre outline.
      ctx.drawImage(surfaces.rubber, -ww * .43, -wh * .33, ww * .86, wh * .66);

      // Pirelli compound sidewall stripe
      ctx.fillStyle = tyreCol;
      ctx.fillRect(-ww * 0.34, -wh * .35, ww * 0.68, wh*.12);
      ctx.fillRect(-ww * 0.34, wh * .23, ww * 0.68, wh*.12);
      ctx.restore();
    }

    // Glowing Carbon-Carbon Brake Discs under braking (radiant heat aura + molten orange + white-hot core)
    if (c.braking && !c.dnf) {
      const brakeRotors = [
        [frontAxle-.3, -2.3], [frontAxle-.3, 2.0],
        [rearAxle+.6, -2.4], [rearAxle+.6, 2.1],
      ];
      for (const [rx, ry] of brakeRotors) {
        ctx.fillStyle = "rgba(255, 60, 0, 0.40)";
        ctx.beginPath();
        ctx.arc(rx, ry, 1.4, 0, Math.PI * 2);
        ctx.fill();

        ctx.fillStyle = "#ff3d00";
        ctx.fillRect(rx - 0.7, ry - 0.35, 1.4, 0.7);

        ctx.fillStyle = "#fff2a8";
        ctx.fillRect(rx - 0.35, ry - 0.2, 0.7, 0.4);
      }
    }

    // Cached sculpted paint, pod graphics, radiator mouths and chassis decals.
    // This uses the original artwork bounds; physical dimensions stay untouched.
    ctx.drawImage(surfaces.body, -8.5, -4.2, 18, 8.4);

    // Stamp miniature Team Logo on the Nosecone when zoomed in
    const logoImg = getTeamLogoImage(c.tid);
    if (logoImg && logoImg.complete && logoImg.naturalWidth > 0 && !c.dnf) {
      ctx.save();
      ctx.translate(4.4, 0);
      ctx.rotate(Math.PI * 0.5);
      ctx.drawImage(logoImg, -1.1, -1.1, 2.2, 2.2);
      ctx.restore();
    }

    // 7. 2026 Multi-Element Active Front Wing & Asymmetric Damage Model
    const dmgSide = c.dmg_side || "NONE";
    const hasLeftDmg = (dmgSide === "LEFT" || dmgSide === "BOTH") && c.dmg > 15;
    const hasRightDmg = (dmgSide === "RIGHT" || dmgSide === "BOTH") && c.dmg > 15;
    const lSpan = hasLeftDmg ? (c.dmg > 45 ? 1.85 : 2.55) : 3.95;
    const rSpan = hasRightDmg ? (c.dmg > 45 ? 1.85 : 2.55) : 3.95;

    ctx.fillStyle = c.dnf ? "#3f4452" : c.tcol;
    ctx.beginPath();
    ctx.moveTo(8.5, -0.8);
    if (hasLeftDmg) {
      // Jagged fractured carbon edge on damaged left side
      ctx.lineTo(7.6, -lSpan * 0.72);
      ctx.lineTo(7.3, -lSpan);
      ctx.lineTo(6.4, -lSpan * 0.9);
      ctx.lineTo(6.6, -lSpan * 0.5);
    } else {
      ctx.lineTo(7.5, -lSpan);
      ctx.lineTo(6.3, -lSpan);
    }
    ctx.lineTo(7.1, 0);
    if (hasRightDmg) {
      // Jagged fractured carbon edge on damaged right side
      ctx.lineTo(6.6, rSpan * 0.5);
      ctx.lineTo(6.4, rSpan * 0.9);
      ctx.lineTo(7.3, rSpan);
      ctx.lineTo(7.6, rSpan * 0.72);
    } else {
      ctx.lineTo(6.3, rSpan);
      ctx.lineTo(7.5, rSpan);
    }
    ctx.lineTo(8.5, 0.8);
    ctx.closePath();
    ctx.fill();

    // Secondary front wing flap (highlights in Straight Active Aero)
    const wingOpacity = ctx.globalAlpha;
    ctx.globalAlpha *= .65;
    ctx.fillStyle = carbonPaint;
    ctx.fill();
    ctx.globalAlpha = wingOpacity;
    ctx.strokeStyle = c.aero === "STRAIGHT" ? "#ffffff" : "#0b0d12";
    ctx.lineWidth = 0.45;
    ctx.beginPath();
    ctx.moveTo(7.2, -lSpan + 0.3);
    ctx.lineTo(7.9, 0);
    ctx.lineTo(7.2, rSpan - 0.3);
    ctx.stroke();

    // Front wing endplates (only drawn if intact) & fluttering composite shards if damaged
    ctx.fillStyle = liv.stripe;
    if (!hasLeftDmg) {
      ctx.fillRect(6.2, -lSpan - 0.25, 1.5, 0.4);
    } else {
      ctx.fillStyle = "#111216";
      const fl = Math.sin(now * 0.035 + c.num) * 0.25;
      ctx.fillRect(6.3, -lSpan - 0.15 + fl, 0.6, 0.3);
    }
    if (!hasRightDmg) {
      ctx.fillRect(6.2, rSpan - 0.15, 1.5, 0.4);
    } else {
      ctx.fillStyle = "#111216";
      const fl = Math.cos(now * 0.035 + c.num) * 0.25;
      ctx.fillRect(6.3, rSpan - 0.15 + fl, 0.6, 0.3);
    }

    // 8. Cockpit Opening, Airbox Intake, Driver Helmet & Titanium Y-Halo
    ctx.fillStyle = "#06070a";
    ctx.beginPath();
    ctx.ellipse(-0.3, 0, 2.05, 0.98, 0, 0, Math.PI * 2);
    ctx.fill();

    // Roll-hoop airbox intake behind helmet
    ctx.fillStyle = "#050608";
    ctx.fillRect(-2.4, -0.55, 0.85, 1.1);

    // Driver Helmet + Dark Visor
    ctx.fillStyle = c.helm;
    ctx.beginPath();
    ctx.arc(-0.35, 0, 0.88, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = "rgba(255,255,255,.32)";
    ctx.beginPath();
    ctx.ellipse(-.6,-.3,.37,.18,-.35,0,Math.PI*2);
    ctx.fill();
    ctx.fillStyle = "#111318";
    ctx.beginPath();
    ctx.arc(-0.05, 0, 0.55, -0.9, 0.9);
    ctx.fill();

    // 3-Point Titanium Halo Structure
    ctx.strokeStyle = "#2b303c";
    ctx.lineWidth = 0.55;
    ctx.beginPath();
    ctx.moveTo(-1.1, -0.88);
    ctx.quadraticCurveTo(0.85, -0.75, 1.55, 0);
    ctx.quadraticCurveTo(0.85, 0.75, -1.1, 0.88);
    ctx.moveTo(1.55, 0);
    ctx.lineTo(0.45, 0);
    ctx.stroke();
    ctx.strokeStyle = "rgba(193,204,215,.65)";
    ctx.lineWidth = .14;
    ctx.stroke();

    // 9. 2026 Multi-Element Active Rear Wing (Opens Slot Gap in Straight Mode!)
    ctx.fillStyle = "#0b0d13";
    ctx.fillRect(-8.0, -3.45, 1.85, 6.9); // Rear wing mainplane
    ctx.fillStyle = carbonPaint;
    ctx.fillRect(-8.0,-3.45,1.85,6.9);
    if ((c.aero === "STRAIGHT" || c.aero === "DRS" || c.ovt || c.drs) && !c.dnf) {
      // Open low-drag DRS slot gap profile revealing white leading edge & green DRS status LED
      ctx.fillStyle = "#f0f4f8";
      ctx.fillRect(-7.35, -3.2, 0.65, 6.4);
      ctx.fillStyle = (c.drs || c.ovt) ? "#00e676" : "#10b981";
      ctx.fillRect(-6.9, -2.8, 0.4, 5.6);
    } else {
      ctx.fillStyle = c.dnf ? "#3f4452" : c.tcol;
      ctx.fillRect(-7.55, -3.25, 1.05, 6.5);
    }
    // Rear wing endplates
    ctx.fillStyle = c.tcol;
    ctx.fillRect(-8.15, -3.65, 2.15, 0.42);
    ctx.fillRect(-8.15, 3.23, 2.15, 0.42);

    // Central FIA Rear Rain / ERS Strobe Light
    if ((c.rech || c.ovt) && Math.floor(now / 110) % 2 === 0 && !c.dnf) {
      ctx.fillStyle = c.ovt ? "#00e676" : "#ff1e00";
      ctx.fillRect(-8.35, -0.55, 0.85, 1.1);
    }

    ctx.restore();
  }

  _drawDriverTags(ctx) {
    if (!this.tick) return;
    const {scale,ox,oy}=this._viewTransform;
    ctx.save();ctx.translate(-ox/scale,-oy/scale);ctx.scale(1/scale,1/scale);

    const manShortMap = {
      DIVEBOMB: "DIVE",
      OUTSIDE: "OUTS",
      SWITCHBACK: "SWBK",
      DUMMY: "DUMY",
      SLIPSTREAM: "TOW",
    };

    const visiblePositions = [];
    const tagItems = [];
    for (const c of this.tick.cars) {
      if (!c.vis || c.pit_tunnel) continue;
      const st = this.carInterp.get(c.id);
      if (!st) continue;
      visiblePositions.push({ id: c.id, x: st.cx*scale+ox, y: st.cy*scale+oy });

      const isMyTeam = c.tid === this.tick.player_team_id;
      const isSelected = c.id === this.selectedDriverId;
      const hasManeuver = Boolean(c.man && c.man !== "DEFEND" && !c.dnf);
      const hasDmg = Boolean(c.dmg > 15 && !c.dnf);
      const showTag =
        !c.elim &&
        (this.camZoom > 1.35 ||
          c.pos <= 3 ||
          isMyTeam ||
          isSelected ||
          c.ovt ||
          c.blue_flag ||
          hasManeuver ||
          hasDmg ||
          c.dnf);

      if (showTag) {
        const priority = isSelected ? 0 : isMyTeam ? 1 : c.blue_flag ? 2 : hasManeuver ? 3 : hasDmg ? 4 : 5;
        tagItems.push({ c, x: st.cx*scale+ox, y: st.cy*scale+oy, isMyTeam, isSelected, hasManeuver, priority });
      }
    }

    // Place highest-priority tags first so leaders & selected drivers get ideal slots
    tagItems.sort((a, b) => a.priority - b.priority || a.c.pos - b.c.pos);

    const placedBoxes = [];
    ctx.save();
    ctx.font = "800 8px 'Titillium Web', Inter, sans-serif";
    ctx.textAlign = "left";
    ctx.textBaseline = "middle";

    for (const item of tagItems) {
      const { c, x, y, isSelected, hasManeuver } = item;
      const manShort = c.man && manShortMap[c.man] ? ` ${manShortMap[c.man]}` : "";
      const dmgSuffix = (c.dmg > 15 && !c.dnf) ? " [FW DMG]" : "";
      const blueSuffix = (c.blue_flag && !c.dnf) ? " [BLUE]" : "";
      const drsOvtTag = (c.drs || c.aero === "DRS") ? " DRS" : (c.ovt ? " OVT" : "");
      const suffix = c.dnf ? " OUT" : `${drsOvtTag}${manShort}${dmgSuffix}${blueSuffix}`;
      const text = `${c.code}${suffix}`;
      const textW = ctx.measureText(text).width;
      const logoSize = 9.5;
      const boxW = textW + logoSize + 10;
      const boxH = 12;

      const candidates = [
        [0, -16.5],
        [0, 5.2],
        [0, -29.5],
        [0, 18.2],
        [-boxW * 0.58, -16.5],
        [boxW * 0.58, -16.5],
        [-boxW * 0.58, 5.2],
        [boxW * 0.58, 5.2],
      ];

      let bestLx = x - boxW * 0.5;
      let bestLy = y - 16.5;
      let bestScore = Infinity;

      for (let k = 0; k < candidates.length; k++) {
        const [ox, oy] = candidates[k];
        const lx = x + ox - boxW * 0.5;
        const ly = y + oy;
        let penalty = k * 4.0;

        // Avoid overlapping already-placed driver callout tags
        for (const b of placedBoxes) {
          if (lx < b.x + b.w + 2.0 && lx + boxW + 2.0 > b.x && ly < b.y + b.h + 1.8 && ly + boxH + 1.8 > b.y) {
            penalty += 1000.0;
          }
        }

        // Avoid covering adjacent side-by-side car bodies
        for (const vp of visiblePositions) {
          if (vp.id === c.id) continue;
          if (vp.x > lx - 3.5 && vp.x < lx + boxW + 3.5 && vp.y > ly - 3.0 && vp.y < ly + boxH + 3.0) {
            penalty += 250.0;
          }
        }

        if (penalty < bestScore) {
          bestScore = penalty;
          bestLx = lx;
          bestLy = ly;
          if (penalty === 0) break;
        }
      }

      placedBoxes.push({ x: bestLx, y: bestLy, w: boxW, h: boxH });

      const hasFwDmg = c.dmg > 15 && !c.dnf;
      const accentCol = hasFwDmg
        ? "#ff3b30"
        : c.blue_flag
        ? "#2563eb"
        : hasManeuver
        ? (c.man === "DIVEBOMB" ? "#ff7b00" : c.man === "OUTSIDE" ? "#38bdf8" : "#00e676")
        : c.ovt
        ? "#00d26a"
        : isSelected
        ? "#ffffff"
        : c.tcol;

      // Subtle leader line connecting displaced tag to its car
      const anchorX = Math.max(bestLx + 3, Math.min(bestLx + boxW - 3, x));
      const anchorY = bestLy + boxH < y ? bestLy + boxH : bestLy > y ? bestLy : bestLy + boxH * 0.5;
      if (Math.hypot(anchorX - x, anchorY - y) > 4.5) {
        ctx.strokeStyle = "rgba(255, 255, 255, 0.34)";
        ctx.lineWidth = 0.8;
        ctx.beginPath();
        ctx.moveTo(x, y);
        ctx.lineTo(anchorX, anchorY);
        ctx.stroke();
      }

      // Broadcast tag background
      ctx.fillStyle = "rgba(15, 15, 22, 0.93)";
      ctx.beginPath();
      ctx.roundRect(bestLx, bestLy, boxW, boxH, 2);
      ctx.fill();

      // Left vertical accent bar
      ctx.fillStyle = accentCol;
      ctx.fillRect(bestLx, bestLy, 2.4, boxH);

      const logoImg2 = getTeamLogoImage(c.tid);
      if (logoImg2 && logoImg2.complete && logoImg2.naturalWidth > 0) {
        ctx.drawImage(logoImg2, bestLx + 4, bestLy + 1.25, logoSize, logoSize);
      }

      ctx.fillStyle = hasManeuver ? accentCol : c.ovt ? "#00e676" : "#ffffff";
      ctx.fillText(text, bestLx + 4 + logoSize + 2.5, bestLy + boxH * 0.5 + 0.4);
    }

    ctx.restore();
    ctx.restore();
  }

  _drawRain(ctx, dt, wetness) {
    ctx.save();
    ctx.strokeStyle = `rgba(180, 215, 255, ${Math.min(0.36, wetness / 210)})`;
    ctx.lineWidth = 1.0;
    for (const r of this.rainDrops) {
      r.x -= r.spd * 22 * dt;
      r.y += r.spd * 48 * dt;
      if (r.y > 680) {
        r.y = -20;
        r.x = Math.random() * 1100;
      }
      if (r.x < -30) r.x = 1050;
      ctx.beginPath();
      ctx.moveTo(r.x, r.y);
      ctx.lineTo(r.x - 4, r.y + 10);
      ctx.stroke();
    }
    ctx.restore();
  }
}
