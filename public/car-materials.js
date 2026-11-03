// Display-only, cached surface artwork in the renderer's existing car coordinates.
// These canvases contain no timing, movement, dimensions or collision state.
export const CAR_SURFACE_BOUNDS = Object.freeze({ x: -8.5, y: -4.2, width: 18, height: 8.4 });
const RESOLUTION = 24;
const BODY_CACHE = new Map();
const RUBBER_CACHE = new Map();
const MIP_CACHE = new WeakMap();
const PAINT_CACHE = new WeakMap();
let shared = null;

function canvas(width, height) {
  const result = document.createElement("canvas");
  result.width = width;
  result.height = height;
  return result;
}

function surface(paint) {
  const b = CAR_SURFACE_BOUNDS;
  const result = canvas(Math.ceil(b.width * RESOLUTION), Math.ceil(b.height * RESOLUTION));
  const ctx = result.getContext("2d");
  ctx.scale(RESOLUTION, RESOLUTION);
  ctx.translate(-b.x, -b.y);
  paint(ctx);
  return result;
}

function scaledSurface(master, width) {
  if (width >= master.width) return master;
  let levels = MIP_CACHE.get(master);
  if (!levels) { levels = new Map(); MIP_CACHE.set(master, levels); }
  if (!levels.has(width)) {
    const result = canvas(width, Math.max(1, Math.round(master.height * width / master.width)));
    result.getContext("2d").drawImage(master,0,0,result.width,result.height);
    levels.set(width,result);
  }
  return levels.get(width);
}

export function getCarbonPaint(ctx, source) {
  let paints = PAINT_CACHE.get(ctx);
  if (!paints) { paints = new Map(); PAINT_CACHE.set(ctx,paints); }
  if (!paints.has(source)) {
    const paint = ctx.createPattern(source,"repeat");
    paint.setTransform({a:18/source.width,b:0,c:0,d:8.4/source.height,e:-8.5,f:-4.2});
    paints.set(source,paint);
  }
  return paints.get(source);
}

function polygon(ctx, points) {
  ctx.beginPath();
  ctx.moveTo(...points[0]);
  for (const point of points.slice(1)) ctx.lineTo(...point);
  ctx.closePath();
}

function carbonPattern(ctx) {
  const tile = canvas(32, 32), t = tile.getContext("2d");
  t.fillStyle = "#101419";
  t.fillRect(0, 0, 32, 32);
  for (let row = -1; row < 5; row++) {
    for (let col = -1; col < 5; col++) {
      const x = col * 8, y = row * 8;
      t.fillStyle = (row + col) % 2 ? "#222830" : "#151a21";
      t.fillRect(x, y, 7, 7);
      t.strokeStyle = "rgba(170,185,202,.13)";
      t.lineWidth = 1;
      t.beginPath();
      for (let n = 1; n < 7; n += 2) {
        if ((row + col) % 2) { t.moveTo(x + n, y); t.lineTo(x + n, y + 7); }
        else { t.moveTo(x, y + n); t.lineTo(x + 7, y + n); }
      }
      t.stroke();
    }
  }
  const pattern = ctx.createPattern(tile, "repeat");
  pattern.setTransform({ a: 1 / 32, b: 0, c: 0, d: 1 / 32, e: 0, f: 0 });
  return pattern;
}

function sharedSurfaces() {
  if (shared) return shared;
  const carbon = surface(ctx => {
    ctx.fillStyle = carbonPattern(ctx);
    ctx.fillRect(-8.5, -4.2, 18, 8.4);
  });
  const floor = surface(ctx => {
    polygon(ctx, [[3.2,-3.3],[-5.8,-3.2],[-7,-2.2],[-7,2.2],[-5.8,3.2],[3.2,3.3]]);
    ctx.save(); ctx.clip();
    ctx.drawImage(carbon, -8.5, -4.2, 18, 8.4);
    const shade = ctx.createLinearGradient(0, -3.3, 0, 3.3);
    shade.addColorStop(0, "rgba(110,130,148,.16)");
    shade.addColorStop(.4, "rgba(0,0,0,.2)");
    shade.addColorStop(1, "rgba(0,0,0,.65)");
    ctx.fillStyle = shade; ctx.fillRect(-7,-3.3,11,6.6);
    ctx.restore();
    ctx.strokeStyle = "#414952"; ctx.lineWidth = .1; ctx.stroke();
    // Machined floor edges and diffuser strakes stay inside the old outline.
    ctx.strokeStyle = "rgba(151,161,170,.44)"; ctx.lineWidth = .07;
    ctx.beginPath();
    for (const side of [-1, 1]) {
      ctx.moveTo(2.7, side * 3.13); ctx.lineTo(-5.55, side * 3.02);
      ctx.lineTo(-6.75, side * 2.04);
    }
    ctx.stroke();
    ctx.strokeStyle = "#080b10"; ctx.lineWidth = .18;
    ctx.beginPath();
    for (let y = -1.6; y <= 1.6; y += .64) {
      ctx.moveTo(-6.85, y); ctx.lineTo(-4.7, y * .72);
    }
    ctx.stroke();
  });
  shared = { floor, carbon };
  return shared;
}

