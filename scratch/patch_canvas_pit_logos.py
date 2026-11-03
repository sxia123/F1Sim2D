# Patch public/canvas.js to render team logos in pit stalls on each map

with open('public/canvas.js', 'r', encoding='utf-8') as f:
    js = f.read()

# 1. Add GARAGE_TEAM_IDS and GARAGE_TEAM_CODES near top
constants_target = """const TEAM_LIVERY = {"""

constants_repl = """const GARAGE_TEAM_IDS = [
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

const TEAM_LIVERY = {"""

assert constants_target in js, "constants_target not found in canvas.js"
js = js.replace(constants_target, constants_repl, 1)

# 2. Replace pit stall rendering loop with team-branded pit stalls and logos
pit_target = """      // Stall locations are shared with the simulation's team stop coordinates.
      const side=this.track.pit_side||1;
      for(const g of this.track.pit_garages||[]) {
        const nx=-g.ty*side,ny=g.tx*side;
        ctx.save();ctx.translate(g.x+nx*8.6,g.y+ny*8.6);ctx.rotate(Math.atan2(g.ty,g.tx));
        ctx.strokeStyle="rgba(255,255,255,.55)";ctx.lineWidth=.7;
        const geom=this.track.car_geometry,ppm=geom.world_units_per_m;
        const stallLen=(geom.length_m+.8)*ppm,stallWid=(geom.width_m+.4)*ppm;
        ctx.strokeRect(-stallLen/2,-stallWid/2,stallLen,stallWid);ctx.restore();
      }"""

pit_repl = """      // Team Pit Stall locations with Constructor Logos & Gantry Graphics
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
      }"""

assert pit_target in js, "pit_target not found in canvas.js"
js = js.replace(pit_target, pit_repl, 1)

with open('public/canvas.js', 'w', encoding='utf-8', newline='\r\n') as f:
    f.write(js)

print("Successfully updated public/canvas.js with team pit logos and graphics")

