import sys

with open("public/canvas.js", "r", encoding="utf-8") as f:
    text = f.read()

# 1. Update _render() call order
old_render_calls = """    this._drawTrack(ctx, now);
    this._drawParticles(ctx);
    this._drawCars(ctx, now);"""

new_render_calls = """    this._drawEnvironment(ctx, now);
    this._drawTrack(ctx, now);
    this._drawOverheadEnvironment(ctx, now);
    this._drawParticles(ctx);
    this._drawCars(ctx, now);"""

assert old_render_calls in text, "Could not find old_render_calls in canvas.js"
text = text.replace(old_render_calls, new_render_calls, 1)

# 2. Insert _drawEnvironment and _drawOverheadEnvironment right before _drawTrack
draw_env_code = '''  _drawEnvironment(ctx, now) {
    if (!this.track || !this.track.environment) return;
    const env = this.track.environment;
    const b = this.track.bounds;

    // 1. Terrain Ground Wash (subtle authentic grass, sand, or coastal tone outside driving area)
    if (b) {
      const margin = Math.max(b.max_x - b.min_x, b.max_y - b.min_y) * 0.15;
      const gx = b.min_x - margin;
      const gy = b.min_y - margin;
      const gw = (b.max_x - b.min_x) + margin * 2;
      const gh = (b.max_y - b.min_y) + margin * 2;

      let groundCol = "#0b120c"; // parkland default
      if (env.theme === "forest") groundCol = "#071009";
      else if (env.theme === "desert") groundCol = "#16130d";
      else if (env.theme === "marina" || env.theme === "coastal") groundCol = "#0c1318";
      else if (env.theme === "dunes") groundCol = "#13140d";
      else if (env.theme === "urban") groundCol = "#090a0d";

      ctx.fillStyle = groundCol;
      ctx.fillRect(gx, gy, gw, gh);
    }

    // 2. Corner Gravel Runoff Traps (beneath kerbs and outside heavy-braking areas)
    for (const trap of env.gravel_traps || []) {
      ctx.save();
      ctx.translate(trap.x, trap.y);
      ctx.rotate(trap.angle);
      ctx.fillStyle = "#a8824f";
      ctx.beginPath();
      if (ctx.roundRect) ctx.roundRect(-trap.w * 0.5, -trap.h * 0.5, trap.w, trap.h, 6);
      else ctx.rect(-trap.w * 0.5, -trap.h * 0.5, trap.w, trap.h);
      ctx.fill();
      ctx.strokeStyle = "rgba(70, 50, 25, 0.35)";
      ctx.lineWidth = 1.2;
      ctx.stroke();
      ctx.restore();
    }

    // 3. Water Bodies (Albert Park Lake, Port Hercule, Bassin Olympique, Yas Marina, Red Sea, etc.)
    for (const wb of env.water_bodies || []) {
      ctx.save();
      ctx.shadowColor = "rgba(0, 0, 0, 0.4)";
      ctx.shadowBlur = 8;

      if (wb.type === "polygon" && wb.points && wb.points.length > 2) {
        ctx.beginPath();
        ctx.moveTo(wb.points[0][0], wb.points[0][1]);
        for (let i = 1; i < wb.points.length; i++) {
          ctx.lineTo(wb.points[i][0], wb.points[i][1]);
        }
        ctx.closePath();
      } else if (wb.type === "rect") {
        ctx.beginPath();
        ctx.translate(wb.x, wb.y);
        ctx.rotate(wb.angle || 0);
        ctx.rect(-wb.w * 0.5, -wb.h * 0.5, wb.w, wb.h);
      } else if (wb.type === "circle") {
        ctx.beginPath();
        ctx.arc(wb.x, wb.y, wb.r, 0, Math.PI * 2);
      }

      // Rich azure / deep cyan water body fill
      ctx.fillStyle = "#035388";
      ctx.fill();
      ctx.strokeStyle = "rgba(255, 255, 255, 0.28)";
      ctx.lineWidth = 2.0;
      ctx.stroke();
      ctx.shadowBlur = 0;

      // Animated Water Glisten / Sunlight Wave Ripples
      const ripplePhase = now * 0.0018;
      ctx.strokeStyle = "rgba(180, 235, 255, 0.10)";
      ctx.lineWidth = 1.8;
      if (wb.points && wb.points.length > 2) {
        const p0 = wb.points[0];
        for (let k = 1; k < wb.points.length - 1; k += 2) {
          const pk = wb.points[k];
          ctx.beginPath();
          const waveOff = Math.sin(ripplePhase + k * 1.5) * 6.0;
          ctx.moveTo(p0[0] + waveOff, p0[1]);
          ctx.quadraticCurveTo((p0[0] + pk[0]) * 0.5, (p0[1] + pk[1]) * 0.5 + waveOff * 1.5, pk[0], pk[1]);
          ctx.stroke();
        }
      }
      ctx.restore();
    }

    // 4. Marina Yachts & Luxury Boats (Monaco, Miami, Yas Marina, Singapore)
    for (const y of env.yachts || []) {
      ctx.save();
      ctx.translate(y.x, y.y);
      ctx.rotate(y.angle || 0);
      // Water shadow
      ctx.fillStyle = "rgba(0, 15, 35, 0.45)";
      ctx.beginPath();
      ctx.ellipse(1.5, 2.5, y.len * 0.5, y.width * 0.55, 0, 0, Math.PI * 2);
      ctx.fill();
      // White yacht hull with pointed bow
      ctx.fillStyle = "#f8fafc";
      ctx.beginPath();
      ctx.moveTo(-y.len * 0.48, -y.width * 0.44);
      ctx.lineTo(y.len * 0.24, -y.width * 0.44);
      ctx.lineTo(y.len * 0.52, 0);
      ctx.lineTo(y.len * 0.24, y.width * 0.44);
      ctx.lineTo(-y.len * 0.48, y.width * 0.44);
      ctx.closePath();
      ctx.fill();
      ctx.strokeStyle = "#cbd5e1";
      ctx.lineWidth = 0.8;
      ctx.stroke();
      // Teak wood deck
      ctx.fillStyle = "#d97706";
      ctx.fillRect(-y.len * 0.38, -y.width * 0.28, y.len * 0.52, y.width * 0.56);
      // Tinted blue glass cabin
      ctx.fillStyle = "#0284c7";
      ctx.fillRect(-y.len * 0.15, -y.width * 0.22, y.len * 0.34, y.width * 0.44);
      ctx.restore();
    }

    // 5. Paddock & Hospitality Buildings
    for (const b of env.buildings || []) {
      ctx.save();
      ctx.translate(b.x, b.y);
      ctx.rotate(b.angle || 0);
      // Ambient drop shadow
      ctx.fillStyle = "rgba(0, 0, 0, 0.42)";
      ctx.fillRect(-b.w * 0.5 + 4, -b.h * 0.5 + 4, b.w, b.h);
      // Architectural roof structure
      ctx.fillStyle = b.roof_color || "#334155";
      ctx.fillRect(-b.w * 0.5, -b.h * 0.5, b.w, b.h);
      ctx.strokeStyle = "#475569";
      ctx.lineWidth = 1.0;
      ctx.strokeRect(-b.w * 0.5, -b.h * 0.5, b.w, b.h);
      // Glass atrium / skylight ribbons
      ctx.fillStyle = "rgba(56, 189, 248, 0.45)";
      ctx.fillRect(-b.w * 0.38, -b.h * 0.22, b.w * 0.76, b.h * 0.44);
      ctx.restore();
    }

    // 6. Spectator Grandstands (Stepped bleachers with crowd colors)
    for (const gs of env.grandstands || []) {
      ctx.save();
      ctx.translate(gs.x, gs.y);
      ctx.rotate(gs.angle || 0);
      ctx.fillStyle = "#1e293b";
      ctx.fillRect(-gs.len * 0.5, -gs.depth * 0.5, gs.len, gs.depth);
      ctx.strokeStyle = "#475569";
      ctx.lineWidth = 0.8;
      ctx.strokeRect(-gs.len * 0.5, -gs.depth * 0.5, gs.len, gs.depth);
      // Tiered rows with colorful spectator clusters
      const rows = 4;
      const rowH = gs.depth / (rows + 1);
      const cols = ["#ef4444", "#3b82f6", "#eab308", "#ffffff", "#10b981"];
      for (let r = 0; r < rows; r++) {
        const ry = -gs.depth * 0.5 + (r + 0.5) * rowH;
        ctx.fillStyle = "rgba(255, 255, 255, 0.08)";
        ctx.fillRect(-gs.len * 0.46, ry, gs.len * 0.92, rowH * 0.85);
        for (let s = -gs.len * 0.42; s < gs.len * 0.42; s += 5.5) {
          ctx.fillStyle = cols[Math.abs(Math.floor(s * 7 + r * 13)) % cols.length];
          ctx.beginPath();
          ctx.arc(s, ry + rowH * 0.4, 0.9, 0, Math.PI * 2);
          ctx.fill();
        }
      }
      // Rear canopy roof
      if (gs.canopy) {
        ctx.fillStyle = gs.roof_color || "#dc2626";
        ctx.fillRect(-gs.len * 0.5, -gs.depth * 0.5, gs.len, gs.depth * 0.42);
        ctx.strokeStyle = "rgba(255, 255, 255, 0.35)";
        ctx.lineWidth = 0.8;
        ctx.strokeRect(-gs.len * 0.5, -gs.depth * 0.5, gs.len, gs.depth * 0.42);
      }
      ctx.restore();
    }

    // 7. Trees & Palms (Safe distance from asphalt driving space)
    for (const tr of env.trees || []) {
      ctx.save();
      ctx.translate(tr.x, tr.y);
      ctx.fillStyle = "rgba(0, 0, 0, 0.38)";
      ctx.beginPath();
      ctx.arc(tr.r * 0.28, tr.r * 0.35, tr.r * 0.92, 0, Math.PI * 2);
      ctx.fill();

      if (tr.type === "palm") {
        ctx.fillStyle = "#78350f";
        ctx.beginPath();
        ctx.arc(0, 0, tr.r * 0.22, 0, Math.PI * 2);
        ctx.fill();
        ctx.strokeStyle = tr.shade === 0 ? "#15803d" : tr.shade === 1 ? "#166534" : "#22c55e";
        ctx.lineWidth = Math.max(1.4, tr.r * 0.24);
        ctx.lineCap = "round";
        for (let a = 0; a < 8; a++) {
          const ang = (a / 8) * Math.PI * 2 + 0.2;
          ctx.beginPath();
          ctx.moveTo(0, 0);
          ctx.lineTo(Math.cos(ang) * tr.r, Math.sin(ang) * tr.r);
          ctx.stroke();
        }
      } else if (tr.type === "pine") {
        ctx.fillStyle = tr.shade === 0 ? "#143622" : tr.shade === 1 ? "#0f2e1c" : "#1b4d2e";
        ctx.beginPath();
        ctx.arc(0, 0, tr.r * 0.95, 0, Math.PI * 2);
        ctx.fill();
        ctx.fillStyle = "rgba(74, 222, 128, 0.25)";
        ctx.beginPath();
        ctx.arc(-tr.r * 0.22, -tr.r * 0.22, tr.r * 0.55, 0, Math.PI * 2);
        ctx.fill();
      } else {
        const darkCol = tr.shade === 0 ? "#1b4332" : tr.shade === 1 ? "#133827" : "#204e38";
        const lightCol = tr.shade === 0 ? "#2d6a4f" : tr.shade === 1 ? "#245c43" : "#387a5c";
        ctx.fillStyle = darkCol;
        ctx.beginPath();
        ctx.arc(0, 0, tr.r, 0, Math.PI * 2);
        ctx.fill();
        ctx.fillStyle = lightCol;
        ctx.beginPath();
        ctx.arc(-tr.r * 0.25, -tr.r * 0.28, tr.r * 0.65, 0, Math.PI * 2);
        ctx.fill();
      }
      ctx.restore();
    }
  }

  _drawOverheadEnvironment(ctx, now) {
    if (!this.track || !this.track.environment) return;
    const env = this.track.environment;

    for (const lm of env.landmarks || []) {
      ctx.save();
      ctx.translate(lm.x, lm.y);

      if (lm.type === "ferris_wheel") {
        const r = lm.radius || 45.0;
        const rot = now * 0.00035;
        ctx.strokeStyle = "#e10600";
        ctx.lineWidth = 2.2;
        ctx.beginPath();
        ctx.arc(0, 0, r, 0, Math.PI * 2);
        ctx.stroke();
        ctx.strokeStyle = "#ffffff";
        ctx.lineWidth = 1.0;
        ctx.beginPath();
        ctx.arc(0, 0, r * 0.72, 0, Math.PI * 2);
        ctx.stroke();
        for (let i = 0; i < 16; i++) {
          const a = rot + (i / 16) * Math.PI * 2;
          const gx = Math.cos(a) * r;
          const gy = Math.sin(a) * r;
          ctx.strokeStyle = "rgba(255, 255, 255, 0.45)";
          ctx.lineWidth = 0.8;
          ctx.beginPath();
          ctx.moveTo(0, 0);
          ctx.lineTo(gx, gy);
          ctx.stroke();
          ctx.fillStyle = i % 2 === 0 ? "#ffd000" : "#00d2be";
          ctx.beginPath();
          ctx.arc(gx, gy, 2.2, 0, Math.PI * 2);
          ctx.fill();
        }
        ctx.fillStyle = "#ffffff";
        ctx.beginPath();
        ctx.arc(0, 0, 4.5, 0, Math.PI * 2);
        ctx.fill();
      } else if (lm.type === "biosphere") {
        const r = lm.radius || 42.0;
        ctx.fillStyle = "rgba(14, 165, 233, 0.22)";
        ctx.beginPath();
        ctx.arc(0, 0, r, 0, Math.PI * 2);
        ctx.fill();
        ctx.strokeStyle = "#38bdf8";
        ctx.lineWidth = 1.2;
        ctx.stroke();
        for (let i = 1; i <= 3; i++) {
          ctx.beginPath();
          ctx.arc(0, 0, r * (i / 3.5), 0, Math.PI * 2);
          ctx.strokeStyle = "rgba(56, 189, 248, 0.45)";
          ctx.stroke();
        }
      } else if (lm.type === "sphere") {
        const r = lm.radius || 68.0;
        const pulse = 0.5 + 0.5 * Math.sin(now * 0.002);
        ctx.fillStyle = "#020617";
        ctx.beginPath();
        ctx.arc(0, 0, r, 0, Math.PI * 2);
        ctx.fill();
        ctx.strokeStyle = `rgba(168, 85, 247, ${0.4 + 0.4 * pulse})`;
        ctx.lineWidth = 2.4;
        ctx.stroke();
        for (let i = 1; i <= 4; i++) {
          ctx.beginPath();
          ctx.arc(0, 0, r * (i / 4.5), 0, Math.PI * 2);
          ctx.strokeStyle = i % 2 === 0 ? "rgba(56, 189, 248, 0.5)" : "rgba(236, 72, 153, 0.5)";
          ctx.lineWidth = 1.4;
          ctx.stroke();
        }
      } else if (lm.type === "cota_tower") {
        const r = lm.radius || 24.0;
        ctx.fillStyle = "#dc2626";
        ctx.beginPath();
        ctx.arc(0, 0, r, 0, Math.PI * 2);
        ctx.fill();
        ctx.fillStyle = "#ffffff";
        ctx.beginPath();
        ctx.arc(0, 0, r * 0.45, 0, Math.PI * 2);
        ctx.fill();
      } else if (lm.type === "sakhir_tower") {
        const r = lm.radius || 34.0;
        ctx.fillStyle = "#f8fafc";
        ctx.beginPath();
        ctx.arc(0, 0, r, 0, Math.PI * 2);
        ctx.fill();
        ctx.strokeStyle = "#0284c7";
        ctx.lineWidth = 2.0;
        ctx.stroke();
        ctx.fillStyle = "#0f172a";
        ctx.beginPath();
        ctx.arc(0, 0, r * 0.55, 0, Math.PI * 2);
        ctx.fill();
      }
      ctx.restore();
    }
  }

'''

target_draw_track = "  _drawTrack(ctx, now) {"
assert target_draw_track in text, "Could not find _drawTrack in canvas.js"
text = text.replace(target_draw_track, draw_env_code + target_draw_track, 1)

with open("public/canvas.js", "w", encoding="utf-8") as f:
    f.write(text)

print("Successfully injected _drawEnvironment and _drawOverheadEnvironment into public/canvas.js!")

