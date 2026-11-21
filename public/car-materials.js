// Display-only, cached surface artwork in the renderer's existing car coordinates.
// These canvases contain no timing, movement or collision state.
export const CAR_SURFACE_BOUNDS = Object.freeze({ x: -8.5, y: -4.2, width: 18, height: 8.4 });
export const FLOOR_SURFACE_BOUNDS = Object.freeze({ x: -7.1, y: -3.4, width: 10.4, height: 6.8 });
export const BODY_SURFACE_BOUNDS = Object.freeze({ x: -6.9, y: -3.15, width: 16.1, height: 6.3 });
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

function surface(paint, b = CAR_SURFACE_BOUNDS) {
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
    // Sculpted ground-effect Venturi floor with subtle mid-waist coke-bottle curve & rear diffuser edge
    ctx.beginPath();
    ctx.moveTo(3.2, -3.28);
    ctx.lineTo(0.2, -3.22);
    ctx.quadraticCurveTo(-2.6, -3.02, -5.65, -3.14);
    ctx.lineTo(-6.95, -2.22);
    ctx.lineTo(-6.95, 2.22);
    ctx.lineTo(-5.65, 3.14);
    ctx.quadraticCurveTo(-2.6, 3.02, 0.2, 3.22);
    ctx.lineTo(3.2, 3.28);
    ctx.closePath();
    ctx.save(); ctx.clip();
    ctx.drawImage(carbon, -8.5, -4.2, 18, 8.4);
    const shade = ctx.createLinearGradient(0, -3.3, 0, 3.3);
    shade.addColorStop(0, "rgba(128,148,166,.20)");
    shade.addColorStop(.38, "rgba(0,0,0,.22)");
    shade.addColorStop(.5, "rgba(18,22,28,.35)");
    shade.addColorStop(1, "rgba(0,0,0,.68)");
    ctx.fillStyle = shade; ctx.fillRect(-7.0, -3.35, 10.3, 6.7);
    // Central titanium plank glint along centerline underside
    ctx.fillStyle = "rgba(165, 178, 194, 0.14)";
    ctx.fillRect(-6.8, -0.35, 8.4, 0.7);
    ctx.restore();
    ctx.strokeStyle = "#48515c"; ctx.lineWidth = .1; ctx.stroke();
    // Machined metallic floor-edge winglet stays & Venturi strake channels
    ctx.strokeStyle = "rgba(175,186,198,.48)"; ctx.lineWidth = .08;
    ctx.beginPath();
    for (const side of [-1, 1]) {
      ctx.moveTo(2.75, side * 3.10); ctx.lineTo(0.4, side * 3.06);
      ctx.quadraticCurveTo(-2.5, side * 2.86, -5.45, side * 2.98);
      ctx.lineTo(-6.72, side * 2.06);
      // Floor-edge winglet slots
      ctx.moveTo(1.55, side * 2.68); ctx.lineTo(1.05, side * 3.15);
      ctx.moveTo(-0.35, side * 2.60); ctx.lineTo(-0.85, side * 3.00);
      ctx.moveTo(-2.55, side * 2.48); ctx.lineTo(-3.05, side * 2.94);
    }
    ctx.stroke();
    // Rear diffuser vertical fences / tunnels
    ctx.strokeStyle = "#07090d"; ctx.lineWidth = .19;
    ctx.beginPath();
    for (let y = -1.75; y <= 1.75; y += .58) {
      ctx.moveTo(-6.9, y); ctx.lineTo(-4.65, y * .70);
    }
    ctx.stroke();
  }, FLOOR_SURFACE_BOUNDS);
  shared = { floor, carbon };
  return shared;
}

function paintRelief(ctx, top, bottom) {
  const reflection = ctx.createLinearGradient(0, top, 0, bottom);
  reflection.addColorStop(0, "rgba(0,0,0,.48)");
  reflection.addColorStop(.14, "rgba(255,255,255,.32)");
  reflection.addColorStop(.34, "rgba(255,255,255,.07)");
  reflection.addColorStop(.49, "rgba(255,255,255,.22)");
  reflection.addColorStop(.64, "rgba(0,0,0,.09)");
  reflection.addColorStop(1, "rgba(0,0,0,.60)");
  ctx.fillStyle = reflection;
  ctx.fillRect(-7, top, 17, bottom - top);
}

