from pathlib import Path

# 1. Patch sim/championship.py
p_champ = Path("sim/championship.py")
text = p_champ.read_text(encoding="utf-8")

# Add DRIVER_DEFAULT_CAREER_NUMBERS near top
const_anchor = "def get_season_regulations(year: int) -> dict[str, Any]:"
const_def = """DRIVER_DEFAULT_CAREER_NUMBERS: dict[str, int] = {
    "norris": 4,
    "verstappen": 33,
    "hamilton": 44,
    "leclerc": 16,
    "russell": 63,
    "piastri": 81,
    "sainz": 55,
    "alonso": 14,
    "antonelli": 12,
    "hadjar": 6,
    "lawson": 30,
    "lindblad": 41,
    "gasly": 10,
    "colapinto": 43,
    "hulkenberg": 27,
    "bortoleto": 20,
    "ocon": 31,
    "bearman": 87,
    "albon": 23,
    "stroll": 18,
    "perez": 11,
    "bottas": 77,
    "tsunoda": 22,
    "raikkonen": 7,
    "vettel": 5,
    "senna": 8,
    "lauda": 2,
    "schumacher": 3,
    "fangio": 21,
    "prost": 15,
    "hakkinen": 9,
    "mansell": 28,
}


def get_season_regulations(year: int) -> dict[str, Any]:"""
assert const_anchor in text, "const_anchor not found in championship.py"
text = text.replace(const_anchor, const_def, 1)

# In _enter_off_season, set self.reigning_wdc_id
off_season_anchor = """        champ_drv = wdc[0]
        champ_team = wcc[0]"""
off_season_repl = """        champ_drv = wdc[0]
        champ_team = wcc[0]
        self.reigning_wdc_id = champ_drv["id"]"""
assert off_season_anchor in text, "off_season_anchor not found in championship.py"
text = text.replace(off_season_anchor, off_season_repl, 1)

# In _save_state, save reigning_wdc_id
save_anchor = '"calendar_results": self.calendar_results,'
save_repl = '"calendar_results": self.calendar_results,\n                "reigning_wdc_id": getattr(self, "reigning_wdc_id", ""),'
assert save_anchor in text, "save_anchor not found in championship.py"
text = text.replace(save_anchor, save_repl, 1)

# In _load_state, load reigning_wdc_id
load_anchor = 'self.driver_dnfs = data["driver_dnfs"]'
load_repl = 'self.driver_dnfs = data["driver_dnfs"]\n            self.reigning_wdc_id = data.get("reigning_wdc_id", "")'
assert load_anchor in text, "load_anchor not found in championship.py"
text = text.replace(load_anchor, load_repl, 1)

# In _start_next_season, handle car #1 and funds carry over with +50M/+100M
old_season_start_block = """        prev_year = self.season_year
        next_year = prev_year + 1

        if next_year == 2028:
            # 2028 NEW REGULATIONS: 2.4L V8 Naturally Aspirated + Classic DRS!
            # Top 4 teams start off better (levels 5-8), everyone else randomized (levels 2-5)
            wcc = self.get_wcc_table()
            tmap = self._teams_by_id()
            for rank_idx, row in enumerate(wcc):
                team = tmap[row["id"]]
                for dept in UPGRADE_DEPARTMENTS:
                    if rank_idx == 0:
                        team["upgrades"][dept] = random.choice([7, 8])
                    elif rank_idx == 1:
                        team["upgrades"][dept] = random.choice([6, 7, 8])
                    elif rank_idx == 2:
                        team["upgrades"][dept] = random.choice([6, 7])
                    elif rank_idx == 3:
                        team["upgrades"][dept] = random.choice([5, 6, 7])
                    else:
                        team["upgrades"][dept] = random.randint(2, 5)
            self._push_event(
                "NEWS",
                "FIA 2028 NEW REGULATIONS: Screaming 20,000 RPM 2.4L V8 engines & classic DRS introduced! Top 4 teams lead early development while rival grids are randomized.",
            )
        else:
            # Normal seasons (2026->2027, 2028->2029, 2029->2030, etc.):
            # Keep 100% of car improvements from previous season!
            pass

        self.season_year = next_year
        self.current_round = 1
        self.starting_compounds.clear()
        self._reset_season_tallies()
        reg = self.regulations
        self._push_event("NEWS", f"NEW SEASON {self.season_year} UNDERWAY ({reg['short_name']})! Cars unveiled for Round 1 in Melbourne.")
        self._begin_weekend()
        self._save_state()"""