function paintRelief(ctx, top, bottom) {
  const reflection = ctx.createLinearGradient(0, top, 0, bottom);
  reflection.addColorStop(0, "rgba(0,0,0,.46)");
  reflection.addColorStop(.15, "rgba(255,255,255,.3)");
  reflection.addColorStop(.34, "rgba(255,255,255,.06)");
  reflection.addColorStop(.48, "rgba(255,255,255,.2)");
  reflection.addColorStop(.62, "rgba(0,0,0,.07)");
  reflection.addColorStop(1, "rgba(0,0,0,.58)");
  ctx.fillStyle = reflection;
  ctx.fillRect(-7, top, 17, bottom - top);
}

function bodySurface(liv, team, number, retired) {
  return surface(ctx => {
    // The body and sidepod outlines match the existing vector car exactly.
    polygon(ctx, [[2.4,-1.3],[1.7,-3.05],[-1.4,-2.95],[-4.8,-1.75],
                  [-4.8,1.75],[-1.4,2.95],[1.7,3.05],[2.4,1.3]]);
    ctx.fillStyle = retired ? "#444b57" : liv.pod; ctx.fill();
    ctx.save(); ctx.clip();
    paintRelief(ctx, -3.05, 3.05);
    for (const side of [-1, 1]) {
      // Carbon undercut separates the coloured pod from its exposed floor.
      polygon(ctx, [[1.8,side*2.85],[-1.5,side*2.78],[-4.65,side*1.72],
                    [-4.65,side*1.95],[-1.5,side*3.04],[1.8,side*3.12]]);
      ctx.fillStyle = "#11161d"; ctx.fill();
      ctx.strokeStyle = retired ? "#69717c" : liv.stripe; ctx.lineWidth = .14;
      ctx.beginPath(); ctx.moveTo(1.5, side * 2.68);
      ctx.lineTo(-1.3, side * 2.6); ctx.lineTo(-4.2, side * 1.72); ctx.stroke();
      if (!retired) {
        // Team-specific panel graphics, rather than a uniform solid fill.
        if (team === "mclaren" || team === "haas" || team === "racingbulls") {
          polygon(ctx, [[1.1,side*1.58],[-.4,side*2.46],[-3.7,side*1.87],[-2.7,side*1.5]]);
          ctx.fillStyle = team === "racingbulls" ? "#eaf2ff" : "#10151b"; ctx.fill();
        } else if (team === "redbull") {
          ctx.fillStyle = "#e10600";
          polygon(ctx, [[.9,side*1.65],[-.8,side*2.55],[-3.5,side*1.85],[-2,side*1.5]]); ctx.fill();
          ctx.fillStyle = "#ffd200"; ctx.beginPath(); ctx.ellipse(-.9,side*2.13,.42,.31,0,0,Math.PI*2); ctx.fill();
        } else if (team === "williams" || team === "cadillac" || team === "audi") {
          polygon(ctx, [[.9,side*2.55],[-.2,side*2.55],[-2.5,side*1.64],[-1.55,side*1.59]]);
          ctx.fillStyle = team === "williams" ? "#dceaff" : liv.stripe; ctx.fill();
        }
      }
      // Recessed cooling louvres and their bevelled leading edges.
      for (let i = 0; i < 6; i++) {
        const x = -.9 - i * .37, y = side * (1.55 + (5 - i) * .07);
        ctx.strokeStyle = "rgba(0,0,0,.65)"; ctx.lineWidth = .17;
        ctx.beginPath(); ctx.moveTo(x,y); ctx.lineTo(x-.25,y+side*.48); ctx.stroke();
        ctx.strokeStyle = "rgba(255,255,255,.18)"; ctx.lineWidth = .045;
        ctx.beginPath(); ctx.moveTo(x+.08,y); ctx.lineTo(x-.17,y+side*.48); ctx.stroke();
      }
    }
    ctx.restore();
    // Deep radiator mouths with a metal lip.
    for (const side of [-1, 1]) {
      ctx.fillStyle = "#070a0d"; ctx.fillRect(1.3, side < 0 ? -2.85 : 1.5, .7, 1.35);
      ctx.fillStyle = "rgba(193,207,217,.4)"; ctx.fillRect(1.91, side < 0 ? -2.8 : 1.55, .08, 1.23);
    }
    polygon(ctx, [[9.1,0],[8.5,-.65],[4,-1.15],[1.2,-1.35],[-5.8,-1.1],[-6.8,-.55],
                  [-6.8,.55],[-5.8,1.1],[1.2,1.35],[4,1.15],[8.5,.65]]);
    ctx.fillStyle = retired ? "#545d6b" : liv.body; ctx.fill();
    ctx.save(); ctx.clip();
    paintRelief(ctx, -1.35, 1.35);
    if (!retired) {
      ctx.fillStyle = liv.noseTip;
      polygon(ctx, [[9.1,0],[7.1,-.72],[7.1,.72]]); ctx.fill();
      ctx.strokeStyle = liv.stripe; ctx.lineWidth = .38;
      ctx.beginPath(); ctx.moveTo(-6.1,0); ctx.lineTo(-2.1,0); ctx.stroke();
      if (team === "ferrari") {
        for (const [y, color] of [[-.22,"#008c48"],[-.07,"#ffffff"],[.08,"#d51c31"]]) {
          ctx.fillStyle = color; ctx.fillRect(-5.8,y,2.4,.15);
        }
      }
    }
    ctx.strokeStyle = "rgba(255,255,255,.32)"; ctx.lineWidth = .09;
    ctx.beginPath(); ctx.moveTo(-5.8,-.68); ctx.lineTo(-2.4,-.8);
    ctx.moveTo(2.2,-.91); ctx.lineTo(7,-.39); ctx.stroke();
    ctx.strokeStyle = "rgba(0,0,0,.45)"; ctx.lineWidth = .08;
    ctx.beginPath(); ctx.moveTo(2.4,-1.05); ctx.lineTo(2.4,1.05);
    ctx.moveTo(-4.9,-.95); ctx.lineTo(-4.9,.95); ctx.stroke();
    // Clear racing numbers, baked once with the livery rather than per frame.
    ctx.save(); ctx.translate(6.2,0); ctx.rotate(Math.PI*.5);
    ctx.font = "900 1.12px Arial, sans-serif"; ctx.textAlign = "center"; ctx.textBaseline = "middle";
    ctx.lineWidth = .16; ctx.strokeStyle = "#10151b"; ctx.fillStyle = "#ffffff";
    ctx.strokeText(String(number ?? ""),0,0); ctx.fillText(String(number ?? ""),0,0); ctx.restore();
    ctx.restore();
    // Flush fasteners on the monocoque shoulders.
    ctx.fillStyle = "rgba(215,222,229,.64)";
    for (const x of [2.5,3.2]) for (const side of [-1,1]) {
      ctx.beginPath(); ctx.arc(x,side*.9,.055,0,Math.PI*2); ctx.fill();
    }
  });
}