function bodySurface(liv, team, number, retired) {
  return surface(ctx => {
    // 1. Sculpted 2026 coke-bottle sidepods with smooth curved taper
    ctx.beginPath();
    ctx.moveTo(2.4, -1.25);
    ctx.quadraticCurveTo(2.25, -2.95, 0.8, -3.02);
    ctx.quadraticCurveTo(-1.8, -2.95, -4.95, -1.55);
    ctx.lineTo(-5.2, 1.55);
    ctx.quadraticCurveTo(-1.8, 2.95, 0.8, 3.02);
    ctx.quadraticCurveTo(2.25, 2.95, 2.4, 1.25);
    ctx.closePath();
    ctx.fillStyle = retired ? "#444b57" : liv.pod; ctx.fill();
    ctx.save(); ctx.clip();
    paintRelief(ctx, -3.05, 3.05);
    for (const side of [-1, 1]) {
      // Carbon sidepod undercut separating coloured bodywork from Venturi floor
      polygon(ctx, [[1.8,side*2.82],[-1.5,side*2.72],[-4.85,side*1.52],
                    [-4.85,side*1.92],[-1.5,side*3.04],[1.8,side*3.12]]);
      ctx.fillStyle = "#11161d"; ctx.fill();
      ctx.strokeStyle = retired ? "#69717c" : liv.stripe; ctx.lineWidth = .14;
      ctx.beginPath();
      ctx.moveTo(1.55, side * 2.66);
      ctx.quadraticCurveTo(-1.3, side * 2.55, -4.45, side * 1.54);
      ctx.stroke();

      // Overhead downwash sidepod waterslide channel shading
      const gully = ctx.createLinearGradient(0, side * 1.35, 0, side * 2.55);
      gully.addColorStop(0, "rgba(0,0,0,.38)");
      gully.addColorStop(.55, "rgba(0,0,0,.12)");
      gully.addColorStop(1, "rgba(255,255,255,.16)");
      ctx.fillStyle = gully;
      polygon(ctx, [[1.0, side * 1.55], [-4.3, side * 1.15], [-4.4, side * 1.65], [0.7, side * 2.42]]);
      ctx.fill();

      if (!retired) {
        if (team === "mclaren" || team === "haas" || team === "racingbulls") {
          polygon(ctx, [[1.15,side*1.58],[-.4,side*2.44],[-3.9,side*1.75],[-2.7,side*1.45]]);
          ctx.fillStyle = team === "racingbulls" ? "#eaf2ff" : "#10151b"; ctx.fill();
        } else if (team === "redbull") {
          ctx.fillStyle = "#e10600";
          polygon(ctx, [[.95,side*1.65],[-.8,side*2.52],[-3.6,side*1.75],[-2,side*1.45]]); ctx.fill();
          ctx.fillStyle = "#ffd200"; ctx.beginPath(); ctx.ellipse(-.9,side*2.08,.44,.32,0,0,Math.PI*2); ctx.fill();
        } else if (team === "williams" || team === "cadillac" || team === "audi") {
          polygon(ctx, [[1.0,side*2.52],[-.2,side*2.52],[-2.6,side*1.60],[-1.55,side*1.55]]);
          ctx.fillStyle = team === "williams" ? "#dceaff" : liv.stripe; ctx.fill();
        } else if (team === "alpine") {
          polygon(ctx, [[1.2,side*2.58],[0.1,side*2.62],[-2.8,side*1.52],[-1.7,side*1.48]]);
          ctx.fillStyle = "#ff87bc"; ctx.fill();
        } else if (team === "aston") {
          polygon(ctx, [[1.1,side*2.45],[0.2,side*2.48],[-3.2,side*1.58],[-2.5,side*1.50]]);
          ctx.fillStyle = "#cedc00"; ctx.fill();
        } else if (team === "mercedes") {
          polygon(ctx, [[1.1,side*2.48],[0.4,side*2.52],[-3.4,side*1.52],[-2.8,side*1.45]]);
          ctx.fillStyle = "#00d2be"; ctx.fill();
        } else if (team === "ferrari") {
          ctx.fillStyle = "#ffffff";
          ctx.fillRect(-1.8, side * 1.92, 1.5, .26);
          ctx.fillStyle = "#ffd200";
          ctx.fillRect(-1.8, side * 1.72, 1.5, .14);
        } else {
          polygon(ctx, [[0.8,side*2.42],[0.1,side*2.45],[-2.8,side*1.56],[-2.1,side*1.50]]);
          ctx.fillStyle = liv.stripe; ctx.fill();
        }
      }
      // Recessed engine-cover cooling louvre gills
      for (let i = 0; i < 7; i++) {
        const x = -.75 - i * .35, y = side * (1.50 + (6 - i) * .065);
        ctx.strokeStyle = "rgba(0,0,0,.68)"; ctx.lineWidth = .16;
        ctx.beginPath(); ctx.moveTo(x,y); ctx.lineTo(x-.24,y+side*.46); ctx.stroke();
        ctx.strokeStyle = "rgba(255,255,255,.20)"; ctx.lineWidth = .045;
        ctx.beginPath(); ctx.moveTo(x+.08,y); ctx.lineTo(x-.16,y+side*.46); ctx.stroke();
      }
    }
    ctx.restore();

    // 2. Sculpted radiator overbite inlets + aerodynamic carbon wing mirrors
    for (const side of [-1, 1]) {
      ctx.fillStyle = "#070a0d"; ctx.fillRect(1.3, side < 0 ? -2.82 : 1.48, .72, 1.34);
      ctx.fillStyle = "rgba(205,220,232,.46)"; ctx.fillRect(1.94, side < 0 ? -2.76 : 1.53, .09, 1.22);
      // Carbon mirror stalk & streamlined wing mirror pod
      ctx.strokeStyle = "#181d25"; ctx.lineWidth = .22;
      ctx.beginPath(); ctx.moveTo(2.05, side * 1.22); ctx.lineTo(2.22, side * 1.92); ctx.stroke();
      ctx.fillStyle = retired ? "#4b5260" : "#11151c";
      ctx.fillRect(1.92, side < 0 ? -2.26 : 1.74, .64, .52);
      ctx.fillStyle = retired ? "#69717c" : liv.stripe;
      ctx.fillRect(2.44, side < 0 ? -2.22 : 1.78, .12, .44);
    }

    // 3. Monocoque chassis, curved F1 nosecone & tapered engine cover
    ctx.beginPath();
    ctx.moveTo(9.1, 0);
    ctx.quadraticCurveTo(8.7, -.56, 6.9, -.82);
    ctx.quadraticCurveTo(4.0, -1.16, 1.2, -1.36);
    ctx.lineTo(-5.8, -1.02);
    ctx.lineTo(-6.85, -.48);
    ctx.lineTo(-6.85, .48);
    ctx.lineTo(-5.8, 1.02);
    ctx.lineTo(1.2, 1.36);
    ctx.quadraticCurveTo(4.0, 1.16, 6.9, .82);
    ctx.quadraticCurveTo(8.7, .56, 9.1, 0);
    ctx.closePath();
    ctx.fillStyle = retired ? "#545d6b" : liv.body; ctx.fill();
    ctx.save(); ctx.clip();
    paintRelief(ctx, -1.35, 1.35);
    if (!retired) {
      ctx.fillStyle = liv.noseTip;
      ctx.beginPath();
      ctx.moveTo(9.1, 0);
      ctx.quadraticCurveTo(8.3, -.58, 7.05, -.74);
      ctx.lineTo(7.05, .74);
      ctx.quadraticCurveTo(8.3, .58, 9.1, 0);
      ctx.closePath();
      ctx.fill();

      // Engine cover shark-fin dorsal spine & team accents
      ctx.strokeStyle = liv.stripe; ctx.lineWidth = .34;
      ctx.beginPath(); ctx.moveTo(-6.3, 0); ctx.lineTo(-2.1, 0); ctx.stroke();
      if (team === "ferrari") {
        for (const [y, color] of [[-.22,"#008c48"],[-.07,"#ffffff"],[.08,"#d51c31"]]) {
          ctx.fillStyle = color; ctx.fillRect(-5.9, y, 2.5, .15);
        }
      } else if (team === "williams") {
        // Classic Duracell copper roll-hoop battery motif
        ctx.fillStyle = "#d97706";
        ctx.fillRect(-3.55, -.44, 1.05, .88);
        ctx.fillStyle = "#0b0e14";
        ctx.fillRect(-4.35, -.44, .80, .88);
      } else if (team === "mercedes") {
        // Subtle INEOS crimson airbox collar
        ctx.fillStyle = "#e10600";
        ctx.fillRect(-3.1, -.45, .85, .90);
      }
    }
    // Panel seams & specular cockpit shoulder contours
    ctx.strokeStyle = "rgba(255,255,255,.34)"; ctx.lineWidth = .09;
    ctx.beginPath(); ctx.moveTo(-5.8,-.64); ctx.lineTo(-2.4,-.76);
    ctx.moveTo(2.2,-.90); ctx.lineTo(7.0,-.36); ctx.stroke();
    ctx.strokeStyle = "rgba(0,0,0,.48)"; ctx.lineWidth = .08;
    ctx.beginPath(); ctx.moveTo(2.4,-1.04); ctx.lineTo(2.4,1.04);
    ctx.moveTo(-4.9,-.92); ctx.lineTo(-4.9,.92); ctx.stroke();

    // Clear shadowed racing number on nose
    ctx.save(); ctx.translate(6.15, 0); ctx.rotate(Math.PI*.5);
    ctx.font = "900 1.15px Arial, sans-serif"; ctx.textAlign = "center"; ctx.textBaseline = "middle";
    ctx.lineWidth = .18; ctx.strokeStyle = "#0b0f14"; ctx.fillStyle = "#ffffff";
    ctx.strokeText(String(number ?? ""),0,0); ctx.fillText(String(number ?? ""),0,0); ctx.restore();
    ctx.restore();

    // Twin FIA forward nose camera vane pods & flush titanium fasteners
    ctx.fillStyle = "#11151b";
    for (const side of [-1, 1]) {
      ctx.fillRect(5.45, side < 0 ? -1.04 : .74, .65, .30);
    }
    ctx.fillStyle = "rgba(220,228,236,.68)";
    for (const x of [2.5, 3.25]) for (const side of [-1,1]) {
      ctx.beginPath(); ctx.arc(x, side*.90, .055, 0, Math.PI*2); ctx.fill();
    }
  }, BODY_SURFACE_BOUNDS);
}

