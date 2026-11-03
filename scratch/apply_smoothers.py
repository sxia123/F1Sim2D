"""Apply velocity and lateral clamping smoothers to sim/physics.py."""
import pathlib

ROOT = pathlib.Path(r"c:\Coding\F1Sim2D")
phys_file = ROOT / "sim" / "physics.py"
text = phys_file.read_text(encoding="utf-8")

# Fix 1: Lines 231-236 (c.v when deficit > 0)
old_1 = """                    deficit = min_long_m - ds_m
                    if deficit > 0:
                        c.v = max(4.0, max(o.v * 0.98, c.v - 22.0 * 0.05))"""
new_1 = """                    deficit = min_long_m - ds_m
                    if deficit > 0:
                        if c.v > o.v:
                            c.v = max(o.v * 0.98, c.v - 22.0 * 0.05)"""
assert old_1 in text, "old_1 not found"
text = text.replace(old_1, new_1)

# Fix 2: Line 367 (mover.v in longitudinal pit/track push)
old_2 = """                    if sign_dir < 0.0 and not mover.dnf and mover.pit_phase != "STOPPED":
                        mover.v = max(4.0, max(ahead.v * 0.98, mover.v - 22.0 * 0.05))"""
new_2 = """                    if sign_dir < 0.0 and not mover.dnf and mover.pit_phase != "STOPPED":
                        if mover.v > ahead.v:
                            mover.v = max(ahead.v * 0.98, mover.v - 22.0 * 0.05)"""
assert old_2 in text, "old_2 not found"
text = text.replace(old_2, new_2)

# Fix 3: Line 2350 (attacker.v on stout defense)
old_3 = """                    # Attacker eases throttle smoothly without instant deceleration crash
                    attacker.v = max(4.0, max(defender.v * 0.96, attacker.v - 14.0 * dt))"""
new_3 = """                    # Attacker eases throttle smoothly without instant deceleration crash
                    if attacker.v > defender.v * 0.96:
                        attacker.v = max(4.0, attacker.v - 14.0 * dt)"""
assert old_3 in text, "old_3 not found"
text = text.replace(old_3, new_3)

# Fix 4: Lateral separation rate clamping in SAT
old_4 = """                if is_lateral and not ahead.in_pits and not behind.in_pits and not c1_off and not c2_off and allow_passing:
                    need_d = (max(pen_w1, pen_w2) + 0.15) / half_usable"""
new_4 = """                if is_lateral and not ahead.in_pits and not behind.in_pits and not c1_off and not c2_off and allow_passing:
                    need_d = min(0.24, (max(pen_w1, pen_w2) + 0.15) / half_usable)"""
assert old_4 in text, "old_4 not found"
text = text.replace(old_4, new_4)

phys_file.write_text(text, encoding="utf-8")
print("Successfully applied velocity and lateral smoothers to sim/physics.py")

