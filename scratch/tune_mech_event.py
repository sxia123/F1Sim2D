with open('sim/physics.py', 'r', encoding='utf-8') as f:
    text = f.read()

t_mech = """            event_cb(
                "CRASH",
                f"MECHANICAL DNF: Smoke from #{car.number} {car.name} ({car.team_short}) near Turn {turn} — {failure}!",
            )"""

r_mech = """            event_cb(
                "RETIREMENT",
                f"MECHANICAL DNF: Smoke from #{car.number} {car.name} ({car.team_short}) near Turn {turn} — {failure}!",
            )"""

# Handle encoding of em-dash if needed
if "f\"MECHANICAL DNF: Smoke from #{car.number}" in text:
    idx = text.find("f\"MECHANICAL DNF: Smoke from #{car.number}")
    # find preceding "CRASH"
    crash_idx = text.rfind('"CRASH"', 0, idx)
    if crash_idx != -1 and (idx - crash_idx) < 50:
        text = text[:crash_idx] + '"RETIREMENT"' + text[crash_idx + len('"CRASH"'):]
        print("Updated MECHANICAL DNF category to RETIREMENT!")

with open('sim/physics.py', 'w', encoding='utf-8') as f:
    f.write(text)