function rubberSurface(compound, worn) {
  const result = canvas(128,64), ctx = result.getContext("2d");
  const shade = ctx.createLinearGradient(0,0,0,64);
  for (const [stop,color] of [[0,"#05070a"],[.13,"#282e35"],[.36,"#1b2026"],[.58,"#15191f"],[.86,"#0d1015"],[1,"#040608"]]) shade.addColorStop(stop,color);
  ctx.fillStyle = shade; ctx.fillRect(0,0,128,64);
  // Subtle moulded centre contact sheen & marbling on worn tyres
  ctx.fillStyle = worn ? "rgba(188,188,176,.14)" : "rgba(255,255,255,.04)";
  ctx.fillRect(0, 22, 128, 20);
  for (let i = 0; i < 36; i++) {
    ctx.fillStyle = `rgba(184,186,178,${worn ? .15 : .06})`;
    ctx.fillRect((i*37)%118, 8+(i*17)%48, 5+(i%5)*3, .65);
  }
  if (compound === "INTER" || compound === "WET") {
    ctx.strokeStyle = "#020305"; ctx.lineWidth = compound === "WET" ? 3.2 : 2.1;
    ctx.beginPath();
    for (const y of [17,32,47]) { ctx.moveTo(0,y); ctx.lineTo(128,y); }
    for (let x = -16; x < 144; x += 17) {
      ctx.moveTo(x,3); ctx.lineTo(x+12,23); ctx.moveTo(x+12,41); ctx.lineTo(x,61);
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
  return { floor: scaledSurface(base.floor,Math.ceil(FLOOR_SURFACE_BOUNDS.width * density)), carbon: scaledSurface(base.carbon,width),
    body: scaledSurface(BODY_CACHE.get(key),Math.ceil(BODY_SURFACE_BOUNDS.width * density)),
    rubber: scaledSurface(RUBBER_CACHE.get(rubberKey),tyreWidth) };
}
