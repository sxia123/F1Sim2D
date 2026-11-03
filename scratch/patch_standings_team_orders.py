with open("sim/physics.py", "r", encoding="utf-8") as f:
    text = f.read().replace("\r\n", "\n")

target = """        leader = self.standings[0]
        for idx, c in enumerate(self.standings):
            new_p = idx + 1"""

repl = """        leader = self.standings[0]
        for idx, c in enumerate(self.standings):
            new_p = idx + 1
            if c.team_order == "YIELD":
                tm = next((o for o in self.standings if o.team_id == c.team_id and o.driver_id != c.driver_id and not o.dnf), None)
                if tm and tm.total_dist > c.total_dist:
                    c.team_order = "FREE"
                    c.swap_target_id = None
                    tm.swap_pass_id = None"""

assert target in text, "target not found in sim/physics.py"
text = text.replace(target, repl, 1)

with open("sim/physics.py", "w", encoding="utf-8") as f:
    f.write(text)

print("Updated _update_standings with team order completion check.")

