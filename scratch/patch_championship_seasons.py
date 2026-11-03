import re
from pathlib import Path

path = Path("sim/championship.py")
content = path.read_text(encoding="utf-8")

# 1. Add get_season_regulations above class ChampionshipWorld
reg_func = '''def get_season_regulations(year: int) -> dict[str, Any]:
    """FIA Technical & Sporting Regulations definition by era (2026-2027 Hybrid vs 2028-2030 V8 & DRS)."""
    if year >= 2028:
        return {
            "year": year,
            "era_id": "V8_DRS",
            "name": f"{year} FIA 2.4L V8 Naturally Aspirated & DRS Era",
            "short_name": f"{year} V8 & DRS",
            "engine_type": "2.4L Naturally Aspirated V8 (20,000 RPM)",
            "ice_power_mult": 1.25,        # +25% combustion engine power/acceleration
            "top_speed_mult": 1.05,
            "electric_system": "120kW KERS",
            "max_battery_mj": 2.0,         # Weaker electric (2.0 MJ vs 4.0 MJ)
            "ers_drain_rate": 0.16,
            "ers_harvest_rate": 0.22,
            "has_active_aero": False,      # Static high downforce wings on straights
            "has_classic_drs": True,       # Classic rear wing flap in FIA DRS zones
            "drs_boost_kmh": 22.0,         # +22 km/h drag reduction boost
            "description": "2.4L V8 engines scream at 20,000 RPM (+25% power). Electrical deployment is reduced to 120kW KERS, and classic rear-wing DRS returns in designated zones.",
        }
    else:
        return {
            "year": year,
            "era_id": "2026_HYBRID",
            "name": f"{year} FIA Turbo-Hybrid & Active Aero Era",
            "short_name": f"{year} Hybrid",
            "engine_type": "1.6L V6 Turbo-Hybrid (350kW MGU-K)",
            "ice_power_mult": 1.00,
            "top_speed_mult": 1.00,
            "electric_system": "350kW MGU-K",
            "max_battery_mj": 4.0,
            "ers_drain_rate": 0.28,
            "ers_harvest_rate": 0.42,
            "has_active_aero": True,       # Active Aero Straight-Mode
            "has_classic_drs": False,
            "drs_boost_kmh": 0.0,
            "description": "50/50 ICE and 350kW MGU-K electrical power split with Active Aero Straight-Mode and manual Overtake boost.",
        }


class ChampionshipWorld:'''

assert "class ChampionshipWorld:" in content, "class ChampionshipWorld not found"
content = content.replace("class ChampionshipWorld:", reg_func, 1)

# 2. Add starting_compounds to __init__
init_target = """        self.temp_ban_subs: list[tuple[str, str, str]] = []"""
init_repl = """        self.temp_ban_subs: list[tuple[str, str, str]] = []
        self.starting_compounds: dict[str, str] = {}"""

assert init_target in content, "init_target not found"
content = content.replace(init_target, init_repl, 1)

# 3. Add regulations property, is_transfer_window_open, and set_starting_compound under Helpers
helper_target = """    @property
    def current_track(self):
        return TRACK_BY_ROUND.get(self.current_round, COMPILED_TRACKS[0])"""

helper_repl = """    @property
    def current_track(self):
        return TRACK_BY_ROUND.get(self.current_round, COMPILED_TRACKS[0])

    @property
    def regulations(self) -> dict[str, Any]:
        return get_season_regulations(self.season_year)

    def is_transfer_window_open(self) -> bool:
        \"\"\"Transfer window is open only at the start of a season (Round 1 or Off-Season).\"\"\"
        return self.phase == "OFF_SEASON" or self.current_round == 1

    def set_starting_compound(self, driver_id: str, compound: str) -> dict:
        with self.lock:
            if compound not in TIRE_COMPOUNDS:
                return {"ok": False, "error": f"Invalid tyre compound: {compound}"}
            p_drivers = [d["id"] for d in self.drivers if d["team_id"] == self.player_team_id]
            if driver_id not in p_drivers:
                return {"ok": False, "error": "Can only set starting tyres for your team's drivers."}
            self.starting_compounds[driver_id] = compound
            dmap = self._drivers_by_id()
            drv = dmap.get(driver_id)
            drv_code = drv["code"] if drv else driver_id
            drv_num = drv["number"] if drv else ""
            if self.race_session:
                self.race_session.set_starting_compound(driver_id, compound)
            self._push_event("RADIO", f"GRID STRATEGY: #{drv_num} {drv_code} confirmed starting on {compound} tyres!")
            self._save_state()
            return {"ok": True, "driver_id": driver_id, "compound": compound}"""