function rubberSurface(compound, worn) {
  const result = canvas(128,64), ctx = result.getContext("2d");
  const shade = ctx.createLinearGradient(0,0,0,64);
  for (const [stop,color] of [[0,"#07090c"],[.16,"#272c31"],[.43,"#171b20"],[.7,"#101318"],[1,"#040609"]]) shade.addColorStop(stop,color);
  ctx.fillStyle = shade; ctx.fillRect(0,0,128,64);
  // Stable, deterministic rubber grain: no frame-to-frame random shimmer.
  for (let i = 0; i < 32; i++) {
    ctx.fillStyle = `rgba(181,183,174,${worn ? .13 : .055})`;
    ctx.fillRect((i*37)%119, 8+(i*17)%48, 5+(i%5)*3, .6);
  }
  if (compound === "INTER" || compound === "WET") {
    ctx.strokeStyle = "#020305"; ctx.lineWidth = compound === "WET" ? 3 : 2;
    ctx.beginPath();
    for (const y of [18,32,46]) { ctx.moveTo(0,y); ctx.lineTo(128,y); }
    for (let x = -16; x < 144; x += 18) {
      ctx.moveTo(x,4); ctx.lineTo(x+12,23); ctx.moveTo(x+12,41); ctx.lineTo(x,60);
    }
    ctx.stroke();
  }
  return result;
}

export function getCarSurfaces(livery, team, number, retired, compound, wear, pixelScale = 24) {
  const base = sharedSurfaces();
  const key = [team,number,retired,livery.body,livery.pod,livery.noseTip,livery.stripe].join(":");
  if (!BODY_CACHE.has(key)) {
    if (BODY_CACHE.size >= 64) BODY_CACHE.delete(BODY_CACHE.keys().next().value);
    BODY_CACHE.set(key, bodySurface(livery,team,number,retired));
  }
  const rubberKey = `${compound}:${wear > 60}`;
  if (!RUBBER_CACHE.has(rubberKey)) RUBBER_CACHE.set(rubberKey, rubberSurface(compound,wear > 60));
  // Discrete cached levels avoid filtering full-size textures for tiny cars.
  // Changing zoom creates at most one canvas per level, not one per frame.
  const density = Math.min(24, Math.max(2, 2 ** Math.ceil(Math.log2(Math.max(1,pixelScale)))));
  const width = Math.ceil(CAR_SURFACE_BOUNDS.width * density);
  const tyreWidth = Math.min(128,Math.max(16,2 ** Math.ceil(Math.log2(3 * Math.max(1,pixelScale)))));
  return { floor: scaledSurface(base.floor,width), carbon: scaledSurface(base.carbon,width),
    body: scaledSurface(BODY_CACHE.get(key),width),
    rubber: scaledSurface(RUBBER_CACHE.get(rubberKey),tyreWidth) };
}
