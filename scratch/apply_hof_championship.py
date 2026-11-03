import re

with open("sim/championship.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Imports
target_imp = "from sim.track_geometry import in_pit_tunnel\n"
new_imp = ("from sim.track_geometry import in_pit_tunnel\n"
           "from sim.hall_of_fame import (\n"
           "    generate_default_season_archives,\n"
           "    record_live_race_to_archive,\n"
           "    sync_live_season_status,\n"
           ")\n")
assert target_imp in content, "Missing target_imp"
content = content.replace(target_imp, new_imp, 1)

# 2. __init__ attribute
target_init = "self.calendar_results: list[dict] = []\n"
new_init = ("self.calendar_results: list[dict] = []\n"
            "        self.season_archives: dict[str, dict] = {}\n")
assert target_init in content, "Missing target_init"
content = content.replace(target_init, new_init, 1)

# 3. _init_fresh_career
target_fresh = "self._reset_season_tallies()\n"
new_fresh = ("self.season_archives = generate_default_season_archives()\n"
             "        sync_live_season_status(\n"
             "            self.season_archives,\n"
             "            self.season_year,\n"
             "            self.current_round,\n"
             "            len(self.calendar),\n"
             "            self.phase,\n"
             "            self.get_wdc_table(),\n"
             "            self.get_wcc_table(),\n"
             "        )\n"
             "        self._reset_season_tallies()\n")
assert target_fresh in content, "Missing target_fresh"
content = content.replace(target_fresh, new_fresh, 1)

# 4. _save_state
target_save = '"calendar_results": self.calendar_results,\n'
new_save = ('"calendar_results": self.calendar_results,\n'
            '                "season_archives": self.season_archives,\n')
assert target_save in content, "Missing target_save"
content = content.replace(target_save, new_save, 1)

# 5. _load_state
target_load = 'self.calendar_results = data.get("calendar_results", [])\n'
new_load = ('self.calendar_results = data.get("calendar_results", [])\n'
            '            self.season_archives = data.get("season_archives")\n'
            '            if not self.season_archives:\n'
            '                self.season_archives = generate_default_season_archives()\n'
            '            sync_live_season_status(\n'
            '                self.season_archives,\n'
            '                self.season_year,\n'
            '                self.current_round,\n'
            '                len(self.calendar),\n'
            '                self.phase,\n'
            '                self.get_wdc_table(),\n'
            '                self.get_wcc_table(),\n'
            '            )\n')
assert target_load in content, "Missing target_load"
content = content.replace(target_load, new_load, 1)

# 6. _finish_race
target_finish = """        round_rec = {
            "round": self.current_round,
            "gp": self.current_track.name,
            "country": self.current_track.country,
            "is_sprint": self.current_track.is_sprint,
            "sprint_winner_code": self.sprint_winner_code,
            "winner_code": winner["code"],
            "winner_name": winner["name"],
            "winner_team": winner["team_short"],
            "winner_color": winner["team_color"],
            "p2_code": p2["code"],
            "p3_code": p3["code"],
            "pole_code": pole_code,
            "fastest_lap_code": rs.fastest_lap_code or winner["code"],
        }
        self.calendar_results.append(round_rec)"""

new_finish = """        round_rec = {
            "round": self.current_round,
            "track_id": self.current_track.id,
            "gp": self.current_track.name,
            "circuit": self.current_track.circuit,
            "city": self.current_track.city,
            "country": self.current_track.country,
            "is_sprint": self.current_track.is_sprint,
            "laps": self.current_track.race_laps,
            "sprint_winner_code": self.sprint_winner_code,
            "winner_code": winner["code"],
            "winner_name": winner["name"],
            "winner_team": winner["team_short"],
            "winner_color": winner["team_color"],
            "p2_code": p2["code"],
            "p3_code": p3["code"],
            "pole_code": pole_code,
            "fastest_lap_code": rs.fastest_lap_code or winner["code"],
            "top10": classification[:10],
        }
        self.calendar_results.append(round_rec)
        record_live_race_to_archive(self.season_archives, self.season_year, round_rec, classification, self.current_track)
        sync_live_season_status(
            self.season_archives,
            self.season_year,
            self.current_round,
            len(self.calendar),
            self.phase,
            self.get_wdc_table(),
            self.get_wcc_table(),
        )"""

assert target_finish in content, "Missing target_finish"
content = content.replace(target_finish, new_finish, 1)

# 7. _enter_off_season
target_off = """        self._push_event(
            "CHAMPION",
            f"WORLD CHAMPIONS {self.season_year}: {champ_drv['name']} ({champ_drv['points']} pts) & {champ_team['name']} ({champ_team['points']} pts)!",
        )"""
new_off = """        sync_live_season_status(
            self.season_archives,
            self.season_year,
            self.current_round,
            len(self.calendar),
            "OFF_SEASON",
            wdc,
            wcc,
        )
        self._push_event(
            "CHAMPION",
            f"WORLD CHAMPIONS {self.season_year}: {champ_drv['name']} ({champ_drv['points']} pts) & {champ_team['name']} ({champ_team['points']} pts)!",
        )"""
assert target_off in content, "Missing target_off"
content = content.replace(target_off, new_off, 1)

# 8. _start_next_season
target_start_next = "self._begin_weekend()\n        self._save_state()\n"
new_start_next = ("sync_live_season_status(\n"
                  "            self.season_archives,\n"
                  "            self.season_year,\n"
                  "            self.current_round,\n"
                  "            len(self.calendar),\n"
                  "            self.phase,\n"
                  "            self.get_wdc_table(),\n"
                  "            self.get_wcc_table(),\n"
                  "        )\n"
                  "        self._begin_weekend()\n"
                  "        self._save_state()\n")
assert target_start_next in content, "Missing target_start_next"
content = content.replace(target_start_next, new_start_next, 1)

# 9. build_full_state_payload and get_hall_of_fame_data
target_payload = '"starting_compounds": self.starting_compounds,\n            }'
new_payload = ('"starting_compounds": self.starting_compounds,\n'
               '                "season_archives": self.get_hall_of_fame_data(),\n'
               '            }')
assert target_payload in content, "Missing target_payload"
content = content.replace(target_payload, new_payload, 1)

# 10. Add get_hall_of_fame_data method
content += """

    def get_hall_of_fame_data(self) -> dict:
        with self.lock:
            if not getattr(self, "season_archives", None):
                self.season_archives = generate_default_season_archives()
            return {
                "available_years": [2026, 2027, 2028, 2029, 2030],
                "current_year": self.season_year,
                "seasons": self.season_archives,
            }
"""

with open("sim/championship.py", "w", encoding="utf-8") as f:
    f.write(content)

print("sim/championship.py updated successfully!")

