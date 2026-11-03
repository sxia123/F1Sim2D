from pathlib import Path

p = Path("sim/physics.py")
text = p.read_text(encoding="utf-8")

bad = """                    if 0.001 < time_gap <= 1.000:
                        car.overtake_eligible = True
                        car.drs_eligible = True
                    else:
                        car.overtake_eligible = False
                        car.drs_eligible = False
                else:
                    car.overtake_eligible = False
                    car.drs_eligible = False
                        car.max_battery_mj = 4.0
                else:
                    car.overtake_eligible = False
                    car.max_battery_mj = 4.0"""

good = """                    if 0.001 < time_gap <= 1.000:
                        car.overtake_eligible = True
                        car.drs_eligible = True
                    else:
                        car.overtake_eligible = False
                        car.drs_eligible = False
                else:
                    car.overtake_eligible = False
                    car.drs_eligible = False"""

assert bad in text, "bad block not found"
text = text.replace(bad, good, 1)
p.write_text(text, encoding="utf-8")
print("Fixed sim/physics.py indentation error!")

