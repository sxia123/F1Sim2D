from pathlib import Path

path = Path("public/canvas.js")
text = path.read_text(encoding="utf-8")

# 1. Update trackside activation line text
old_act = '''          ctx.fillStyle = "#10b981";
          ctx.font = "800 7.0px 'Titillium Web', Inter, sans-serif";
          ctx.fillText("OVT", act.x - act.nx * (detHalf + 4.5) - 7, act.y - act.ny * (detHalf + 4.5) + 2.5);'''

new_act = '''          const isV8 = this.tick && this.tick.regulations && this.tick.regulations.era_id === "V8_DRS";
          ctx.fillStyle = "#10b981";
          ctx.font = "800 7.0px 'Titillium Web', Inter, sans-serif";
          ctx.fillText(isV8 ? "DRS" : "OVT", act.x - act.nx * (detHalf + 4.5) - 7, act.y - act.ny * (detHalf + 4.5) + 2.5);'''

assert old_act in text, "old_act not found in canvas.js"
text = text.replace(old_act, new_act, 1)

# 2. Update rear wing slot opening
old_rw = '''    if ((c.aero === "STRAIGHT" || c.ovt) && !c.dnf) {
      // Open low-drag DRS slot gap profile revealing white leading edge & green DRS status LED
      ctx.fillStyle = "#f0f4f8";
      ctx.fillRect(-7.35, -3.2, 0.65, 6.4);
      ctx.fillStyle = c.ovt ? "#00e676" : "#10b981";
      ctx.fillRect(-6.9, -2.8, 0.4, 5.6);
    } else {'''

new_rw = '''    if ((c.aero === "STRAIGHT" || c.aero === "DRS" || c.ovt || c.drs) && !c.dnf) {
      // Open low-drag DRS slot gap profile revealing white leading edge & green DRS status LED
      ctx.fillStyle = "#f0f4f8";
      ctx.fillRect(-7.35, -3.2, 0.65, 6.4);
      ctx.fillStyle = (c.drs || c.ovt) ? "#00e676" : "#10b981";
      ctx.fillRect(-6.9, -2.8, 0.4, 5.6);
    } else {'''

assert old_rw in text, "old_rw not found in canvas.js"
text = text.replace(old_rw, new_rw, 1)

# 3. Update driver tag DRS / OVT
old_tag = '''      const suffix = c.dnf ? " OUT" : `${c.ovt ? " OVT" : ""}${manShort}${dmgSuffix}${blueSuffix}`;'''
new_tag = '''      const drsOvtTag = (c.drs || c.aero === "DRS") ? " DRS" : (c.ovt ? " OVT" : "");
      const suffix = c.dnf ? " OUT" : `${drsOvtTag}${manShort}${dmgSuffix}${blueSuffix}`;'''

assert old_tag in text, "old_tag not found in canvas.js"
text = text.replace(old_tag, new_tag, 1)

path.write_text(text, encoding="utf-8")
print("Successfully patched public/canvas.js!")

