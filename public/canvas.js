// High-DPI 60fps 2D Real-GPS Circuit & Detailed 2026 F1 Car Renderer
import { getTeamLogoImage } from "/logos.js";
import { SceneryLayer } from "/scenery.js";
import { getCarSurfaces, getCarbonPaint, FLOOR_SURFACE_BOUNDS, BODY_SURFACE_BOUNDS } from "/car-materials.js";

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
  let diff = (b - a) % (Math.PI * 2);
  if (diff > Math.PI) diff -= Math.PI * 2;
  if (diff < -Math.PI) diff += Math.PI * 2;
  return a + diff * t;
}

function unwrapAngleNear(angle, ref) {
  let diff = (angle - ref) % (Math.PI * 2);
  if (diff > Math.PI) diff -= Math.PI * 2;
  if (diff < -Math.PI) diff += Math.PI * 2;
  return ref + diff;
}

function catmullRomValue(v0, v1, v2, v3, t) {
  const t2 = t * t;
  const t3 = t2 * t;
  return 0.5 * (
    (2 * v1)
    + (-v0 + v2) * t
    + (2 * v0 - 5 * v1 + 4 * v2 - v3) * t2
    + (-v0 + 3 * v1 - 3 * v2 + v3) * t3
  );
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
    this.directorStatus = "";
    this._directorLockUntil = 0;
    this._directorPrio = 0;
    this._directorTargetId = null;
    this._directorTargetBId = null;

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
    if (mode !== "director") {
      this.directorStatus = "";
      this._directorPrio = 0;
      this._directorTargetId = null;
      this._directorTargetBId = null;
    }
  }

  setSelectedDriver(driverId) {
    this.selectedDriverId = driverId;
    if (this.cameraMode === "selected") {
      this._camLocked = false;
      this._camTransitElapsed = 0;
    }
  }

  resetInterpolation() {
    this.carInterp.clear();
    this.scInterp = null;
    this.renderTimeInitialized = false;
    this.renderTickInitialized = false;
    this.renderTick = 0;
    this.playbackRate = 1.0;
    this.particles = [];
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
          steer: c.steer || 0.0,
          buffer: [{ tick: currentTick, x: c.x, y: c.y, h: c.h, steer: c.steer || 0.0 }],
          data: c,
        };
        this.carInterp.set(c.id, st);
      } else {
        st.data = c;
        st.buffer.push({ tick: currentTick, x: c.x, y: c.y, h: c.h, steer: c.steer || 0.0 });
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

          // Unwrapped cubic Catmull-Rom angular & steering interpolation for C1 continuity
          const crIdx = buf.indexOf(s1);
          const cr0 = buf[Math.max(0, crIdx - 1)];
          const cr3 = buf[Math.min(buf.length - 1, crIdx + 2)];
          const h1 = s1.h;
          const h0 = unwrapAngleNear(cr0.h, h1);
          const h2 = unwrapAngleNear(s2.h, h1);
          const h3 = unwrapAngleNear(cr3.h, h2);
          const jumpH = Math.abs(h1 - h0) > 0.45 || Math.abs(h2 - h1) > 0.45 || Math.abs(h3 - h2) > 0.45;
          st.ch = jumpH
            ? lerpAngle(s1.h, s2.h, t)
            : unwrapAngleNear(catmullRomValue(h0, h1, h2, h3, t), 0);

          const fallbackSteer = st.data?.steer || 0.0;
          const st0 = cr0.steer !== undefined ? cr0.steer : fallbackSteer;
          const st1 = s1.steer !== undefined ? s1.steer : fallbackSteer;
          const st2 = s2.steer !== undefined ? s2.steer : fallbackSteer;
          const st3 = cr3.steer !== undefined ? cr3.steer : fallbackSteer;
          const jumpSteer = Math.abs(st1 - st0) > 0.45 || Math.abs(st2 - st1) > 0.45 || Math.abs(st3 - st2) > 0.45;
          st.steer = jumpSteer
            ? st1 + (st2 - st1) * t
            : Math.max(-0.45, Math.min(0.45, catmullRomValue(st0, st1, st2, st3, t)));
        } else if (this.renderTick < buf[0].tick) {
          st.cx = buf[0].x;
          st.cy = buf[0].y;
          st.ch = buf[0].h;
          st.steer = buf[0].steer || 0.0;
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
          const dhDiff = unwrapAngleNear(last.h, prev.h) - prev.h;
          const dhPerTick = Math.max(-0.35, Math.min(0.35, dhDiff / dtTicks));
          st.ch = unwrapAngleNear(last.h + dhPerTick * extraTicks, 0);
          const prevSteer = prev.steer || 0.0;
          const lastSteer = last.steer || 0.0;
          const dsPerTick = Math.max(-0.2, Math.min(0.2, (lastSteer - prevSteer) / dtTicks));
          st.steer = Math.max(-0.45, Math.min(0.45, lastSteer + dsPerTick * extraTicks));
        }
      } else {
        st.cx = buf[0].x;
        st.cy = buf[0].y;
        st.ch = buf[0].h;
        st.steer = buf[0].steer || 0.0;
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
      } else if (this.cameraMode === "director") {
        const now = performance.now();
        const cars = this.tick.cars || [];
        const incident = cars.find((c) => c.vis && !c.in_pit && (c.smoke > 1.5 || c.dnf));
        const myPit = cars.find((c) => c.tid === this.tick.player_team_id && c.in_pit && (c.pit_ph === "ENTRY" || c.pit_ph === "STOPPED"));
        const myBattle = cars.find((c) => c.tid === this.tick.player_team_id && c.battle && !c.dnf);
        const topBattle = cars.find((c) => c.battle && !c.dnf && c.pos <= 10);
        const leaderCar = cars.find((c) => !c.dnf && !c.elim) || cars[0];

        let candPrio = 1;
        let candA = leaderCar ? leaderCar.id : null;
        let candB = null;
        let candZoom = 2.45 * zoomRatio;
        let candLabel = leaderCar ? `LEADER · ${leaderCar.code}` : "DIRECTOR";

        if (incident) {
          candPrio = 4;
          candA = incident.id;
          candZoom = 2.85 * zoomRatio;
          candLabel = `INCIDENT · ${incident.code}`;
        } else if (myPit) {
          candPrio = 3;
          candA = myPit.id;
          candZoom = 3.05 * zoomRatio;
          candLabel = `PIT BOX · ${myPit.code}`;
        } else if (myBattle || topBattle) {
          const bCar = myBattle || topBattle;
          const rival = cars.find((c) => c.code === bCar.battle && !c.dnf);
          candPrio = 2;
          candA = bCar.id;
          candB = rival ? rival.id : null;
          candLabel = rival ? `BATTLE · ${bCar.code} vs ${rival.code}` : `BATTLE · ${bCar.code}`;
        }

        const curCarValid = this._directorTargetId && cars.some((c) => c.id === this._directorTargetId && c.vis);
        const pitExited = this._directorPrio === 3 && this._directorTargetId && !cars.some((c) => c.id === this._directorTargetId && c.in_pit);
        if (!curCarValid || pitExited || now > this._directorLockUntil || candPrio > this._directorPrio) {
          this._directorPrio = candPrio;
          this._directorTargetId = candA;
          this._directorTargetBId = candB;
          this._directorLockUntil = now + (candPrio >= 3 ? 3500 : 4500);
          this.directorStatus = candLabel;
        }

        const stA = this._directorTargetId && this.carInterp.get(this._directorTargetId);
        const stB = this._directorTargetBId && this.carInterp.get(this._directorTargetBId);
        if (stA && stB) {
          isTrackingCar = true;
          targetX = (stA.cx + stB.cx) * 0.5;
          targetY = (stA.cy + stB.cy) * 0.5;
          const battleDist = Math.hypot(stA.cx - stB.cx, stA.cy - stB.cy);
          targetZoom = Math.max(1.6, Math.min(2.75, 2.45 * zoomRatio * (65 / Math.max(45, battleDist))));
          currentTargetKey = "dir:" + this._directorTargetId + "-" + this._directorTargetBId;
        } else if (stA) {
          isTrackingCar = true;
          targetX = stA.cx;
          targetY = stA.cy;
          targetZoom = this._directorPrio === 3 ? 3.05 * zoomRatio : (this._directorPrio === 4 ? 2.85 * zoomRatio : 2.45 * zoomRatio);
          currentTargetKey = "dir:" + this._directorTargetId;
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
    const lightingPhase = this.tick?.lighting_phase || 0;
    if (lightingPhase > 0.05) {
      this._drawNightAtmosphere(ctx, lightingPhase);
    }
    this._drawParticles(ctx);
    this._drawCars(ctx, now);
    if (this.tick && this.tick.wetness >= 15) {
      this._drawRain(ctx, dt, this.tick.wetness);
    }

    ctx.restore();

    if (this.cameraMode !== "full" || this.camZoom > 1.25) {
      this._drawMiniMapPiP(ctx);
    }
  }

  _drawEnvironment(ctx, now) {
    this.scenery.draw(ctx, this.track, this._viewTransform, this.width, this.height, this.dpr);
  }

  _drawRunoffZones(ctx) {
    const zones = this.track.runoff_zones;
    if (!zones || !zones.length) return;
    ctx.save();
    ctx.lineJoin = "round";
    ctx.lineCap = "round";
    for (const z of zones) {
      const inner = z.points;
      const outer = z.outer_points;
      if (!inner || !outer || inner.length < 3 || outer.length < 3) continue;

      let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
      for (const p of inner) {
        if (p[0] < minX) minX = p[0];
        if (p[0] > maxX) maxX = p[0];
        if (p[1] < minY) minY = p[1];
        if (p[1] > maxY) maxY = p[1];
      }
      for (const p of outer) {
        if (p[0] < minX) minX = p[0];
        if (p[0] > maxX) maxX = p[0];
        if (p[1] < minY) minY = p[1];
        if (p[1] > maxY) maxY = p[1];
      }

      ctx.beginPath();
      ctx.moveTo(inner[0][0], inner[0][1]);
      for (let i = 1; i < inner.length - 1; i++) {
        const mx = (inner[i][0] + inner[i + 1][0]) * 0.5;
        const my = (inner[i][1] + inner[i + 1][1]) * 0.5;
        ctx.quadraticCurveTo(inner[i][0], inner[i][1], mx, my);
      }
      ctx.lineTo(inner[inner.length - 1][0], inner[inner.length - 1][1]);
      ctx.lineTo(outer[outer.length - 1][0], outer[outer.length - 1][1]);
      for (let i = outer.length - 2; i >= 1; i--) {
        const mx = (outer[i][0] + outer[i - 1][0]) * 0.5;
        const my = (outer[i][1] + outer[i - 1][1]) * 0.5;
        ctx.quadraticCurveTo(outer[i][0], outer[i][1], mx, my);
      }
      ctx.lineTo(outer[0][0], outer[0][1]);
      ctx.closePath();

      if (z.surface === "gravel") {
        ctx.fillStyle = "#6f6250";
        ctx.fill();
        ctx.strokeStyle = "rgba(42, 34, 24, 0.72)";
        ctx.lineWidth = 1.4;
        ctx.stroke();
      } else {
        ctx.fillStyle = "#1a1f28";
        ctx.fill();
        ctx.save();
        ctx.clip();
        const span = (maxX - minX) + (maxY - minY);
        const startC = minX + minY - 4;
        const endC = startC + span + 8;
        ctx.lineWidth = 2.4;
        for (let idx = 0, c = startC; c <= endC; c += 6.5, idx++) {
          ctx.beginPath();
          ctx.moveTo(minX - 4, c - (minX - 4));
          ctx.lineTo(maxX + 4, c - (maxX + 4));
          ctx.strokeStyle = idx % 2 === 0 ? "rgba(56, 130, 246, 0.20)" : "rgba(225, 6, 0, 0.14)";
          ctx.stroke();
        }
        ctx.restore();
      }

      this._traceSmoothOpenPoints(ctx, outer);
      ctx.strokeStyle = "rgba(18, 22, 30, 0.88)";
      ctx.lineWidth = 2.2;
      ctx.stroke();
      ctx.strokeStyle = z.surface === "gravel" ? "rgba(225, 40, 30, 0.45)" : "rgba(235, 240, 250, 0.28)";
      ctx.lineWidth = 0.8;
      ctx.stroke();
    }
    ctx.restore();
  }

  _drawTrack(ctx, now) {
    const sts = this.track.stations;
    const n = sts.length;
    const wPx = this.track.track_width_px || 24.5;

    // 0. Real-Circuit Gravel & Tarmac Runoff Aprons underneath track verges
    this._drawRunoffZones(ctx);

    // 1. Track & Pit Outer Verge Shadows first so verges never overlap adjacent asphalt or pit joins
    this._traceRoadRibbon(ctx, sts, 7.6);
    ctx.fillStyle = "#060609";
    ctx.lineJoin = "round";
    ctx.fill();

    const ppts = this.track.pit_points || [];
    const pitWidth = this.track.pit_width_px || 32;
    if (ppts.length > 1) {
      const side = this.track.pit_side || 1;
      const geom = this.track.car_geometry || { length_m: 5.5, width_m: 1.9, front_axle_m: 1.55, world_units_per_m: 3.2 };
      const ppm = geom.world_units_per_m || 3.2;
      const stallLen = (geom.length_m + 0.9) * ppm;
      const stallWid = (geom.width_m + 0.45) * ppm;
      const fastOff = this.track.pit_fast_offset_px ?? (-1.6 * ppm);
      const apronOff = this.track.pit_apron_offset_px ?? (3.0 * ppm);
      const laneDividerOff = (apronOff - stallWid * 0.5 - 1.1) * side;

      const uSpeedIn = this.track.pit_speed_entry_u ?? 0.1;
      const uSpeedOut = this.track.pit_speed_exit_u ?? 0.9;
      const pitLenM = Math.max(80, this.track.pit_length_m || 360);
      const garages = this.track.pit_garages || [];
      let uGarMin = uSpeedIn + 0.04;
      let uGarMax = uSpeedOut - 0.04;
      if (garages.length > 0) {
        uGarMin = 1.0;
        uGarMax = 0.0;
        for (const g of garages) {
          let bestK = 0;
          let bestD2 = Infinity;
          for (let k = 0; k < ppts.length; k++) {
            const dx = ppts[k][0] - g.x;
            const dy = ppts[k][1] - g.y;
            const d2 = dx * dx + dy * dy;
            if (d2 < bestD2) {
              bestD2 = d2;
              bestK = k;
            }
          }
          const gu = bestK / Math.max(1, ppts.length - 1);
          if (gu < uGarMin) uGarMin = gu;
          if (gu > uGarMax) uGarMax = gu;
        }
      }

      const smoothstep = (t) => {
        const c = Math.max(0, Math.min(1, t));
        return c * c * (3 - 2 * c);
      };
      const taperU = Math.min(36.0, pitLenM * 0.20) / pitLenM;
      const rampU = Math.min(0.16, Math.max(0.075, 58.0 / pitLenM));
      const wFull0 = Math.max(0.03, Math.min(uGarMin - 0.025, uSpeedIn + 0.025));
      const wFull1 = Math.min(0.97, Math.max(uGarMax + 0.025, uSpeedOut - 0.025));
      const wStart0 = Math.max(0.01, wFull0 - rampU);
      const wEnd1 = Math.min(0.99, wFull1 + rampU);
      const fastHalf = Math.max(4.4, 1.95 * ppm);
      const workingOuter = Math.max(apronOff + stallWid * 0.5 + 2.0, pitWidth * 0.5);

      const nPit = ppts.length;
      const workRampAt = new Array(nPit);
      const wallOffs = new Array(nPit);
      const apronOffs = new Array(nPit);
      const shadowWallOffs = new Array(nPit);
      const shadowApronOffs = new Array(nPit);
      const concInnerOffs = new Array(nPit);
      const concOuterOffs = new Array(nPit);
      for (let k = 0; k < nPit; k++) {
        const u = k / Math.max(1, nPit - 1);
        const fastFade = Math.min(smoothstep(u / Math.max(0.01, taperU)), smoothstep((1 - u) / Math.max(0.01, taperU)));
        const fastCenter = fastOff * fastFade;
        let wr = 1.0;
        if (u <= wStart0 || u >= wEnd1) wr = 0.0;
        else if (u < wFull0) wr = smoothstep((u - wStart0) / Math.max(0.01, wFull0 - wStart0));
        else if (u > wFull1) wr = smoothstep((wEnd1 - u) / Math.max(0.01, wEnd1 - wFull1));
        workRampAt[k] = wr;
        const wOff = fastCenter - fastHalf;
        const aOff = (fastCenter + fastHalf) * (1 - wr) + workingOuter * wr;
        wallOffs[k] = wOff;
        apronOffs[k] = aOff;
        shadowWallOffs[k] = wOff - 2.3;
        shadowApronOffs[k] = aOff + 2.3;
        const cIn = fastCenter + fastHalf * 0.45;
        concInnerOffs[k] = cIn;
        concOuterOffs[k] = Math.max(cIn, aOff - 0.8);
      }

      const shWallPts = this._buildPitEdgePoints(ppts, side, shadowWallOffs);
      const shApronPts = this._buildPitEdgePoints(ppts, side, shadowApronOffs);
      const wallPts = this._buildPitEdgePoints(ppts, side, wallOffs);
      const apronPts = this._buildPitEdgePoints(ppts, side, apronOffs);

      // 1. Continuous tapered pit verge shadow
      this._tracePitRibbon(ctx, shWallPts, shApronPts);
      ctx.fillStyle = "#060609";
      ctx.fill();

      // 2. Smooth continuous asphalt ribbon (no abrupt step widening)
      this._tracePitRibbon(ctx, wallPts, apronPts);
      ctx.fillStyle = "#161b26";
      ctx.fill();

      // 3. Contrasting FIA garage apron zone across the flared working bay
      const wStartIdx = Math.max(0, Math.floor(wStart0 * (nPit - 1)));
      const wEndIdx = Math.min(nPit - 1, Math.ceil(wEnd1 * (nPit - 1)));
      if (wEndIdx > wStartIdx + 2) {
        const concSlice = ppts.slice(wStartIdx, wEndIdx + 1);
        const cInPts = this._buildPitEdgePoints(concSlice, side, concInnerOffs.slice(wStartIdx, wEndIdx + 1));
        const cOutPts = this._buildPitEdgePoints(concSlice, side, concOuterOffs.slice(wStartIdx, wEndIdx + 1));
        this._tracePitRibbon(ctx, cInPts, cOutPts);
        ctx.fillStyle = "#1e2433";
        ctx.fill();
      }

      // 4. Crisp white pit-lane boundary stripes along both tapered edges
      ctx.save();
      ctx.strokeStyle = "rgba(255,255,255,.46)";
      ctx.lineWidth = 0.9;
      ctx.lineCap = "round";
      ctx.lineJoin = "round";
      this._traceSmoothOpenPoints(ctx, wallPts);
      ctx.stroke();
      this._traceSmoothOpenPoints(ctx, apronPts);
      ctx.stroke();
      ctx.restore();

      // 5. Sleek FIA Pit Wall barrier along working complex edge (towards track side)
      const fia0 = Math.max(0, Math.floor(wFull0 * (nPit - 1)));
      const fia1 = Math.min(nPit - 1, Math.ceil(wFull1 * (nPit - 1)));
      if (fia1 > fia0 + 2) {
        const pitWallBarPts = this._buildPitEdgePoints(
          ppts.slice(fia0, fia1 + 1),
          side,
          wallOffs.slice(fia0, fia1 + 1).map((o) => o - 1.5),
        );
        ctx.save();
        ctx.lineCap = "butt";
        ctx.lineJoin = "round";
        ctx.strokeStyle = "#343c4e";
        ctx.lineWidth = 2.0;
        this._traceSmoothOpenPoints(ctx, pitWallBarPts);
        ctx.stroke();
        ctx.strokeStyle = "rgba(225, 6, 0, 0.55)";
        ctx.lineWidth = 0.6;
        ctx.stroke();
        ctx.restore();
      }

      const iDiv0 = Math.max(0, Math.floor(uSpeedIn * (ppts.length - 1)));
      const iDiv1 = Math.min(ppts.length - 1, Math.ceil(uSpeedOut * (ppts.length - 1)));
      if (iDiv1 > iDiv0 + 1) {
        ctx.save();
        ctx.strokeStyle = "rgba(255, 255, 255, 0.36)";
        ctx.lineWidth = 0.85;
        ctx.setLineDash([4.5, 4.5]);
        ctx.beginPath();
        for (let k = iDiv0; k <= iDiv1; k++) {
          const prev = ppts[Math.max(0, k - 1)];
          const next = ppts[Math.min(ppts.length - 1, k + 1)];
          const dx = next[0] - prev[0], dy = next[1] - prev[1];
          const segL = Math.hypot(dx, dy) || 1;
          const pnx = -dy / segL, pny = dx / segL;
          const px = ppts[k][0] + pnx * laneDividerOff;
          const py = ppts[k][1] + pny * laneDividerOff;
          if (k === iDiv0) ctx.moveTo(px, py);
          else ctx.lineTo(px, py);
        }
        ctx.stroke();
        ctx.restore();
      }

      // 6. Yellow FIA 80 km/h speed limit entry & exit lines trimmed strictly between asphalt edges
      for (const u of [uSpeedIn, uSpeedOut]) {
        const i = Math.max(0, Math.min(nPit - 1, Math.round(u * (nPit - 1))));
        ctx.beginPath();
        ctx.moveTo(wallPts[i].x, wallPts[i].y);
        ctx.lineTo(apronPts[i].x, apronPts[i].y);
        ctx.strokeStyle = "#ffd700";
        ctx.lineWidth = 1.5;
        ctx.stroke();
      }
      // Team Pit Stall locations with Constructor Logos & Gantry Graphics
      for (const g of this.track.pit_garages || []) {
        const teamId = GARAGE_TEAM_IDS[g.index] || "williams";
        const cMeta = this.tick?.custom_team_meta;
        const isCust = cMeta && cMeta.id === teamId;
        const teamCode = isCust ? (cMeta.code || "MY") : (GARAGE_TEAM_CODES[g.index] || "F1");
        const teamColor = isCust ? (cMeta.secondary || cMeta.color || "#00d2be") : (TEAM_LIVERY[teamId]?.stripe || "#00d2be");

        const nx = -g.ty * side, ny = g.tx * side;
        const gx = g.x + nx * apronOff, gy = g.y + ny * apronOff;
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

        // 5. Pit Wall / Garage Gantry Nameplate Tag strictly on Outer Garage Side
        ctx.fillStyle = "rgba(12, 14, 20, 0.88)";
        const tagW = Math.max(stallLen * 0.38, 14);
        const tagH = Math.max(stallWid * 0.38, 5.5);
        const tagY = side >= 0 ? (stallWid * 0.5 + 0.8) : (-stallWid * 0.5 - tagH - 0.8);
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

    // 3. FIA Red & White Corner Kerbs
    const kerbOut = this._computeSmoothEdgePoints(sts, 1, -1.6);
    const kerbIn = this._computeSmoothEdgePoints(sts, -1, -1.6);
    ctx.save();
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    ctx.lineWidth = 5.8;
    for (let i = 0; i < n; i++) {
      if (sts[i].curv > 0.012) {
        const ip = (i - 1 + n) % n;
        const nx = (i + 1) % n;
        ctx.strokeStyle = i % 2 === 0 ? "#e10600" : "#e8ecf2";
        for (const edge of [kerbOut, kerbIn]) {
          const pPrev = edge[ip], pCur = edge[i], pNext = edge[nx];
          ctx.beginPath();
          ctx.moveTo((pPrev.x + pCur.x) * 0.5, (pPrev.y + pCur.y) * 0.5);
          ctx.quadraticCurveTo(pCur.x, pCur.y, (pCur.x + pNext.x) * 0.5, (pCur.y + pNext.y) * 0.5);
          ctx.stroke();
        }
      }
    }
    ctx.restore();

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
      let groove = this.track.racing_line_points.map((p) => ({ x: p[0], y: p[1] }));
      const gn = groove.length;
      for (let pass = 0; pass < 2; pass++) {
        groove = groove.map((p, idx) => {
          const prv = groove[(idx - 1 + gn) % gn];
          const nxt = groove[(idx + 1) % gn];
          return {
            x: 0.22 * prv.x + 0.56 * p.x + 0.22 * nxt.x,
            y: 0.22 * prv.y + 0.56 * p.y + 0.22 * nxt.y,
          };
        });
      }
      ctx.save();
      ctx.lineJoin = "round";
      ctx.lineCap = "round";

      // 1. Soft wide rubbered track foundation & progressive race rubber
      const rubberPct = (this.tick && this.tick.track_rubber != null) ? (this.tick.track_rubber / 100) : 0.45;
      const fAlpha = (wet > 25 ? 0.14 : (0.16 + rubberPct * 0.24)).toFixed(2);
      const cAlpha = (wet > 25 ? 0.26 : (0.28 + rubberPct * 0.38)).toFixed(2);
      this._traceSmoothClosedPoints(ctx, groove);
      ctx.strokeStyle = wet > 25 ? "rgba(8, 10, 14, 0.16)" : `rgba(10, 10, 14, ${fAlpha})`;
      ctx.lineWidth = Math.max(6.5, wPx * 0.38);
      ctx.stroke();

      // 2. High-grip dark central rubber groove
      ctx.strokeStyle = wet > 25 ? "rgba(6, 8, 12, 0.28)" : `rgba(6, 6, 10, ${cAlpha})`;
      ctx.lineWidth = Math.max(3.6, wPx * 0.20);
      ctx.stroke();
      ctx.restore();
    } else {
      this._traceClosedSpline(ctx, sts);
      ctx.strokeStyle = "rgba(10, 10, 14, 0.32)";
      ctx.lineWidth = Math.max(6.0, wPx * 0.34);
      ctx.stroke();
    }

    // 4a-bis. FIA White Dashed Pit Entry / Exit Lane Blend Markings
    for (const bpts of [this.track.pit_entry_blend_points, this.track.pit_blend_points]) {
      if (bpts && bpts.length >= 2) {
        ctx.save();
        ctx.beginPath();
        ctx.moveTo(bpts[0][0], bpts[0][1]);
        for (let i = 1; i < bpts.length; i++) {
          ctx.lineTo(bpts[i][0], bpts[i][1]);
        }
        ctx.strokeStyle = "rgba(245, 247, 252, 0.65)";
        ctx.lineWidth = 1.0;
        ctx.setLineDash([4.5, 3.5]);
        ctx.stroke();
        ctx.restore();
      }
    }

    // 4b. Drying Racing Groove Contrast (dry/drier line vs wet offline marbles)
    const gWet = (this.tick && this.tick.groove_wetness != null) ? this.tick.groove_wetness : wet;
    const oWet = (this.tick && this.tick.offline_wetness != null) ? this.tick.offline_wetness : wet;
    if (oWet > gWet + 6) {
      ctx.save();
      this._traceClosedSpline(ctx, sts);
      const contrast = Math.min(0.65, 0.25 + (oWet - gWet) / 60);
      ctx.strokeStyle = `rgba(18, 22, 32, ${contrast.toFixed(2)})`;
      ctx.lineWidth = Math.max(5.5, wPx * 0.36);
      ctx.stroke();
      ctx.restore();
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

  _traceSmoothClosedPoints(ctx, pts, doBeginPath = true) {
    if (doBeginPath) ctx.beginPath();
    const n = pts.length;
    if (n < 2) return;
    const gx = (p) => (Array.isArray(p) ? p[0] : p.x);
    const gy = (p) => (Array.isArray(p) ? p[1] : p.y);
    const pLast = pts[n - 1], p0 = pts[0];
    ctx.moveTo((gx(pLast) + gx(p0)) * 0.5, (gy(pLast) + gy(p0)) * 0.5);
    for (let i = 0; i < n; i++) {
      const p = pts[i];
      const nxt = pts[(i + 1) % n];
      ctx.quadraticCurveTo(
        gx(p),
        gy(p),
        (gx(p) + gx(nxt)) * 0.5,
        (gy(p) + gy(nxt)) * 0.5,
      );
    }
    ctx.closePath();
  }

  _traceSmoothOpenPoints(ctx, pts) {
    ctx.beginPath();
    const n = pts.length;
    if (n === 0) return;
    const gx = (p) => (Array.isArray(p) ? p[0] : p.x);
    const gy = (p) => (Array.isArray(p) ? p[1] : p.y);
    ctx.moveTo(gx(pts[0]), gy(pts[0]));
    if (n === 2) {
      ctx.lineTo(gx(pts[1]), gy(pts[1]));
      return;
    }
    for (let i = 1; i < n - 1; i++) {
      const mx = (gx(pts[i]) + gx(pts[i + 1])) * 0.5;
      const my = (gy(pts[i]) + gy(pts[i + 1])) * 0.5;
      ctx.quadraticCurveTo(gx(pts[i]), gy(pts[i]), mx, my);
    }
    ctx.lineTo(gx(pts[n - 1]), gy(pts[n - 1]));
  }

  _buildPitEdgePoints(ppts, side, offsets) {
    const n = ppts.length;
    let pts = new Array(n);
    for (let k = 0; k < n; k++) {
      const prev = ppts[Math.max(0, k - 1)];
      const next = ppts[Math.min(n - 1, k + 1)];
      const dx = next[0] - prev[0], dy = next[1] - prev[1];
      const segL = Math.hypot(dx, dy) || 1;
      const nx = (-dy / segL) * side, ny = (dx / segL) * side;
      const off = offsets[k] || 0;
      pts[k] = { x: ppts[k][0] + nx * off, y: ppts[k][1] + ny * off };
    }
    for (let pass = 0; pass < 2; pass++) {
      const nextPts = pts.slice();
      for (let k = 1; k < n - 1; k++) {
        nextPts[k] = {
          x: 0.22 * pts[k - 1].x + 0.56 * pts[k].x + 0.22 * pts[k + 1].x,
          y: 0.22 * pts[k - 1].y + 0.56 * pts[k].y + 0.22 * pts[k + 1].y,
        };
      }
      pts = nextPts;
    }
    return pts;
  }

  _tracePitRibbon(ctx, sideAPts, sideBPts) {
    const nA = sideAPts.length;
    const revB = [...sideBPts].reverse();
    const nB = revB.length;
    ctx.beginPath();
    if (nA < 2 || nB < 2) return;
    ctx.moveTo(sideAPts[0].x, sideAPts[0].y);
    for (let i = 1; i < nA - 1; i++) {
      const mx = (sideAPts[i].x + sideAPts[i + 1].x) * 0.5;
      const my = (sideAPts[i].y + sideAPts[i + 1].y) * 0.5;
      ctx.quadraticCurveTo(sideAPts[i].x, sideAPts[i].y, mx, my);
    }
    ctx.lineTo(sideAPts[nA - 1].x, sideAPts[nA - 1].y);
    ctx.lineTo(revB[0].x, revB[0].y);
    for (let i = 1; i < nB - 1; i++) {
      const mx = (revB[i].x + revB[i + 1].x) * 0.5;
      const my = (revB[i].y + revB[i + 1].y) * 0.5;
      ctx.quadraticCurveTo(revB[i].x, revB[i].y, mx, my);
    }
    ctx.lineTo(revB[nB - 1].x, revB[nB - 1].y);
    ctx.closePath();
  }

  _computeSmoothEdgePoints(sts, side, extraWidth = 0) {
    const n = sts.length;
    const rawH = sts.map((p) => ((p.width_px || this.track.track_width_px) + extraWidth) * 0.5);
    let pts = sts.map((p, idx) => {
      const h = rawH[idx];
      return { x: p.x + side * p.nx * h, y: p.y + side * p.ny * h };
    });
    for (let pass = 0; pass < 2; pass++) {
      pts = pts.map((p, idx) => {
        const prv = pts[(idx - 1 + n) % n];
        const nxt = pts[(idx + 1) % n];
        let sx = 0.20 * prv.x + 0.60 * p.x + 0.20 * nxt.x;
        let sy = 0.20 * prv.y + 0.60 * p.y + 0.20 * nxt.y;
        const st = sts[idx];
        const h = rawH[idx];
        const isOutside = side * (st.inside_sign || 1) <= 0;
        if (isOutside || (st.curv || 0) < 0.022) {
          const proj = (sx - st.x) * side * st.nx + (sy - st.y) * side * st.ny;
          if (proj < h * 0.985) {
            const fix = h * 0.985 - proj;
            sx += side * st.nx * fix;
            sy += side * st.ny * fix;
          }
        }
        return { x: sx, y: sy };
      });
    }
    return pts;
  }

  _traceClosedSpline(ctx, sts) {
    this._traceSmoothClosedPoints(ctx, sts, true);
  }

  _traceRoadRibbon(ctx, sts, extraWidth = 0) {
    // One continuous ribbon with smoothed offset borders to prevent hairpin inner pinching.
    const outerPts = this._computeSmoothEdgePoints(sts, 1, extraWidth);
    const innerPts = this._computeSmoothEdgePoints(sts, -1, extraWidth).reverse();
    ctx.beginPath();
    this._traceSmoothClosedPoints(ctx, outerPts, false);
    this._traceSmoothClosedPoints(ctx, innerPts, false);
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

    this._drawRejoinGhost(ctx, now);

    const lightPhase = this.tick?.lighting_phase || 0;
    // Pass 1: Draw all visible 2026 F1 chassis (back-to-front so leaders sit cleanly on top of wakes)
    const ordered = [...this.tick.cars].reverse();
    for (const c of ordered) {
      if (!c.vis || c.pit_tunnel) continue;
      const st = this.carInterp.get(c.id);
      if (!st) continue;
      if (lightPhase > 0.25 && !c.dnf) {
        this._drawCarNightLights(ctx, st.cx, st.cy, st.ch);
      }
      this._drawSingleCar(ctx, st.cx, st.cy, st.ch, c, now, st.steer);
      if (c.in_pit && c.pit_ph === "STOPPED" && c.pit_tot > 0 && c.pit_rem > 0) {
        const frac = Math.max(0, Math.min(1, 1 - c.pit_rem / c.pit_tot));
        const ringCol = c.pit_tot <= 2.05 ? "#a855f7" : c.pit_tot > 3.8 ? "#ffd000" : "#00d2be";
        const sc = Math.max(0.45, this._viewTransform.scale);
        const rad = 11.0 / sc;
        ctx.save();
        ctx.strokeStyle = "rgba(255,255,255,0.18)";
        ctx.lineWidth = 2.0 / sc;
        ctx.beginPath();
        ctx.arc(st.cx, st.cy, rad, 0, Math.PI * 2);
        ctx.stroke();
        ctx.strokeStyle = ringCol;
        ctx.beginPath();
        ctx.arc(st.cx, st.cy, rad, -Math.PI * 0.5, -Math.PI * 0.5 + frac * Math.PI * 2);
        ctx.stroke();
        const elapsedS = Math.max(0, c.pit_tot - c.pit_rem).toFixed(1) + "s";
        ctx.font = `800 ${Math.max(8, 9.5 / sc)}px 'Titillium Web', sans-serif`;
        const bw = ctx.measureText(elapsedS).width + 6 / sc;
        const bh = 12 / sc;
        ctx.fillStyle = "rgba(10,12,18,0.9)";
        ctx.fillRect(st.cx - bw * 0.5, st.cy - rad - bh - 2 / sc, bw, bh);
        ctx.fillStyle = ringCol;
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(elapsedS, st.cx, st.cy - rad - bh * 0.5 - 2 / sc);
        ctx.restore();
      }
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
    const geom = this.track.car_geometry;
    const ppm = geom.world_units_per_m;
    ctx.scale(geom.safety_car_length_m * ppm / 14.4, geom.safety_car_width_m * ppm / 7.6);

    // 1. Ground shadow & subtle LED headlight beams
    ctx.fillStyle = "rgba(0, 0, 0, 0.46)";
    ctx.beginPath();
    ctx.ellipse(-0.1, 0, 7.6, 4.35, 0, 0, Math.PI * 2);
    ctx.fill();

    for (const side of [-1, 1]) {
      const beamGrad = ctx.createLinearGradient(6.7, 0, 12.6, 0);
      beamGrad.addColorStop(0, "rgba(235, 245, 255, 0.20)");
      beamGrad.addColorStop(1, "rgba(235, 245, 255, 0)");
      ctx.fillStyle = beamGrad;
      ctx.beginPath();
      ctx.moveTo(6.7, side * 2.35);
      ctx.lineTo(12.6, side * 4.1);
      ctx.lineTo(12.6, side * 1.15);
      ctx.closePath();
      ctx.fill();
    }

    // Carbon-fiber front splitter + corner aero canards & rear diffuser with quad AMG exhausts
    ctx.fillStyle = "#11141c";
    ctx.beginPath();
    ctx.roundRect(6.25, -3.45, 1.10, 6.90, 0.65);
    ctx.roundRect(-7.30, -3.35, 1.50, 6.70, 0.55);
    ctx.fill();

    for (const side of [-1, 1]) {
      // Front bumper corner aero flicks
      ctx.fillStyle = "#1a1f2b";
      ctx.beginPath();
      ctx.moveTo(6.45, side * 3.25);
      ctx.lineTo(7.15, side * 3.72);
      ctx.lineTo(6.05, side * 3.65);
      ctx.closePath();
      ctx.fill();

      // Rear quad exhaust tips + diffuser strakes
      ctx.fillStyle = "#c9d1dc";
      ctx.fillRect(-7.35, side * 1.65 - 0.24, 0.36, 0.48);
      ctx.fillRect(-7.35, side * 2.35 - 0.24, 0.36, 0.48);
      ctx.fillStyle = "#262c3a";
      ctx.fillRect(-7.22, side * 0.75 - 0.08, 0.65, 0.16);
    }

    // 2. Forged AMG wheels tucked inside front (x=+4.25) and rear (x=-4.15) arches
    const scWheels = [
      [4.25, -3.55], [4.25, 3.55],
      [-4.15, -3.62], [-4.15, 3.62],
    ];
    for (const [wx, wy] of scWheels) {
      ctx.fillStyle = "#0a0c10";
      ctx.beginPath();
      ctx.roundRect(wx - 1.12, wy - 0.46, 2.24, 0.92, 0.32);
      ctx.fill();
      ctx.fillStyle = "#2b3242";
      ctx.fillRect(wx - 0.55, wy + (wy < 0 ? -0.44 : 0.28), 1.10, 0.16);
    }

    // 3. Sculpted Mercedes-AMG GT 63 Coke-bottle fastback silhouette & side skirts
    const bodyGrad = ctx.createLinearGradient(-7.0, -3.8, 7.1, 3.8);
    bodyGrad.addColorStop(0.00, "#8c0b15");
    bodyGrad.addColorStop(0.28, "#d91424");
    bodyGrad.addColorStop(0.54, "#ff3847");
    bodyGrad.addColorStop(0.82, "#d91424");
    bodyGrad.addColorStop(1.00, "#990d18");
    ctx.fillStyle = bodyGrad;
    ctx.beginPath();
    ctx.moveTo(7.15, 0);
    ctx.bezierCurveTo(7.12, -1.65, 6.75, -3.20, 5.45, -3.62);
    ctx.bezierCurveTo(3.95, -3.76, 2.55, -3.40, 1.05, -3.38);
    ctx.bezierCurveTo(-0.55, -3.38, -2.05, -3.82, -3.95, -3.80);
    ctx.bezierCurveTo(-5.75, -3.78, -6.78, -3.15, -7.05, -1.95);
    ctx.lineTo(-7.05, 1.95);
    ctx.bezierCurveTo(-6.78, 3.15, -5.75, 3.78, -3.95, 3.80);
    ctx.bezierCurveTo(-2.05, 3.82, -0.55, 3.38, 1.05, 3.38);
    ctx.bezierCurveTo(2.55, 3.40, 3.95, 3.76, 5.45, 3.62);
    ctx.bezierCurveTo(6.75, 3.20, 7.12, 1.65, 7.15, 0);
    ctx.closePath();
    ctx.fill();

    ctx.strokeStyle = "rgba(255, 255, 255, 0.24)";
    ctx.lineWidth = 0.28;
    ctx.stroke();

    // Carbon side skirts & aerodynamic side mirrors
    ctx.fillStyle = "#141821";
    ctx.fillRect(-2.8, -3.50, 5.6, 0.34);
    ctx.fillRect(-2.8, 3.16, 5.6, 0.34);
    for (const side of [-1, 1]) {
      ctx.fillStyle = "#b8101d";
      ctx.beginPath();
      ctx.ellipse(1.35, side * 3.88, 0.52, 0.28, side * 0.22, 0, Math.PI * 2);
      ctx.fill();
    }

    // 4. Panamericana vertical-slat grille, sculpted V8 bonnet powerdomes & LED headlights
    ctx.fillStyle = "#0e1118";
    ctx.beginPath();
    ctx.roundRect(6.65, -1.95, 0.56, 3.90, 0.28);
    ctx.fill();
    ctx.fillStyle = "#dce3ef";
    for (let gy = -1.55; gy <= 1.551; gy += 0.44) {
      ctx.fillRect(6.72, gy - 0.05, 0.44, 0.10);
    }

    // Bonnet powerdomes, heat-extractor vents & FIA nose crest
    ctx.fillStyle = "rgba(255, 115, 125, 0.34)";
    ctx.beginPath();
    ctx.roundRect(2.15, -0.92, 3.75, 0.48, 0.22);
    ctx.roundRect(2.15, 0.44, 3.75, 0.48, 0.22);
    ctx.fill();
    ctx.fillStyle = "#141821";
    ctx.beginPath();
    ctx.roundRect(3.55, -1.85, 1.45, 0.62, 0.18);
    ctx.roundRect(3.55, 1.23, 1.45, 0.62, 0.18);
    ctx.fill();
    ctx.fillStyle = "rgba(255, 255, 255, 0.88)";
    ctx.beginPath();
    ctx.arc(5.80, 0, 0.42, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = "#00a2ff";
    ctx.beginPath();
    ctx.arc(5.80, 0, 0.22, 0, Math.PI * 2);
    ctx.fill();

    // Angular swept-back LED headlights
    for (const side of [-1, 1]) {
      ctx.fillStyle = "#eef6ff";
      ctx.beginPath();
      ctx.moveTo(6.92, side * 2.32);
      ctx.lineTo(6.22, side * 3.32);
      ctx.lineTo(5.95, side * 2.95);
      ctx.lineTo(6.62, side * 2.08);
      ctx.closePath();
      ctx.fill();
    }

    // 5. Wraparound fastback greenhouse, carbon roof & flashing FIA light bar
    ctx.fillStyle = "#10141d";
    ctx.beginPath();
    ctx.moveTo(2.05, 0);
    ctx.bezierCurveTo(1.98, -1.65, 1.45, -2.68, 0.55, -2.72);
    ctx.lineTo(-2.35, -2.52);
    ctx.bezierCurveTo(-3.65, -2.42, -4.65, -1.85, -5.05, 0);
    ctx.bezierCurveTo(-4.65, 1.85, -3.65, 2.42, -2.35, 2.52);
    ctx.lineTo(0.55, 2.72);
    ctx.bezierCurveTo(1.45, 2.68, 1.98, 1.65, 2.05, 0);
    ctx.closePath();
    ctx.fill();

    // Windshield glossy tint & carbon coupe roof panel
    ctx.fillStyle = "#1c2434";
    ctx.beginPath();
    ctx.moveTo(1.88, 0);
    ctx.bezierCurveTo(1.80, -1.42, 1.32, -2.36, 0.55, -2.42);
    ctx.lineTo(-0.08, -2.26);
    ctx.lineTo(-0.08, 2.26);
    ctx.lineTo(0.55, 2.42);
    ctx.bezierCurveTo(1.32, 2.36, 1.80, 1.42, 1.88, 0);
    ctx.closePath();
    ctx.fill();

    ctx.fillStyle = "#141821";
    ctx.beginPath();
    ctx.roundRect(-2.15, -2.18, 2.15, 4.36, 0.45);
    ctx.fill();

    // Fastback rear hatch glass
    ctx.fillStyle = "#182030";
    ctx.beginPath();
    ctx.moveTo(-2.25, -2.02);
    ctx.lineTo(-4.72, -1.35);
    ctx.quadraticCurveTo(-4.95, 0, -4.72, 1.35);
    ctx.lineTo(-2.25, 2.02);
    ctx.closePath();
    ctx.fill();

    // FIA Roof Light Bar Pod with alternating amber/orange/green LEDs & glow
    const flash = Math.floor(now / 95) % 2 === 0;
    const glowGrad = ctx.createRadialGradient(-0.7, 0, 0.5, -0.7, 0, 5.2);
    glowGrad.addColorStop(0, "rgba(255, 196, 0, 0.30)");
    glowGrad.addColorStop(1, "rgba(255, 196, 0, 0)");
    ctx.fillStyle = glowGrad;
    ctx.beginPath();
    ctx.arc(-0.7, 0, 5.2, 0, Math.PI * 2);
    ctx.fill();

    ctx.fillStyle = "#171c26";
    ctx.beginPath();
    ctx.roundRect(-1.25, -3.00, 1.10, 6.00, 0.40);
    ctx.fill();
    ctx.fillStyle = flash ? "#ffd000" : "#ff6a00";
    ctx.fillRect(-1.08, -2.85, 0.76, 1.95);
    ctx.fillStyle = flash ? "#ff6a00" : "#ffd000";
    ctx.fillRect(-1.08, 0.90, 0.76, 1.95);
    ctx.fillStyle = flash ? "#00e676" : "#fff7cc";
    ctx.fillRect(-1.05, -0.75, 0.70, 1.50);

    // 6. Slim LED taillights & fixed swan-neck carbon GT rear wing
    for (const side of [-1, 1]) {
      ctx.fillStyle = "#ff2a36";
      ctx.beginPath();
      ctx.roundRect(-7.05, side * 2.25 - 0.85, 0.35, 1.70, 0.14);
      ctx.fill();
    }

    // Swan-neck wing pylons & carbon airfoil
    ctx.fillStyle = "#151924";
    ctx.fillRect(-6.45, -1.35, 1.15, 0.28);
    ctx.fillRect(-6.45, 1.07, 1.15, 0.28);
    ctx.fillStyle = "#11141c";
    ctx.beginPath();
    ctx.roundRect(-6.85, -3.55, 1.00, 7.10, 0.22);
    ctx.fill();
    ctx.fillStyle = "#2b3242";
    ctx.fillRect(-6.92, -3.65, 1.25, 0.24);
    ctx.fillRect(-6.92, 3.41, 1.25, 0.24);

    ctx.restore();

    ctx.save();
    ctx.font = "800 7.5px 'Titillium Web', Inter, sans-serif";
    ctx.fillStyle = "#ffd000";
    ctx.textAlign = "center";
    ctx.fillText("SC", sc.cx, sc.cy - 9.0);
    ctx.restore();
  }

  _drawRejoinGhost(ctx, now) {
    if (!this.tick || (this.tick.phase !== "RACE" && this.tick.phase !== "SPRINT_RACE")) return;
    const cars = this.tick.cars || [];
    let target = cars.find((c) => c.id === this.selectedDriverId && !c.dnf && c.rejoin_x != null);
    if (!target) {
      target = cars.find((c) => c.tid === this.tick.player_team_id && !c.dnf && c.rejoin_x != null);
    }
    if (!target || target.in_pit) return;

    const gx = target.rejoin_x;
    const gy = target.rejoin_y;
    const traf = target.rejoin_traffic_s != null ? target.rejoin_traffic_s : 5.0;
    const col = traf < 1.2 ? "#ff3b30" : traf < 2.2 ? "#ffd000" : "#00d2be";
    const pulse = 0.65 + 0.35 * Math.sin(now * 0.006);

    ctx.save();
    ctx.strokeStyle = col;
    ctx.globalAlpha = pulse * 0.85;
    ctx.lineWidth = 1.6 / Math.max(0.35, this._viewTransform.scale);
    ctx.setLineDash([4, 3]);
    ctx.beginPath();
    ctx.arc(gx, gy, 7.5 / Math.max(0.45, this._viewTransform.scale), 0, Math.PI * 2);
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle = col;
    ctx.globalAlpha = 0.32;
    ctx.beginPath();
    ctx.arc(gx, gy, 3.6 / Math.max(0.45, this._viewTransform.scale), 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();

    const { scale, ox, oy } = this._viewTransform;
    const sx = gx * scale + ox;
    const sy = gy * scale + oy;
    const label = `${target.code} REJOIN P${target.rejoin_pos || "?"} ${traf < 2.2 ? `+${traf.toFixed(1)}s` : "CLR"}`;

    ctx.save();
    ctx.translate(-ox / scale, -oy / scale);
    ctx.scale(1 / scale, 1 / scale);
    ctx.font = "800 9.5px 'Titillium Web', Inter, sans-serif";
    const w = ctx.measureText(label).width + 10;
    const h = 15;
    const bx = sx - w * 0.5;
    const by = sy - 22;
    ctx.fillStyle = "rgba(12, 13, 20, 0.92)";
    ctx.beginPath();
    ctx.roundRect(bx, by, w, h, 3);
    ctx.fill();
    ctx.strokeStyle = col;
    ctx.lineWidth = 1.1;
    ctx.stroke();
    ctx.fillStyle = col;
    ctx.textBaseline = "middle";
    ctx.fillText(label, bx + 5, by + h * 0.5 + 0.4);
    ctx.restore();
  }

  _drawSingleCar(ctx, x, y, heading, c, now, steerInterp) {
    const isMyTeam = this.tick && c.tid === this.tick.player_team_id;
    const isSelected = c.id === this.selectedDriverId;
    const liv = c.custom_team
      ? { body: c.tcol, pod: c.tcol, noseTip: c.scol || c.tcol, stripe: c.scol || c.tcol }
      : (TEAM_LIVERY[c.tid] || { body: c.tcol, pod: c.tcol, noseTip: c.tcol, stripe: c.scol });
    const livKey = c.custom_team ? `${c.tid}_${c.tcol}_${c.scol}` : c.tid;
    const viewTransform = ctx.getTransform();
    const pixelScale = Math.max(Math.hypot(viewTransform.a,viewTransform.b),Math.hypot(viewTransform.c,viewTransform.d));
    const surfaces = getCarSurfaces(liv, livKey, c.num, c.dnf, c.comp, c.wear, pixelScale);
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
    const floorBounds = FLOOR_SURFACE_BOUNDS;
    ctx.drawImage(surfaces.floor, floorBounds.x, floorBounds.y, floorBounds.width, floorBounds.height);

    // 3. Carbon Double-Wishbone Suspension Arms, Pushrods & Brake-Duct Aero Scoops
    ctx.strokeStyle = "#181a22";
    ctx.lineWidth = 0.85;
    ctx.beginPath();
    // Front double wishbones & steering track-rod
    ctx.moveTo(5.45, -1.0); ctx.lineTo(frontAxle + 0.15, -frontHub);
    ctx.moveTo(3.45, -1.2); ctx.lineTo(frontAxle - 0.15, -frontHub);
    ctx.moveTo(4.65, -0.95); ctx.lineTo(frontAxle, -frontHub);
    ctx.moveTo(5.45, 1.0);  ctx.lineTo(frontAxle + 0.15, frontHub);
    ctx.moveTo(3.45, 1.2);  ctx.lineTo(frontAxle - 0.15, frontHub);
    ctx.moveTo(4.65, 0.95); ctx.lineTo(frontAxle, frontHub);
    // Rear double wishbones & pullrod
    ctx.moveTo(-4.15, -1.15); ctx.lineTo(rearAxle + 0.12, -rearHub);
    ctx.moveTo(-6.05, -0.92); ctx.lineTo(rearAxle - 0.12, -rearHub);
    ctx.moveTo(-4.15, 1.15);  ctx.lineTo(rearAxle + 0.12, rearHub);
    ctx.moveTo(-6.05, 0.92);  ctx.lineTo(rearAxle - 0.12, rearHub);
    ctx.stroke();

    // Inner carbon brake-duct scoops beside all four upright hubs
    ctx.fillStyle = "#11141c";
    for (const [ax, hb] of [[frontAxle, -frontHub + 0.45], [frontAxle, frontHub - 0.45], [rearAxle, -rearHub + 0.48], [rearAxle, rearHub - 0.48]]) {
      ctx.fillRect(ax - 0.42, hb - 0.22, 0.84, 0.44);
    }

    // 4. Four Sculpted Pirelli F1 Wheels + Wheel-Cover Highlight + Sidewall Rings
    const tyreCol = TIRE_COLORS[c.comp] || "#ffffff";
    const wheelSpecs = [
      [frontAxle,-frontHub,geom.front_tyre_diameter_m*ppm,geom.front_tyre_width_m*ppm,true],
      [frontAxle, frontHub,geom.front_tyre_diameter_m*ppm,geom.front_tyre_width_m*ppm,true],
      [rearAxle,-rearHub,geom.rear_tyre_diameter_m*ppm,geom.rear_tyre_width_m*ppm,false],
      [rearAxle, rearHub,geom.rear_tyre_diameter_m*ppm,geom.rear_tyre_width_m*ppm,false],
    ];
    const steerRad = (steerInterp !== undefined) ? steerInterp : (c.steer || 0.0);
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

      // Subtle glossy inner rim lip & Pirelli compound sidewall bands
      ctx.fillStyle = "rgba(198, 210, 224, 0.20)";
      ctx.fillRect(-ww * 0.28, -wh * 0.11, ww * 0.56, wh * 0.22);
      ctx.fillStyle = tyreCol;
      ctx.fillRect(-ww * 0.36, -wh * .36, ww * 0.72, wh * .12);
      ctx.fillRect(-ww * 0.36, wh * .24, ww * 0.72, wh * .12);
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
    const bodyBounds = BODY_SURFACE_BOUNDS;
    ctx.drawImage(surfaces.body, bodyBounds.x, bodyBounds.y, bodyBounds.width, bodyBounds.height);

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
    ctx.moveTo(8.75, 0);
    ctx.quadraticCurveTo(8.55, -0.82, 8.35, -1.05);
    if (hasLeftDmg) {
      // Jagged fractured carbon edge on damaged left side
      ctx.lineTo(7.6, -lSpan * 0.72);
      ctx.lineTo(7.3, -lSpan);
      ctx.lineTo(6.4, -lSpan * 0.9);
      ctx.lineTo(6.6, -lSpan * 0.5);
    } else {
      ctx.quadraticCurveTo(7.95, -lSpan * 0.62, 7.55, -lSpan);
      ctx.lineTo(6.25, -lSpan);
    }
    ctx.lineTo(7.05, 0);
    if (hasRightDmg) {
      // Jagged fractured carbon edge on damaged right side
      ctx.lineTo(6.6, rSpan * 0.5);
      ctx.lineTo(6.4, rSpan * 0.9);
      ctx.lineTo(7.3, rSpan);
      ctx.lineTo(7.6, rSpan * 0.72);
    } else {
      ctx.lineTo(6.25, rSpan);
      ctx.lineTo(7.55, rSpan);
      ctx.quadraticCurveTo(7.95, rSpan * 0.62, 8.35, 1.05);
      ctx.quadraticCurveTo(8.55, 0.82, 8.75, 0);
    }
    if (hasRightDmg) {
      ctx.lineTo(8.35, 1.05);
      ctx.quadraticCurveTo(8.55, 0.82, 8.75, 0);
    }
    ctx.closePath();
    ctx.fill();

    // Triple stacked carbon flap slot-gap accents (highlights in Straight Active Aero)
    const wingOpacity = ctx.globalAlpha;
    ctx.globalAlpha *= .68;
    ctx.fillStyle = carbonPaint;
    ctx.fill();
    ctx.globalAlpha = wingOpacity;

    // Nose mounting pylons anchoring mainplane
    ctx.fillStyle = "#0e1118";
    ctx.fillRect(7.45, -0.52, 0.85, 0.22);
    ctx.fillRect(7.45, 0.30, 0.85, 0.22);

    ctx.strokeStyle = c.aero === "STRAIGHT" ? "#ffffff" : "rgba(255,255,255,0.28)";
    ctx.lineWidth = c.aero === "STRAIGHT" ? 0.42 : 0.22;
    ctx.beginPath();
    ctx.moveTo(7.15, -lSpan + 0.32);
    ctx.quadraticCurveTo(7.72, -lSpan * 0.35, 7.95, 0);
    ctx.quadraticCurveTo(7.72, rSpan * 0.35, 7.15, rSpan - 0.32);
    ctx.moveTo(6.68, -lSpan + 0.45);
    ctx.quadraticCurveTo(7.32, -lSpan * 0.32, 7.52, 0);
    ctx.quadraticCurveTo(7.32, rSpan * 0.32, 6.68, rSpan - 0.45);
    ctx.stroke();

    // Sculpted outward-flared front wing endplates & corner diveplanes (or composite shards if broken)
    ctx.fillStyle = liv.stripe;
    if (!hasLeftDmg) {
      ctx.fillRect(6.15, -lSpan - 0.26, 1.65, 0.42);
      ctx.fillStyle = "#11151d";
      ctx.fillRect(6.45, -lSpan - 0.38, 0.95, 0.16);
    } else {
      ctx.fillStyle = "#111216";
      const fl = Math.sin(now * 0.035 + c.num) * 0.25;
      ctx.fillRect(6.3, -lSpan - 0.15 + fl, 0.6, 0.3);
    }
    ctx.fillStyle = liv.stripe;
    if (!hasRightDmg) {
      ctx.fillRect(6.15, rSpan - 0.16, 1.65, 0.42);
      ctx.fillStyle = "#11151d";
      ctx.fillRect(6.45, rSpan + 0.22, 0.95, 0.16);
    } else {
      ctx.fillStyle = "#111216";
      const fl = Math.cos(now * 0.035 + c.num) * 0.25;
      ctx.fillRect(6.3, rSpan - 0.15 + fl, 0.6, 0.3);
    }

    // 8. Cockpit Opening, HANS Suit Shoulders, Roll-Hoop T-Cam, Helmet & Titanium Halo
    ctx.strokeStyle = "#1e2430";
    ctx.lineWidth = 0.22;
    ctx.fillStyle = "#06070a";
    ctx.beginPath();
    ctx.ellipse(-0.3, 0, 2.08, 1.00, 0, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();

    // Driver flame-retardant race suit shoulders inside cockpit tub
    ctx.fillStyle = c.dnf ? "#323742" : (c.tcol || "#182030");
    ctx.beginPath();
    ctx.ellipse(-0.75, 0, 0.72, 0.78, 0, 0, Math.PI * 2);
    ctx.fill();

    // Roll-hoop airbox intake + FIA Broadcast T-Cam pod above roll-hoop
    ctx.fillStyle = "#050608";
    ctx.fillRect(-2.45, -0.56, 0.90, 1.12);
    ctx.fillStyle = "#161a24";
    ctx.fillRect(-2.42, -0.18, 0.38, 0.36);
    ctx.fillStyle = (c.num % 2 === 0) ? "#e5e7eb" : "#ffd200";
    ctx.fillRect(-2.34, -0.78, 0.22, 1.56);

    // Driver Helmet + Crown Accent Stripe + Glossy Reflective Visor
    ctx.fillStyle = c.helm;
    ctx.beginPath();
    ctx.arc(-0.32, 0, 0.88, 0, Math.PI * 2);
    ctx.fill();
    ctx.strokeStyle = liv.stripe;
    ctx.lineWidth = 0.18;
    ctx.beginPath();
    ctx.moveTo(-0.98, 0);
    ctx.lineTo(0.18, 0);
    ctx.stroke();
    ctx.fillStyle = "rgba(255,255,255,.35)";
    ctx.beginPath();
    ctx.ellipse(-0.56, -0.30, 0.38, 0.18, -0.35, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = "#111318";
    ctx.beginPath();
    ctx.arc(-0.04, 0, 0.56, -0.92, 0.92);
    ctx.fill();

    // 3-Point Titanium Halo Structure with specular highlight
    ctx.strokeStyle = "#2b303c";
    ctx.lineWidth = 0.56;
    ctx.beginPath();
    ctx.moveTo(-1.12, -0.88);
    ctx.quadraticCurveTo(0.86, -0.76, 1.58, 0);
    ctx.quadraticCurveTo(0.86, 0.76, -1.12, 0.88);
    ctx.moveTo(1.58, 0);
    ctx.lineTo(0.45, 0);
    ctx.stroke();
    ctx.strokeStyle = "rgba(205,216,228,.72)";
    ctx.lineWidth = .16;
    ctx.stroke();

    // 9. Lower Carbon Beam Wing, Swan-Neck Pylon & 2026 Multi-Element Active Rear Wing
    ctx.fillStyle = "#12161e";
    ctx.fillRect(-6.85, -2.35, 0.75, 4.70); // Lower beam wing

    ctx.fillStyle = "#0b0d13";
    ctx.fillRect(-8.0, -3.45, 1.85, 6.9); // Rear wing mainplane
    ctx.fillStyle = carbonPaint;
    ctx.fillRect(-8.0,-3.45,1.85,6.9);

    // Central swan-neck DRS actuator pod
    ctx.fillStyle = "#1b202b";
    ctx.fillRect(-7.35, -0.32, 1.35, 0.64);

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
    // Sculpted rear wing endplates with livery outer trim
    ctx.fillStyle = c.tcol;
    ctx.fillRect(-8.15, -3.65, 2.20, 0.44);
    ctx.fillRect(-8.15, 3.21, 2.20, 0.44);
    ctx.fillStyle = liv.stripe;
    ctx.fillRect(-8.10, -3.65, 2.05, 0.14);
    ctx.fillRect(-8.10, 3.51, 2.05, 0.14);

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

  _drawNightAtmosphere(ctx, phase) {
    const b = this.track?.bounds;
    if (!b) return;
    const p = Math.max(0, Math.min(1, phase));
    ctx.save();
    // Twilight warm-to-midnight indigo atmospheric wash over track surface & runoff
    const r = Math.round(28 - p * 22);
    const g = Math.round(16 - p * 4);
    const bl = Math.round(38 - p * 10);
    ctx.fillStyle = `rgba(${r}, ${g}, ${bl}, ${(p * 0.42).toFixed(3)})`;
    ctx.fillRect(b.min_x - 350, b.min_y - 350, (b.max_x - b.min_x) + 700, (b.max_y - b.min_y) + 700);

    // Trackside floodlight illumination pools when darkness sets in
    if (p > 0.25 && this.track?.stations?.length) {
      const step = Math.max(1, Math.floor(this.track.stations.length / 18));
      const glowAlpha = Math.min(0.18, (p - 0.25) * 0.22);
      for (let i = 0; i < this.track.stations.length; i += step) {
        const s = this.track.stations[i];
        const grad = ctx.createRadialGradient(s.x, s.y, 4, s.x, s.y, 58);
        grad.addColorStop(0, `rgba(255, 244, 214, ${glowAlpha.toFixed(3)})`);
        grad.addColorStop(1, "rgba(255, 244, 214, 0)");
        ctx.fillStyle = grad;
        ctx.beginPath();
        ctx.arc(s.x, s.y, 58, 0, Math.PI * 2);
        ctx.fill();
      }
    }
    ctx.restore();
  }

  _drawCarNightLights(ctx, x, y, heading) {
    const geom = this.track?.car_geometry;
    if (!geom) return;
    const ppm = geom.world_units_per_m || 2.0;
    const scaleX = (geom.length_m * ppm) / 17.45;
    const scaleY = (geom.width_m * ppm) / 8.4;
    ctx.save();
    ctx.translate(x, y);
    ctx.rotate(heading);
    ctx.scale(scaleX, scaleY);
    for (const side of [-1, 1]) {
      const cone = ctx.createLinearGradient(7.5, 0, 26, 0);
      cone.addColorStop(0, "rgba(240, 248, 255, 0.28)");
      cone.addColorStop(1, "rgba(240, 248, 255, 0)");
      ctx.fillStyle = cone;
      ctx.beginPath();
      ctx.moveTo(7.5, side * 1.6);
      ctx.lineTo(26, side * 4.8);
      ctx.lineTo(26, side * 0.4);
      ctx.closePath();
      ctx.fill();
    }
    // Bright crimson FIA rain / rear light bloom
    const rearGlow = ctx.createRadialGradient(-8.4, 0, 0.5, -9.2, 0, 5.2);
    rearGlow.addColorStop(0, "rgba(255, 36, 48, 0.65)");
    rearGlow.addColorStop(1, "rgba(255, 36, 48, 0)");
    ctx.fillStyle = rearGlow;
    ctx.beginPath();
    ctx.arc(-9.2, 0, 5.2, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();
  }

  _drawMiniMapPiP(ctx) {
    if (!this.track?.bounds || !this.track?.stations?.length) return;
    const b = this.track.bounds;
    const bw = Math.max(1, b.max_x - b.min_x);
    const bh = Math.max(1, b.max_y - b.min_y);
    const boxW = 166;
    const boxH = 116;
    const pad = 12;
    const x0 = 12;
    const y0 = Math.max(14, this.height - boxH - 12);
    const sc = Math.min((boxW - pad * 2) / bw, (boxH - pad * 2) / bh);
    const cxOff = x0 + (boxW - bw * sc) * 0.5 - b.min_x * sc;
    const cyOff = y0 + (boxH - bh * sc) * 0.5 - b.min_y * sc;

    ctx.save();
    ctx.fillStyle = "rgba(10, 12, 18, 0.82)";
    ctx.fillRect(x0, y0, boxW, boxH);
    ctx.strokeStyle = "rgba(255, 255, 255, 0.16)";
    ctx.lineWidth = 1;
    ctx.strokeRect(x0, y0, boxW, boxH);

    // Track silhouette
    const sts = this.track.stations;
    ctx.beginPath();
    for (let i = 0; i < sts.length; i += 2) {
      const px = sts[i].x * sc + cxOff;
      const py = sts[i].y * sc + cyOff;
      if (i === 0) ctx.moveTo(px, py);
      else ctx.lineTo(px, py);
    }
    ctx.closePath();
    ctx.strokeStyle = "rgba(200, 210, 228, 0.45)";
    ctx.lineWidth = 2.6;
    ctx.stroke();

    // Start/Finish tick
    const sf = sts[0];
    if (sf) {
      ctx.fillStyle = "#ffffff";
      ctx.fillRect(sf.x * sc + cxOff - 2, sf.y * sc + cyOff - 2, 4, 4);
    }

    // All active cars & player rejoin ghost
    if (this.tick?.cars) {
      for (const c of this.tick.cars) {
        if (c.dnf) continue;
        const interp = this.carInterp.get(c.id);
        const wx = interp ? interp.cx : c.x;
        const wy = interp ? interp.cy : c.y;
        const px = wx * sc + cxOff;
        const py = wy * sc + cyOff;
        const isPlayer = c.tid === this.tick.player_team_id;
        ctx.beginPath();
        ctx.arc(px, py, isPlayer ? 3.2 : 2.1, 0, Math.PI * 2);
        ctx.fillStyle = c.tcol || "#ffffff";
        ctx.fill();
        if (isPlayer) {
          ctx.strokeStyle = "#ffffff";
          ctx.lineWidth = 1.1;
          ctx.stroke();
        }
        if (isPlayer && c.rejoin_x != null && c.rejoin_y != null && !c.in_pit) {
          const rx = c.rejoin_x * sc + cxOff;
          const ry = c.rejoin_y * sc + cyOff;
          ctx.strokeStyle = "rgba(0, 210, 190, 0.85)";
          ctx.lineWidth = 1.0;
          ctx.beginPath();
          ctx.arc(rx, ry, 3.0, 0, Math.PI * 2);
          ctx.stroke();
        }
      }
    }
    ctx.fillStyle = "rgba(255,255,255,0.55)";
    ctx.font = "800 9px 'Titillium Web', sans-serif";
    ctx.fillText("TRACK MAP", x0 + 6, y0 + 11);
    ctx.restore();
  }
}