assert helper_target in content, "helper_target not found"
content = content.replace(helper_target, helper_repl, 1)

# 4. Pass regulations and starting_compounds to sessions
sprint_race_target = """        self.race_session = RaceSession(
            trk,
            self._teams_by_id(),
            grid_drivers,
            round(sprint_wet, 2),
            trk.rain_chance,
            self.player_team_id,
            is_sprint=True,
        )"""
sprint_race_repl = """        self.race_session = RaceSession(
            trk,
            self._teams_by_id(),
            grid_drivers,
            round(sprint_wet, 2),
            trk.rain_chance,
            self.player_team_id,
            is_sprint=True,
            regulations=self.regulations,
            starting_compounds=self.starting_compounds,
        )"""
assert sprint_race_target in content, "sprint_race_target not found"
content = content.replace(sprint_race_target, sprint_race_repl, 1)

sprint_quali_target = """        self.quali_session = QualifyingSession(
            trk,
            self._teams_by_id(),
            self._active_drivers(),
            self.weekend_wetness,
            is_sprint_quali=True,
        )"""
sprint_quali_repl = """        self.quali_session = QualifyingSession(
            trk,
            self._teams_by_id(),
            self._active_drivers(),
            self.weekend_wetness,
            is_sprint_quali=True,
            regulations=self.regulations,
        )"""
assert sprint_quali_target in content, "sprint_quali_target not found"
content = content.replace(sprint_quali_target, sprint_quali_repl, 1)

main_quali_target = """        self.quali_session = QualifyingSession(
            trk,
            self._teams_by_id(),
            self._active_drivers(),
            self.weekend_wetness,
            is_sprint_quali=False,
        )"""
main_quali_repl = """        self.quali_session = QualifyingSession(
            trk,
            self._teams_by_id(),
            self._active_drivers(),
            self.weekend_wetness,
            is_sprint_quali=False,
            regulations=self.regulations,
        )"""
assert main_quali_target in content, "main_quali_target not found"
content = content.replace(main_quali_target, main_quali_repl, 1)

main_grid_target = """        self.race_session = RaceSession(
            trk,
            self._teams_by_id(),
            grid_drivers,
            round(race_wet, 2),
            trk.rain_chance,
            self.player_team_id,
            is_sprint=False,
        )"""
main_grid_repl = """        self.race_session = RaceSession(
            trk,
            self._teams_by_id(),
            grid_drivers,
            round(race_wet, 2),
            trk.rain_chance,
            self.player_team_id,
            is_sprint=False,
            regulations=self.regulations,
            starting_compounds=self.starting_compounds,
        )"""
assert main_grid_target in content, "main_grid_target not found"
content = content.replace(main_grid_target, main_grid_repl, 1)

# 5. Multi-season transition (keep improvements, 2028 new regulations for top 4 and randomized midfield)
season_reset_target = """        for t in self.teams:
            for dept, lvl in t["upgrades"].items():
                if lvl >= 8:
                    t["upgrades"][dept] = lvl - 1

        self.season_year += 1
        self.current_round = 1
        self._reset_season_tallies()
        self._push_event("NEWS", f"NEW SEASON {self.season_year} UNDERWAY! Cars unveiled for Round 1 in Melbourne.")"""

season_reset_repl = """        prev_year = self.season_year
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
        self._push_event("NEWS", f"NEW SEASON {self.season_year} UNDERWAY ({reg['short_name']})! Cars unveiled for Round 1 in Melbourne.")"""

assert season_reset_target in content, "season_reset_target not found"
content = content.replace(season_reset_target, season_reset_repl, 1)

# 6. Restrict driver transfer window in evaluate_trade, execute_trade, sign_free_agent
eval_target = """    def evaluate_trade(self, my_driver_id: str, target_driver_id: str, cash_offer_m: float) -> dict:
        with self.lock:"""
eval_repl = """    def evaluate_trade(self, my_driver_id: str, target_driver_id: str, cash_offer_m: float) -> dict:
        with self.lock:
            if not self.is_transfer_window_open():
                return {
                    "ok": False,
                    "error": "Transfer window is currently LOCKED. FIA regulations permit driver trades and free agent signings only at the start of each season (Round 1 or Off-Season).",
                }"""
