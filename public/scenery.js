// Static geographic scenery is cached around the camera, then composited below racing.
// The final road mask protects asphalt, kerbs and pit aprons even inside large land polygons.
const GROUND = {
  parkland: "#18271e", forest: "#17281d", desert: "#615039",
  dunes: "#5d5940", urban: "#252b30", marina: "#283d36", coastal: "#454c38",
};
const LAND = {
  wood: "#244632", grass: "#36553a", scrub: "#5c6541", sand: "#aa9767",
  field: "#666947", parking: "#454b4e", pitch: "#486d43",
};

export class SceneryLayer {
  constructor() { this.cache = null; }

  draw(ctx, track, view, width, height, dpr) {
    const env = track.environment;
    if (!env?.revision) return; // An older running server can finish its session safely.
    const { scale, ox, oy } = view;
    const left = -ox / scale, top = -oy / scale;
    const right = left + width / scale, bottom = top + height / scale;
    const key = `${track.id}:${track.geometry_revision}:${env.revision}`;
    let c = this.cache;
    // A generous camera gutter amortizes rebuilding during follow-camera movement.
    if (!c || c.key !== key || left < c.left || top < c.top || right > c.right || bottom > c.bottom ||
        scale / c.viewScale > 1.22 || scale / c.viewScale < .78 || c.dpr !== dpr) {
      const gutter = 240 / scale;
      const x = left - gutter, y = top - gutter;
      const w = right - left + gutter * 2, h = bottom - top + gutter * 2;
      const resolution = Math.min(scale * Math.min(dpr, 2), 3072 / w, 3072 / h);
      const canvas = document.createElement("canvas");
      canvas.width = Math.ceil(w * resolution);
      canvas.height = Math.ceil(h * resolution);
      const rasterW = canvas.width / resolution, rasterH = canvas.height / resolution;
      const off = canvas.getContext("2d");
      off.setTransform(resolution, 0, 0, resolution, -x * resolution, -y * resolution);
      this.paint(off, track, [x, y, x + rasterW, y + rasterH], scale);
      this.maskRoads(off, track);
      c = this.cache = { key, canvas, left: x, top: y, right: x + rasterW, bottom: y + rasterH,
        w: rasterW, h: rasterH, viewScale: scale, dpr };
    }
    ctx.drawImage(c.canvas, c.left, c.top, c.w, c.h);
  }

  path(ctx, paths) {
    ctx.beginPath();
    for (const p of paths) {
      if (!p.length) continue;
      ctx.moveTo(p[0][0], p[0][1]);
      for (let i = 1; i < p.length; i++) ctx.lineTo(p[i][0], p[i][1]);
      ctx.closePath();
    }
  }

  visible(f, view) {
    const b = f.bounds;
    return !b || !(b[2] < view[0] || b[0] > view[2] || b[3] < view[1] || b[1] > view[3]);
  }

