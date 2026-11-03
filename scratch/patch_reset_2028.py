from pathlib import Path

# 1. Patch sim/championship.py
p_champ = Path("sim/championship.py")
text_champ = p_champ.read_text(encoding="utf-8")

old_init_fresh = """    def _init_fresh_career(self, player_team_id: str = "williams") -> None:
        self.season_year = 2026
        self.current_round = 1
        self.player_team_id = player_team_id
        self.teams, self.drivers = clone_initial_roster()
        for d in self.drivers:
            d.setdefault("penalty_points", 0)
        self._reset_season_tallies()
        self.hall_of_fame = []
        self.ledger = []
        self.event_feed = []
        self._log_ledger("CAREER", "Appointed Team Principal — FIA 2026 Season Budget Allocated", 0.0)
        self._push_event("NEWS", f"WELCOME TO {self.season_year} FORMULA 1! Active Aero, Sprint Calendar & Overtake Mode era begins.")"""

new_init_fresh = """    def _init_fresh_career(self, player_team_id: str = "williams", start_year: int = 2026) -> None:
        self.season_year = 2028 if int(start_year) == 2028 else 2026
        self.current_round = 1
        self.player_team_id = player_team_id
        self.teams, self.drivers = clone_initial_roster()
        self.starting_compounds.clear()

        if self.season_year == 2028:
            # Age drivers by 2 years from 2026 baseline
            for d in self.drivers:
                d["age"] += 2
                d.setdefault("penalty_points", 0)

            # Assign Car #1 to Verstappen as reigning champion, Norris to permanent career #4
            self.reigning_wdc_id = "verstappen"
            ver = next((d for d in self.drivers if d["id"] == "verstappen"), None)
            nor = next((d for d in self.drivers if d["id"] == "norris"), None)
            if ver:
                ver["career_number"] = 33
                ver["number"] = 1
            if nor:
                nor["career_number"] = 4
                nor["number"] = 4

            # 2028 New Regulations: Top 4 teams start off better (levels 5-8), others randomized (levels 2-5)
            # All teams receive +$100.0M new regulations R&D injection
            for t in self.teams:
                tid = t["id"]
                if tid == "mclaren":
                    for dept in UPGRADE_DEPARTMENTS:
                        t["upgrades"][dept] = random.choice([7, 8])
                elif tid == "redbull":
                    for dept in UPGRADE_DEPARTMENTS:
                        t["upgrades"][dept] = random.choice([6, 7, 8])
                elif tid == "ferrari":
                    for dept in UPGRADE_DEPARTMENTS:
                        t["upgrades"][dept] = random.choice([6, 7])
                elif tid == "mercedes":
                    for dept in UPGRADE_DEPARTMENTS:
                        t["upgrades"][dept] = random.choice([5, 6, 7])
                else:
                    for dept in UPGRADE_DEPARTMENTS:
                        t["upgrades"][dept] = random.randint(2, 5)
                t["budget_m"] = round(t["budget_m"] + 100.0, 2)

            self.hall_of_fame = [
                {
                    "season": 2026,
                    "wdc_name": "Lando Norris",
                    "wdc_code": "NOR",
                    "wdc_team": "McLaren",
                    "wdc_points": 412,
                    "wdc_wins": 8,
                    "wcc_name": "McLaren",
                    "wcc_color": "#ff8000",
                    "wcc_points": 724,
                },
                {
                    "season": 2027,
                    "wdc_name": "Max Verstappen",
                    "wdc_code": "VER",
                    "wdc_team": "Red Bull",
                    "wdc_points": 428,
                    "wdc_wins": 9,
                    "wcc_name": "Red Bull Racing",
                    "wcc_color": "#1e41ff",
                    "wcc_points": 710,
                },
            ]
            self.ledger = []
            self.event_feed = []
            self._log_ledger("CAREER", "Appointed Team Principal — FIA 2028 Season Launch", 0.0)
            self._log_ledger("FUNDS", "2028 New Regulations Technical R&D Grant", 100.0)
            self._push_event(
                "NEWS",
                "FIA 2028 NEW REGULATIONS LAUNCH: Screaming 20,000 RPM 2.4L V8 engines & classic DRS era begins! Welcome to Round 1 in Melbourne.",
            )
            self._push_event("CHAMPION", "CAR #1: Reigning World Champion Max Verstappen defends the crown with #1 in 2028!")
            self._push_event(
                "UPGRADE",
                "NEW REGS R&D BOOST: +$100.0M injected into all team budgets for the 2028 new technical regulations!",
            )
        else:
            for d in self.drivers:
                d.setdefault("penalty_points", 0)
            self.hall_of_fame = []
            self.ledger = []
            self.event_feed = []
            self._log_ledger("CAREER", "Appointed Team Principal — FIA 2026 Season Budget Allocated", 0.0)
            self._push_event("NEWS", f"WELCOME TO {self.season_year} FORMULA 1! Active Aero, Sprint Calendar & Overtake Mode era begins.")

        self._reset_season_tallies()"""

