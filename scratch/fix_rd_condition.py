from pathlib import Path

p = Path("sim/championship.py")
text = p.read_text(encoding="utf-8")

old = """        # AI rival teams invest surplus budget into R&D upgrades starting from Round 2 onward
        if not (self.season_year == 2026 and self.current_round == 1):
            self._run_ai_rd_upgrades()"""

new = """        # AI rival teams invest surplus budget into R&D upgrades starting from Round 2 onward
        if self.current_round > 1:
            self._run_ai_rd_upgrades()"""

assert old in text, "old not found"
text = text.replace(old, new, 1)
p.write_text(text, encoding="utf-8")
print("Updated AI R&D upgrade trigger to current_round > 1!")