  paint(ctx, track, view, scale) {
    const env = track.environment;
    ctx.fillStyle = env.palette?.ground || GROUND[env.theme] || GROUND.parkland;
    ctx.fillRect(view[0], view[1], view[2] - view[0], view[3] - view[1]);
    // Broad land cover precedes smaller pitches, car parks and landscaped grounds.
    const order = { wood: 0, field: 1, scrub: 2, sand: 3, grass: 4, parking: 5, pitch: 6 };
    for (const f of [...(env.terrain || [])].sort((a, b) => order[a.kind] - order[b.kind])) {
      if (!this.visible(f, view)) continue;
      this.path(ctx, f.paths);
      ctx.fillStyle = env.palette?.[f.kind] || LAND[f.kind] || LAND.grass;
      ctx.fill("evenodd");
      ctx.strokeStyle = "#ffffff0c";
      ctx.lineWidth = 2;
      ctx.stroke();
      if (f.kind === "parking" || f.kind === "field" || f.kind === "pitch") {
        ctx.save();
        ctx.clip("evenodd");
        const [x0, y0, x1, y1] = f.bounds;
        ctx.strokeStyle = f.kind === "pitch" ? "#ffffff44" : "#ffffff15";
        ctx.lineWidth = 1.5;
        const spacing = f.kind === "parking" ? 32 : 60;
        for (let y = Math.max(y0, view[1]); y < Math.min(y1, view[3]); y += spacing) {
          ctx.beginPath();ctx.moveTo(Math.max(x0, view[0]), y);ctx.lineTo(Math.min(x1, view[2]), y);ctx.stroke();
          if (f.kind === "parking" && scale > .1) {
            for (let x = Math.max(x0, view[0]); x < Math.min(x1, view[2]); x += 18) {
              ctx.fillStyle = ["#98a5ad", "#323b47", "#b9b9ac", "#865b50"][Math.abs(Math.floor(x / 18 + y / 32)) % 4];
              ctx.fillRect(x + 4, y + 7, 8, 15);
            }
          }
        }
        ctx.restore();
      }
    }

    for (const water of env.water_bodies || []) {
      if (!this.visible(water, view)) continue;
      ctx.save();
      this.path(ctx, water.paths);
      ctx.fillStyle = env.palette?.water || "#226575";
      if (env.palette && water.coastal) {
        const gradient=ctx.createLinearGradient(water.bounds[0],0,water.bounds[2],0);
        gradient.addColorStop(0,"#123b58");gradient.addColorStop(1,"#267e8d");
        ctx.fillStyle=gradient;
      }
      ctx.fill("evenodd");
      ctx.strokeStyle = env.palette?.shoreline || "#7da897";ctx.lineWidth = 5;ctx.stroke();
      ctx.clip("evenodd");
      ctx.strokeStyle = "#9dd6d51c";ctx.lineWidth = 2;
      const [x0, y0, x1, y1] = water.bounds;
      for (let y = Math.max(view[1], y0); y < Math.min(view[3], y1); y += 38) {
        ctx.beginPath();
        for (let x = Math.max(view[0], x0), i = 0; x <= Math.min(view[2], x1); x += 26, i++) {
          const yy = y + Math.sin(x * .025 + y) * 3;
          if (!i) ctx.moveTo(x, yy); else ctx.lineTo(x, yy);
        }
        ctx.stroke();
      }
      ctx.restore();
    }

    // Mapped Corniche boulevards, promenades and marina piers, below buildings/cars.
    for (const route of env.routes || []) {
      if (!this.visible(route,view)) continue;
      ctx.beginPath();ctx.moveTo(...route.points[0]);
      for (let i=1;i<route.points.length;i++) ctx.lineTo(...route.points[i]);
      ctx.lineCap="round";ctx.lineJoin="round";
      ctx.strokeStyle=route.kind==="access_road"?"#8d8775":"#c9bda1";
      ctx.lineWidth=route.width+3;ctx.stroke();
      ctx.strokeStyle=route.kind==="access_road"?"#414950":route.kind==="pier"?"#a99475":"#afab97";
      ctx.lineWidth=route.width;ctx.stroke();
      if (route.kind==="access_road" && route.width>22 && scale>.12) {
        ctx.save();ctx.setLineDash([9,14]);ctx.strokeStyle="#c7c0a45a";
        ctx.lineWidth=1.2;ctx.stroke();ctx.restore();
      }
    }

    for (const f of [...(env.buildings || []), ...(env.grandstands || [])]) {
      if (!this.visible(f, view)) continue;
      const [x0, y0, x1, y1] = f.bounds;
      ctx.save();ctx.translate(5, 6);this.path(ctx, f.paths);
      ctx.fillStyle = "#00000050";ctx.fill("evenodd");ctx.restore();
      this.path(ctx, f.paths);
      ctx.fillStyle = f.roof_color || "#64747b";ctx.fill("evenodd");
      ctx.strokeStyle = f.landmark?"#c1d8d2":"#afbbc080";ctx.lineWidth = f.landmark?2.8:1.6;ctx.stroke();
      ctx.save();ctx.clip("evenodd");
      const stand = f.kind === "grandstand";
      ctx.strokeStyle = stand ? "#d6d8c75a" : "#23374366";ctx.lineWidth = stand ? 3 : 2;
      for (let y = Math.max(y0 + 6, view[1]); y < Math.min(y1, view[3]); y += stand ? 9 : 28) {
        ctx.beginPath();ctx.moveTo(Math.max(x0 + 4, view[0]), y);ctx.lineTo(Math.min(x1 - 4, view[2]), y);ctx.stroke();
        if (stand && scale > .12) {
          for (let x = Math.max(x0 + 6, view[0]); x < Math.min(x1 - 4, view[2]); x += 7) {
            ctx.fillStyle = ["#d4b16a", "#dce4df", "#a64f42", "#5b93a4"][Math.abs(Math.floor(x + y)) % 4];
            ctx.fillRect(x, y, 3, 3);
          }
        }
      }
      // Recognizable mapped major structures retain their actual footprint and location.
      const name = (f.name || "").toLowerCase();
      if (name.includes("sphere")) {
        ctx.fillStyle = "#70638d";
        ctx.beginPath();ctx.ellipse((x0+x1)/2, (y0+y1)/2, (x1-x0)*.42, (y1-y0)*.42, 0, 0, Math.PI*2);ctx.fill();
      }
      if (scale > .22 && f.name && x1 - x0 > 110 && y1 - y0 > 35) {
        ctx.fillStyle = "#f3eee0c0";ctx.font = "600 10px sans-serif";
        ctx.textAlign = "center";ctx.textBaseline = "middle";
        ctx.fillText(f.name.toUpperCase(), (x0 + x1)/2, (y0 + y1)/2, x1 - x0 - 12);
      }
      ctx.restore();
    }

    for (const y of env.yachts || []) {
      if (y.x < view[0]-80 || y.x > view[2]+80 || y.y < view[1]-80 || y.y > view[3]+80) continue;
      ctx.save();ctx.translate(y.x, y.y);ctx.rotate(y.angle);
      ctx.fillStyle = "#e4e6df";
      ctx.beginPath();ctx.moveTo(-y.len*.5, -y.width*.5);ctx.lineTo(y.len*.26, -y.width*.5);
      ctx.lineTo(y.len*.5, 0);ctx.lineTo(y.len*.26, y.width*.5);ctx.lineTo(-y.len*.5, y.width*.5);ctx.closePath();ctx.fill();
      ctx.fillStyle = "#ba9973";ctx.fillRect(-y.len*.4, -y.width*.32, y.len*.6, y.width*.64);
      ctx.fillStyle = "#59828e";ctx.fillRect(-y.len*.12, -y.width*.24, y.len*.32, y.width*.48);ctx.restore();
    }

    for (const t of env.trees || []) {
      if (t.x < view[0]-50 || t.x > view[2]+50 || t.y < view[1]-50 || t.y > view[3]+50) continue;
      ctx.save();ctx.translate(t.x, t.y);ctx.rotate(t.rotation || 0);
      ctx.fillStyle = "#08180f50";ctx.beginPath();ctx.ellipse(t.r*.24, t.r*.3, t.r, t.r*.87, 0, 0, Math.PI*2);ctx.fill();
      if (t.type === "palm") {
        ctx.strokeStyle = ["#4f7951", "#648950", "#427657"][t.shade];
        ctx.lineWidth = t.r*.19;ctx.lineCap = "round";
        for (let i = 0; i < 7; i++) {
          const a = i*Math.PI*2/7;
          ctx.beginPath();ctx.moveTo(0, 0);ctx.quadraticCurveTo(Math.cos(a+.3)*t.r*.7, Math.sin(a+.3)*t.r*.7, Math.cos(a)*t.r, Math.sin(a)*t.r);ctx.stroke();
        }
        ctx.fillStyle = "#c7aa6c";ctx.beginPath();ctx.arc(0, 0, t.r*.12, 0, Math.PI*2);ctx.fill();
      } else {
        ctx.fillStyle = (t.type === "pine" ? ["#234634", "#31573c", "#294d3d"] : ["#467347", "#537b46", "#3d6847"])[t.shade];
        ctx.beginPath();
        for (let i = 0; i < 14; i++) {
          const a = i*Math.PI*2/14, r = t.r*(i % 2 ? .81 : 1);
          if (!i) ctx.moveTo(Math.cos(a)*r, Math.sin(a)*r);else ctx.lineTo(Math.cos(a)*r, Math.sin(a)*r);
        }
        ctx.closePath();ctx.fill();
        ctx.fillStyle = "#a8bb6540";ctx.beginPath();ctx.ellipse(-t.r*.22, -t.r*.2, t.r*.55, t.r*.45, -.4, 0, Math.PI*2);ctx.fill();
      }
      ctx.restore();
    }
    for (const d of env.details || []) {
      if (d.x < view[0] || d.x > view[2] || d.y < view[1] || d.y > view[3]) continue;
      ctx.fillStyle = (d.type === "scrub" ? ["#8f9061", "#aaa078", "#777f52"] : ["#61774a", "#79905b", "#425f3c"])[d.shade];
      ctx.beginPath();ctx.ellipse(d.x, d.y, d.r, d.r*.55, d.shade, 0, Math.PI*2);ctx.fill();
    }
    for (const light of env.lights || []) {
      if (light.x<view[0]-20 || light.x>view[2]+20 || light.y<view[1]-20 || light.y>view[3]+20) continue;
      const glow=ctx.createRadialGradient(light.x,light.y,0,light.x,light.y,light.r);
      glow.addColorStop(0,"#d3edf87a");glow.addColorStop(.35,"#a7d6f132");glow.addColorStop(1,"#a7d6f100");
      ctx.fillStyle=glow;ctx.beginPath();ctx.arc(light.x,light.y,light.r,0,Math.PI*2);ctx.fill();
      ctx.fillStyle="#eff8ed";ctx.beginPath();ctx.arc(light.x,light.y,2.5,0,Math.PI*2);ctx.fill();
    }
  }

  maskRoads(ctx, track) {
    ctx.save();
    ctx.globalCompositeOperation = "destination-out";
    ctx.strokeStyle = "#000";ctx.lineCap = "round";ctx.lineJoin = "round";
    const transform = ctx.getTransform();
    const padding = Math.max(28, 6 / Math.hypot(transform.a, transform.b));
    const sts = track.stations;
    for (let i = 0; i < sts.length; i++) {
      const a = sts[i], b = sts[(i + 1) % sts.length];
      ctx.lineWidth = Math.max(a.width_px || track.track_width_px, b.width_px || track.track_width_px) + padding;
      ctx.beginPath();ctx.moveTo(a.x, a.y);ctx.lineTo(b.x, b.y);ctx.stroke();
    }
    const pit = track.pit_points || [];
    if (pit.length > 1) {
      ctx.lineWidth = (track.pit_width_px || 26) + padding;
      // Separate round capsules avoid tessellation seams on tightly curved pit routes.
      for (let i = 1; i < pit.length; i++) {
        ctx.beginPath();ctx.moveTo(...pit[i - 1]);ctx.lineTo(...pit[i]);ctx.stroke();
      }
    }
    ctx.restore();
  }
}