new_season_start_block = """        prev_year = self.season_year
        next_year = prev_year + 1

        # 1. Award Car #1 to Reigning World Drivers' Champion
        champ_id = getattr(self, "reigning_wdc_id", "")
        if not champ_id and self.hall_of_fame:
            hof_champ_name = self.hall_of_fame[-1].get("wdc_name", "")
            match = next((d for d in self.drivers if d["name"] == hof_champ_name), None)
            if match:
                champ_id = match["id"]
        if not champ_id:
            wdc = self.get_wdc_table()
            if wdc and wdc[0]["points"] > 0:
                champ_id = wdc[0]["id"]

        if champ_id:
            # Revert any driver currently holding #1 who is not the reigning champion
            for d in self.drivers:
                if d.get("number") == 1 and d["id"] != champ_id:
                    d["number"] = DRIVER_DEFAULT_CAREER_NUMBERS.get(
                        d["id"],
                        d.get("career_number", 4 if d["id"] == "norris" else 33),
                    )

            # Assign #1 to the reigning champion
            for d in self.drivers:
                if d["id"] == champ_id:
                    if d.get("number") != 1:
                        d["career_number"] = DRIVER_DEFAULT_CAREER_NUMBERS.get(d["id"], d["number"])
                    d["number"] = 1
                    self._push_event(
                        "CHAMPION",
                        f"CAR #1 AWARDED: Reigning World Champion {d['name']} defends their crown with #1 in {next_year}!",
                    )
                    break

        # 2. Regulations and Car Improvements
        prev_era = get_season_regulations(prev_year)["era_id"]
        next_era = get_season_regulations(next_year)["era_id"]
        is_new_regs = (next_year == 2028 or prev_era != next_era)

        if next_year == 2028:
            # 2028 NEW REGULATIONS: 2.4L V8 Naturally Aspirated + Classic DRS!
            # Top 4 teams start off better (levels 5-8), everyone else randomized (levels 2-5)
            wcc = self.get_wcc_table()
            tmap = self._teams_by_id()
            for rank_idx, row in enumerate(wcc):
                team = tmap[row["id"]]
                for dept in UPGRADE_DEPARTMENTS:
                    if rank_idx == 0:
                        team["upgrades"][dept] = random.choice([7, 8])
                    elif rank_idx == 1:
                        team["upgrades"][dept] = random.choice([6, 7, 8])
                    elif rank_idx == 2:
                        team["upgrades"][dept] = random.choice([6, 7])
                    elif rank_idx == 3:
                        team["upgrades"][dept] = random.choice([5, 6, 7])
                    else:
                        team["upgrades"][dept] = random.randint(2, 5)
            self._push_event(
                "NEWS",
                "FIA 2028 NEW REGULATIONS: Screaming 20,000 RPM 2.4L V8 engines & classic DRS introduced! Top 4 teams lead early development while rival grids are randomized.",
            )
        else:
            # Normal seasons: keep 100% of car improvements from previous season!
            pass

        # 3. Funds Carry Over & Season Start Injections (+50M normal, +100M in new regs)
        funds_bonus_m = 100.0 if is_new_regs else 50.0
        for team in self.teams:
            team["budget_m"] = round(team["budget_m"] + funds_bonus_m, 2)
            if team["id"] == self.player_team_id:
                ledger_label = (
                    f"{next_year} New Regulations Technical R&D Grant"
                    if is_new_regs
                    else f"{next_year} Season Start Budget Allocation"
                )
                self._log_ledger("FUNDS", ledger_label, funds_bonus_m)

        funds_announcement = (
            f"NEW REGULATIONS R&D BOOST: +$100.0M injected into all team budgets for {next_year} ({get_season_regulations(next_year)['short_name']})! Prior season funds fully carried over."
            if is_new_regs
            else f"SEASON START FUNDS: +$50.0M allocated to all team budgets for {next_year}! Prior season funds fully carried over."
        )
        self._push_event("UPGRADE", funds_announcement)

        self.season_year = next_year
        self.current_round = 1
        self.starting_compounds.clear()
        self._reset_season_tallies()
        reg = self.regulations
        self._push_event("NEWS", f"NEW SEASON {self.season_year} UNDERWAY ({reg['short_name']})! Cars unveiled for Round 1 in Melbourne.")
        self._begin_weekend()
        self._save_state()"""

assert old_season_start_block in text, "old_season_start_block not found in championship.py"
text = text.replace(old_season_start_block, new_season_start_block, 1)

p_champ.write_text(text, encoding="utf-8")
print("sim/championship.py successfully patched with funds carryover, season start bonuses, and #1 car allocation!")

# 2. Patch public/app.js
p_app = Path("public/app.js")
text_app = p_app.read_text(encoding="utf-8")

# In renderLeaderboard: highlight car #1 with gold class champ-1
old_lead_num = '<span class="t-num">${c.num}</span>'
new_lead_num = '<span class="t-num ${c.num === 1 ? "champ-1" : ""}">${c.num}</span>'
assert old_lead_num in text_app, "old_lead_num not found in app.js"
text_app = text_app.replace(old_lead_num, new_lead_num)

# In renderDriverDatabase: add WDC #1 badge
old_drv_card_hdr = '<strong>#${d.number} ${d.name}</strong>'
new_drv_card_hdr = '<strong>#${d.number} ${d.name}</strong>${d.number === 1 ? \' <span class="champ-badge">WDC #1</span>\' : ""}'
assert old_drv_card_hdr in text_app, "old_drv_card_hdr not found in app.js"
text_app = text_app.replace(old_drv_card_hdr, new_drv_card_hdr, 1)

p_app.write_text(text_app, encoding="utf-8")
print("public/app.js successfully patched with #1 champion indicators!")

# 3. Patch public/styles.css
p_css = Path("public/styles.css")
text_css = p_css.read_text(encoding="utf-8")

css_add = """
.t-num.champ-1 {
  color: #ffd700;
  font-weight: 900;
  text-shadow: 0 0 6px rgba(255, 215, 0, 0.5);
}

.champ-badge {
  display: inline-block;
  font-size: 9px;
  font-weight: 800;
  letter-spacing: 0.6px;
  color: #111;
  background: linear-gradient(135deg, #ffd700, #ffae00);
  padding: 1px 6px;
  border-radius: 3px;
  margin-left: 6px;
  text-transform: uppercase;
}
"""
if ".champ-badge" not in text_css:
    text_css += css_add
    p_css.write_text(text_css, encoding="utf-8")
    print("public/styles.css successfully patched with champion badge and gold number styles!")
