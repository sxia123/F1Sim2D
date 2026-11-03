# Patch physics and championship with rich team radio transmissions

# 1. Update sim/championship.py
with open('sim/championship.py', 'r', encoding='utf-8') as f:
    champ = f.read()

target1 = 'self._push_event("PIT", f"PIT WALL RADIO ({car.code}): \'Box, box this lap for {car.next_compound} tyres!\'")'
repl1 = 'self._push_event("RADIO", f"PIT WALL RADIO ({car.code}): \'Box, box this lap for {car.next_compound} tyres!\'")'

target2 = 'self._push_event("PIT", f"TEAM ORDERS ({car.team_short}): #{car.number} {car.code} instructed to let teammate pass.")'
repl2 = 'self._push_event("RADIO", f"TEAM ORDERS RADIO ({car.team_short}): #{car.number} {car.code} instructed to let teammate pass.")'

if target1 in champ:
    champ = champ.replace(target1, repl1, 1)
if target2 in champ:
    champ = champ.replace(target2, repl2, 1)

with open('sim/championship.py', 'w', encoding='utf-8', newline='\r\n') as f:
    f.write(champ)
print("Updated championship.py pit wall events to RADIO")

# 2. Update sim/physics.py
with open('sim/physics.py', 'r', encoding='utf-8') as f:
    phys = f.read()

# Pit entry radio
p_target1 = """        if car.box_this_lap and entry_gap <= car.v*dt:
            self._advance_car_progress(car,entry_gap,leader_finished,event_cb)
            car.in_pits = True
            car.pit_phase = "ENTRY"
            car.pit_entry_d = car.d
            car.pit_apron = 0.0
            car.pit_speed_checked = False
            car.box_this_lap = False
            car.overtake_active = False
            car.aero_mode = "CORNER" """

p_repl1 = """        if car.box_this_lap and entry_gap <= car.v*dt:
            self._advance_car_progress(car,entry_gap,leader_finished,event_cb)
            car.in_pits = True
            car.pit_phase = "ENTRY"
            car.pit_entry_d = car.d
            car.pit_apron = 0.0
            car.pit_speed_checked = False
            car.box_this_lap = False
            car.overtake_active = False
            car.aero_mode = "CORNER"
            event_cb("RADIO", f"TEAM RADIO ({car.team_short}): [Engineer to #{car.number} {car.code}] 'Box, box! Pitting this lap for {car.next_compound} tyres.'") """

if p_target1.strip() in phys:
    phys = phys.replace(p_target1.strip(), p_repl1.strip(), 1)
    print("Added pit entry radio")
else:
    print("Warning: p_target1 not found")

# Pit out radio
p_target2 = """                event_cb(
                    "PIT",
                    f"PIT OUT: #{car.number} {car.code} ({car.team_short}) rejoins on {car.compound} ({car.last_pit_duration:.2f}s stationary).",
                )"""

p_repl2 = """                event_cb(
                    "PIT",
                    f"PIT OUT: #{car.number} {car.code} ({car.team_short}) rejoins on {car.compound} ({car.last_pit_duration:.2f}s stationary).",
                )
                if random.random() < 0.70:
                    event_cb(
                        "RADIO",
                        f"TEAM RADIO ({car.team_short}): [Engineer to {car.code}] 'Good stop ({car.last_pit_duration:.1f}s). Watch cold tyres on rejoin.'",
                    )"""

if p_target2 in phys:
    phys = phys.replace(p_target2, p_repl2, 1)
    print("Added pit out radio")
else:
    print("Warning: p_target2 not found")

# Tyre wear radio
p_target3 = """        car.tire_wear = min(0.99, car.tire_wear + km_step * max(0.002, wear_rate))"""
p_repl3 = """        car.tire_wear = min(0.99, car.tire_wear + km_step * max(0.002, wear_rate))
        if car.tire_wear >= 0.65 and not getattr(car, "_radio_tyre_warned", False) and not car.in_pits:
            car._radio_tyre_warned = True
            event_cb("RADIO", f"TEAM RADIO ({car.team_short}): [#{car.number} {car.code}] 'Rear tyres are dropping off, losing traction.'")"""

if p_target3 in phys:
    phys = phys.replace(p_target3, p_repl3, 1)
    print("Added tyre wear radio")
else:
    print("Warning: p_target3 not found")

# Reset tyre wear radio warning on new tyres
p_target4 = """                car.tire_wear = 0.0
                car.tire_age_laps = 0"""
p_repl4 = """                car.tire_wear = 0.0
                car.tire_age_laps = 0
                car._radio_tyre_warned = False"""

if p_target4 in phys:
    phys = phys.replace(p_target4, p_repl4, 1)
    print("Added reset tyre wear radio")
else:
    print("Warning: p_target4 not found")

# Collision radio
p_target5 = """            event_cb(
                "CRASH",
                f"COLLISION AT TURN {turn}! {attacker.code} and {defender.code} tangle â€” {victim.code} spins & carbon debris flies!",
            )"""

# In file it might be utf-8 em dash or â€”
if p_target5 in phys:
    p_repl5 = p_target5 + """
            event_cb("RADIO", f"TEAM RADIO ({victim.team_short}): [#{victim.number} {victim.code}] 'He turned in on me! Front wing is damaged!'")"""
    phys = phys.replace(p_target5, p_repl5, 1)
    print("Added collision radio")
else:
    # Try finding with re
    import re
    m = re.search(r'event_cb\(\s*"CRASH",\s*f"COLLISION AT TURN \{turn\}![^"]+"\s*\)', phys)
    if m:
        matched = m.group(0)
        repl = matched + '\n            event_cb("RADIO", f"TEAM RADIO ({victim.team_short}): [#{victim.number} {victim.code}] \'He turned in on me! Front wing is damaged!\'")'
        phys = phys.replace(matched, repl, 1)
        print("Added collision radio via regex")

# Penalty radio
p_target6 = """        elif verdict == "5S":
            culprit.time_penalty_s += 5
            culprit.penalty_points_season += 1
            culprit.penalty_points_added += 1
            event_cb(
                "PENALTY",
                f"PENALTY: +5s Time Penalty for #{culprit.number} {culprit.code} ({item['reason']} at Turn {turn}).",
            )"""

p_repl6 = """        elif verdict == "5S":
            culprit.time_penalty_s += 5
            culprit.penalty_points_season += 1
            culprit.penalty_points_added += 1
            event_cb(
                "PENALTY",
                f"PENALTY: +5s Time Penalty for #{culprit.number} {culprit.code} ({item['reason']} at Turn {turn}).",
            )
            event_cb(
                "RADIO",
                f"TEAM RADIO ({culprit.team_short}): [Engineer to {culprit.code}] 'Copy, 5-second penalty received. Head down and build the gap.'",
            )"""

if p_target6 in phys:
    phys = phys.replace(p_target6, p_repl6, 1)
    print("Added penalty radio")

with open('sim/physics.py', 'w', encoding='utf-8', newline='\r\n') as f:
    f.write(phys)
print("Successfully patched sim/physics.py with radio calls")