assert old_init_fresh in text_champ, "old_init_fresh not found in championship.py"
text_champ = text_champ.replace(old_init_fresh, new_init_fresh, 1)

old_reset_career = """    def reset_career(self, team_id: str = "williams") -> dict:
        with self.lock:
            t_id = team_id if team_id in self._teams_by_id() else "williams"
            self._init_fresh_career(t_id)
            self._begin_weekend()
            self._save_state()
            return {"ok": True}"""

new_reset_career = """    def reset_career(self, team_id: str = "williams", start_year: int = 2026) -> dict:
        with self.lock:
            t_id = team_id if team_id in self._teams_by_id() else "williams"
            year = 2028 if int(start_year) == 2028 else 2026
            self._init_fresh_career(t_id, start_year=year)
            self._begin_weekend()
            self._save_state()
            return {"ok": True, "season_year": self.season_year}"""

assert old_reset_career in text_champ, "old_reset_career not found in championship.py"
text_champ = text_champ.replace(old_reset_career, new_reset_career, 1)

p_champ.write_text(text_champ, encoding="utf-8")
print("sim/championship.py successfully patched with 2028 start_year option!")

# 2. Patch server.py
p_server = Path("server.py")
text_server = p_server.read_text(encoding="utf-8")

old_server_reset = """        elif path == "/api/reset":
            res = self.world.reset_career(str(body.get("team_id", "williams")))"""

new_server_reset = """        elif path == "/api/reset":
            team_id = str(body.get("team_id", "williams"))
            start_year = int(body.get("year", body.get("start_year", 2026)))
            res = self.world.reset_career(team_id, start_year=start_year)"""

assert old_server_reset in text_server, "old_server_reset not found in server.py"
text_server = text_server.replace(old_server_reset, new_server_reset, 1)

p_server.write_text(text_server, encoding="utf-8")
print("server.py successfully patched to pass start_year to reset_career!")

# 3. Patch public/index.html
p_html = Path("public/index.html")
text_html = p_html.read_text(encoding="utf-8")

old_html_ftr = """      <div class="modal-ftr">
        <button class="btn-danger btn-sm" id="btn-reset-career">RESET FRESH 2026 CHAMPIONSHIP</button>
      </div>"""

new_html_ftr = """      <div class="modal-ftr" style="display:flex;gap:10px;justify-content:flex-end;align-items:center;flex-wrap:wrap">
        <span class="muted-note" style="margin:0;margin-right:auto">Restart Season:</span>
        <button class="btn-outline btn-sm" id="btn-reset-career" style="border-color:var(--border);color:var(--text)">RESET 2026 (HYBRID)</button>
        <button class="btn-danger btn-sm" id="btn-reset-2028" style="background:#ff5500;border-color:#ff5500;color:#fff;font-weight:700">START AT 2028 (V8 & DRS)</button>
      </div>"""

assert old_html_ftr in text_html, "old_html_ftr not found in index.html"
text_html = text_html.replace(old_html_ftr, new_html_ftr, 1)

p_html.write_text(text_html, encoding="utf-8")
print("public/index.html successfully patched with 2028 season start button!")

# 4. Patch public/app.js
p_app = Path("public/app.js")
text_app = p_app.read_text(encoding="utf-8")

old_app_reset = """    document.getElementById("btn-reset-career").addEventListener("click", async () => {
      const tid = this.fullState ? this.fullState.player_team_id : "williams";
      const res = await this.apiPost("/api/reset", { team_id: tid });
      if (res.ok) {
        modal.classList.add("hidden");
        this.showToast("SEASON RESET: 2026 FIA Formula 1 World Championship initialized");
        this.fetchFullState();
      }
    });"""

new_app_reset = """    document.getElementById("btn-reset-career").addEventListener("click", async () => {
      const tid = this.fullState ? this.fullState.player_team_id : "williams";
      const res = await this.apiPost("/api/reset", { team_id: tid, year: 2026 });
      if (res.ok) {
        modal.classList.add("hidden");
        this.showToast("SEASON RESET: 2026 FIA Formula 1 World Championship initialized");
        this.fetchFullState();
      }
    });

    const btnReset2028 = document.getElementById("btn-reset-2028");
    if (btnReset2028) {
      btnReset2028.addEventListener("click", async () => {
        const tid = this.fullState ? this.fullState.player_team_id : "williams";
        const res = await this.apiPost("/api/reset", { team_id: tid, year: 2028 });
        if (res.ok) {
          modal.classList.add("hidden");
          this.showToast("SEASON LAUNCH: 2028 FIA 2.4L V8 & Classic DRS Era initialized!");
          this.fetchFullState();
        }
      });
    }"""

assert old_app_reset in text_app, "old_app_reset not found in app.js"
text_app = text_app.replace(old_app_reset, new_app_reset, 1)

p_app.write_text(text_app, encoding="utf-8")
print("public/app.js successfully patched with 2028 button handler!")

