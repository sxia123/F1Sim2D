import copy
import re

with open('sim/championship.py', 'r', encoding='utf-8') as f:
    code = f.read()

target = """            self.drivers = data["drivers"]
            self.driver_points = data["driver_points"]
            self.driver_wins = data["driver_wins"]
            self.driver_podiums = data["driver_podiums"]
            self.driver_poles = data["driver_poles"]
            self.driver_dnfs = data["driver_dnfs"]"""

replacement = """            self.drivers = data["drivers"]
            self.driver_points = data["driver_points"]
            self.driver_wins = data["driver_wins"]
            self.driver_podiums = data["driver_podiums"]
            self.driver_poles = data["driver_poles"]
            self.driver_dnfs = data["driver_dnfs"]

            # Seamlessly sync any new or legendary drivers from INITIAL_DRIVERS
            existing_ids = {d["id"]: d for d in self.drivers}
            for init_d in INITIAL_DRIVERS:
                did = init_d["id"]
                if did not in existing_ids:
                    self.drivers.append(copy.deepcopy(init_d))
                else:
                    if init_d.get("legend"):
                        existing_ids[did]["legend"] = True
                    if did == "bortoleto" and existing_ids[did].get("number") == 5:
                        existing_ids[did]["number"] = 20
                    if did == "doohan" and existing_ids[did].get("number") == 7:
                        existing_ids[did]["number"] = 17

                if did not in self.driver_points:
                    self.driver_points[did] = 0
                if did not in self.driver_wins:
                    self.driver_wins[did] = 0
                if did not in self.driver_podiums:
                    self.driver_podiums[did] = 0
                if did not in self.driver_poles:
                    self.driver_poles[did] = 0
                if did not in self.driver_dnfs:
                    self.driver_dnfs[did] = 0"""

assert target in code, "Target not found in sim/championship.py"
new_code = code.replace(target, replacement, 1)

with open('sim/championship.py', 'w', encoding='utf-8', newline='\r\n') as f:
    f.write(new_code)

print("Successfully updated sim/championship.py")

