# Patch sim/physics.py to drain battery faster and remove free DRS battery injections

with open('sim/physics.py', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Update RaceSession battery drain logic
target_drain = """        if self.flag_state == "GREEN" and not in_yellow:
            if self.is_braking[st]:
                harvest = 0.42 * dt * (1.0 + (u["power_unit"] - 5) * 0.03)
                car.battery_mj = min(car.max_battery_mj, car.battery_mj + harvest)
                car.recharging = True
            elif car.aero_mode == "STRAIGHT" or smp["curv"] < 0.0065:
                want_overtake = (
                    car.overtake_eligible
                    and car.battery_mj > 0.25
                    and car.ers_mode != "HARVEST"
                    and (gap_ahead_s < 1.35 or car.ers_mode in ("OVERTAKE", "BOOST"))
                )
                want_boost = (
                    not want_overtake
                    and car.battery_mj > 0.55
                    and (
                        car.ers_mode == "BOOST"
                        or (car.ers_mode == "AUTO" and (gap_ahead_s < 0.85 or car.pace_mode in ("PUSH", "ATTACK")))
                    )
                )
                if want_overtake:
                    car.overtake_active = True
                    drain = 0.28 * dt * (1.0 - (u["power_unit"] - 5) * 0.025)
                    car.battery_mj = max(0.0, car.battery_mj - drain)
                elif want_boost:
                    car.boost_active = True
                    drain = 0.22 * dt
                    car.battery_mj = max(0.0, car.battery_mj - drain)
                elif car.ers_mode != "HARVEST" and car.battery_mj > 1.20:
                    # Realistic baseline corner exit and straight-line MGU-K electrical deployment
                    drain = 0.12 * dt
                    car.battery_mj = max(0.0, car.battery_mj - drain)
                elif car.ers_mode == "HARVEST" or car.battery_mj < 0.45:
                    car.recharging = True
                    car.battery_mj = min(car.max_battery_mj, car.battery_mj + 0.16 * dt)"""

repl_drain = """        if self.flag_state == "GREEN" and not in_yellow:
            if self.is_braking[st]:
                harvest = 0.35 * dt * (1.0 + (u["power_unit"] - 5) * 0.03)
                car.battery_mj = min(car.max_battery_mj, car.battery_mj + harvest)
                car.recharging = True
            elif car.aero_mode == "STRAIGHT" or smp["curv"] < 0.0065:
                want_overtake = (
                    car.overtake_eligible
                    and car.battery_mj > 0.18
                    and car.ers_mode != "HARVEST"
                    and (gap_ahead_s < 1.35 or car.ers_mode in ("OVERTAKE", "BOOST"))
                )
                want_boost = (
                    not want_overtake
                    and car.battery_mj > 0.25
                    and (
                        car.ers_mode == "BOOST"
                        or (car.ers_mode == "AUTO" and (gap_ahead_s < 0.85 or car.pace_mode in ("PUSH", "ATTACK")))
                    )
                )
                if want_overtake:
                    car.overtake_active = True
                    # Rapid high-power 350kW active overtake drain (3x faster)
                    drain = 0.85 * dt * (1.0 - (u["power_unit"] - 5) * 0.025)
                    car.battery_mj = max(0.0, car.battery_mj - drain)
                elif want_boost:
                    car.boost_active = True
                    # Fast electrical boost punch (2.5x faster)
                    drain = 0.55 * dt
                    car.battery_mj = max(0.0, car.battery_mj - drain)
                elif car.ers_mode != "HARVEST" and car.battery_mj > 0.35:
                    # Faster baseline straight-line MGU-K electrical deployment (2.3x faster)
                    drain = 0.28 * dt
                    car.battery_mj = max(0.0, car.battery_mj - drain)
                elif car.ers_mode == "HARVEST" or car.battery_mj <= 0.35:
                    car.recharging = True
                    car.battery_mj = min(car.max_battery_mj, car.battery_mj + 0.12 * dt)
            else:
                # Active corner-exit acceleration deployment
                if car.v < target_v and car.ers_mode != "HARVEST" and car.battery_mj > 0.30:
                    corner_drain = (0.24 if car.pace_mode in ("PUSH", "ATTACK") else 0.16) * dt
                    car.battery_mj = max(0.0, car.battery_mj - corner_drain)"""

assert target_drain in text, "target_drain not found in physics.py"
text = text.replace(target_drain, repl_drain, 1)

# 2. Remove free battery injections at DRS zone detection
target_drs1 = """                        if 0.02 < time_gap <= 1.000:
                            car.overtake_eligible = True
                            car.max_battery_mj = 4.5
                            car.battery_mj = min(4.5, car.battery_mj + 0.35)
                        else:
                            car.overtake_eligible = False
                            car.max_battery_mj = 4.0"""

repl_drs1 = """                        if 0.02 < time_gap <= 1.000:
                            car.overtake_eligible = True
                        else:
                            car.overtake_eligible = False"""

assert target_drs1 in text, "target_drs1 not found in physics.py"
text = text.replace(target_drs1, repl_drs1, 1)

target_drs2 = """                    if 0.02 < time_gap <= 1.000:
                        car.overtake_eligible = True
                        car.max_battery_mj = 4.5
                        car.battery_mj = min(4.5, car.battery_mj + 0.35)
                    else:
                        car.overtake_eligible = False
                        car.max_battery_mj = 4.0"""

repl_drs2 = """                    if 0.02 < time_gap <= 1.000:
                        car.overtake_eligible = True
                    else:
                        car.overtake_eligible = False"""

assert target_drs2 in text, "target_drs2 not found in physics.py"
text = text.replace(target_drs2, repl_drs2, 1)

# 3. Update QualifyingSession battery behavior
target_quali_bat = """car.battery_mj = 2.0 + 1.8 * (0.5 + 0.5 * math.sin(self.elapsed * 0.4 + car.number))"""
repl_quali_bat = """lap_progress = (car.s / L)
            car.battery_mj = round(max(0.3, 4.0 - lap_progress * 3.4 + 0.4 * (1.0 - math.cos(lap_progress * math.pi * 4))), 2)"""

assert target_quali_bat in text, "target_quali_bat not found in physics.py"
text = text.replace(target_quali_bat, repl_quali_bat, 1)

with open('sim/physics.py', 'w', encoding='utf-8', newline='\r\n') as f:
    f.write(text)

print("Successfully updated sim/physics.py with faster battery drain physics")