assert eval_target in content, "eval_target not found"
content = content.replace(eval_target, eval_repl, 1)

exec_target = """    def execute_trade(self, my_driver_id: str, target_driver_id: str, cash_offer_m: float) -> dict:
        with self.lock:"""
exec_repl = """    def execute_trade(self, my_driver_id: str, target_driver_id: str, cash_offer_m: float) -> dict:
        with self.lock:
            if not self.is_transfer_window_open():
                return {
                    "ok": False,
                    "error": "Transfer window is currently LOCKED. FIA regulations permit driver trades and free agent signings only at the start of each season (Round 1 or Off-Season).",
                }"""
assert exec_target in content, "exec_target not found"
content = content.replace(exec_target, exec_repl, 1)

sign_target = """    def sign_free_agent(self, release_driver_id: str, free_agent_id: str) -> dict:
        with self.lock:"""
sign_repl = """    def sign_free_agent(self, release_driver_id: str, free_agent_id: str) -> dict:
        with self.lock:
            if not self.is_transfer_window_open():
                return {
                    "ok": False,
                    "error": "Transfer window is currently LOCKED. FIA regulations permit driver trades and free agent signings only at the start of each season (Round 1 or Off-Season).",
                }"""
assert sign_target in content, "sign_target not found"
content = content.replace(sign_target, sign_repl, 1)

# 7. Pit wall command support start_compound
pw_target = """            if "next_compound" in cmd and cmd["next_compound"] in TIRE_COMPOUNDS:
                car.next_compound = cmd["next_compound"]"""
pw_repl = """            if "start_compound" in cmd and cmd["start_compound"] in TIRE_COMPOUNDS:
                comp = cmd["start_compound"]
                self.starting_compounds[driver_id] = comp
                if self.phase in ("GRID_WALK", "PRE_WEEKEND") or (self.race_session and self.race_session.lights_countdown > 0):
                    car.compound = comp
                    car.compounds_used = {comp}
                    car.tire_age_laps = 0
                    car.tire_wear = 0.01
                    self._push_event("RADIO", f"GRID CALL: #{car.number} {car.code} fitted with {comp} tyres for race start!")
            if "next_compound" in cmd and cmd["next_compound"] in TIRE_COMPOUNDS:
                car.next_compound = cmd["next_compound"]"""
assert pw_target in content, "pw_target not found"
content = content.replace(pw_target, pw_repl, 1)

# 8. Add drs and drs_elig in cars payload of build_live_tick_payload
car_payload_target = """                        "ovt_elig": c.overtake_eligible,
                        "ovt": c.overtake_active,"""
car_payload_repl = """                        "ovt_elig": c.overtake_eligible,
                        "ovt": c.overtake_active,
                        "drs_elig": getattr(c, "drs_eligible", False),
                        "drs": getattr(c, "drs_active", False),"""
assert car_payload_target in content, "car_payload_target not found"
content = content.replace(car_payload_target, car_payload_repl, 1)

# 9. Add regulations and transfer_window_open in build_live_tick_payload
tick_return_target = """                "events": self.event_feed[-28:],
                "podium": self.last_podium_summary,
            }"""
tick_return_repl = """                "events": self.event_feed[-28:],
                "podium": self.last_podium_summary,
                "regulations": self.regulations,
                "transfer_window_open": self.is_transfer_window_open(),
            }"""
assert tick_return_target in content, "tick_return_target not found"
content = content.replace(tick_return_target, tick_return_repl, 1)

# 10. Add regulations and transfer_window_open in build_full_state_payload
state_return_target = """                "ledger": list(reversed(self.ledger[-40:])),
                "track": self.current_track.to_client_payload(),
            }"""
state_return_repl = """                "ledger": list(reversed(self.ledger[-40:])),
                "track": self.current_track.to_client_payload(),
                "regulations": self.regulations,
                "transfer_window_open": self.is_transfer_window_open(),
                "starting_compounds": self.starting_compounds,
            }"""
assert state_return_target in content, "state_return_target not found"
content = content.replace(state_return_target, state_return_repl, 1)

path.write_text(content, encoding="utf-8")
print("Successfully patched sim/championship.py!")

