from pathlib import Path

p = Path("sim/physics.py")
text = p.read_text(encoding="utf-8")

old = """        else:
            car.aero_mode = "CORNER"

        car.overtake_active = False"""

new = """        else:
            car.aero_mode = "CORNER"

        target_v = self.v_env[st] * math.sqrt(grip_mult)

        car.overtake_active = False"""

assert old in text, "old string not found"
text = text.replace(old, new, 1)

# Also remove the duplicate target_v = self.v_env[st] * math.sqrt(grip_mult) at line 1693 if it's there
# Actually reassigning target_v = self.v_env[st] * math.sqrt(grip_mult) at line 1693 resets any baseline before aero modes, which is fine, but keeping it clean:
p.write_text(text, encoding="utf-8")
print("Target v moved earlier successfully!")

