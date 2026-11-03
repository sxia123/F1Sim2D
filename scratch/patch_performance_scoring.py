from pathlib import Path

# 1. Patch sim/championship.py
p_champ = Path("sim/championship.py")
text = p_champ.read_text(encoding="utf-8")

method_to_insert = """    def _adjust_driver_scores_from_performance(self, wdc: list[dict], wcc: list[dict]) -> None:
        \"\"\"Adjust driver scores (pace, racecraft, consistency, tire_mgmt, defense) and market values
        based on their actual on-track performance in the concluded championship season.\"\"\"
        tmap = self._teams_by_id()
        wcc_ranks = {row["id"]: row["rank"] for row in wcc}
        wdc_ranks = {row["id"]: row["rank"] for row in wdc}

        upgraded_drivers = []
        downgraded_drivers = []

        for d in self.drivers:
            did = d["id"]
            old_ovr = driver_overall(d)

            # Inactive free agent / reserve driver adjustment
            if d["team_id"] is None:
                if d["age"] <= 23:
                    d["pace"] = min(96, d["pace"] + random.choice([0, 1]))
                    d["consistency"] = min(96, d["consistency"] + random.choice([0, 1]))
                elif d["age"] >= 36 and not d.get("legend"):
                    d["pace"] = max(74, d["pace"] - random.choice([0, 1]))
                d["last_ovr_change"] = round(driver_overall(d) - old_ovr, 1)
                continue

            # Active championship driver metrics
            pts = self.driver_points.get(did, 0)
            wins = self.driver_wins.get(did, 0)
            pods = self.driver_podiums.get(did, 0)
            poles = self.driver_poles.get(did, 0)
            dnfs = self.driver_dnfs.get(did, 0)
            pen_pts = d.get("penalty_points", 0)
            rank = wdc_ranks.get(did, 22)
            tid = d["team_id"]
            wcc_rank = wcc_ranks.get(tid, 10)

            # 1. Base score from championship finish rank
            if rank == 1:
                perf = 1.90  # World Champion
            elif rank <= 3:
                perf = 1.40
            elif rank <= 6:
                perf = 0.90
            elif rank <= 10:
                perf = 0.40
            elif rank <= 15:
                perf = 0.00
            elif rank <= 19:
                perf = -0.55
            else:
                perf = -1.05

            # 2. Race achievements bonus
            perf += min(0.9, wins * 0.22)
            perf += min(0.6, pods * 0.08)
            perf += min(0.4, poles * 0.10)

            # 3. Teammate head-to-head comparison in equal machinery
            teammate = next((other for other in self._active_drivers() if other["team_id"] == tid and other["id"] != did), None)
            if teammate:
                tm_pts = self.driver_points.get(teammate["id"], 0)
                tot_pts = pts + tm_pts
                if tot_pts > 0:
                    share = pts / tot_pts
                    if share >= 0.72:
                        perf += 0.85  # Decisively outperformed teammate
                    elif share >= 0.58:
                        perf += 0.45
                    elif share <= 0.28:
                        perf -= 0.85  # Decisively outscored by teammate
                    elif share <= 0.42:
                        perf -= 0.45

            # 4. Car tier expectation comparison
            exp_rank = (wcc_rank * 2) - 1
            if rank <= exp_rank - 3:
                perf += 0.65  # Punched above car's weight
            elif rank >= exp_rank + 4:
                perf -= 0.65  # Lagged behind car capability

            # 5. Clean driving & reliability impact
            if dnfs <= 1 and pen_pts == 0:
                perf += 0.30
            elif dnfs >= 4:
                perf -= 0.35
            if pen_pts >= 6:
                perf -= 0.40

            # 6. Age trajectory modulation
            if d["age"] <= 23:
                perf += 0.60
            elif d["age"] <= 25:
                perf += 0.25
            elif d["age"] >= 37:
                if perf > 1.0:
                    perf -= 0.15  # Veteran in form defies decline
                else:
                    perf -= 0.55
            elif d["age"] >= 35 and perf < 0.2:
                perf -= 0.25

            # 7. Apply stat modifications
            max_stat = 99 if d.get("legend") else 98
            min_stat = 72

            if perf >= 2.1:
                # S-Tier Performance (+3 OVR)
                d["pace"] = min(max_stat, d["pace"] + 2)
                d["racecraft"] = min(max_stat, d["racecraft"] + 2)
                d["consistency"] = min(max_stat, d["consistency"] + 2)
                d["tire_mgmt"] = min(max_stat, d["tire_mgmt"] + 2)
                d["defense"] = min(max_stat, d["defense"] + 1)
                d["value_m"] = round(min(65.0, d["value_m"] + 5.5), 1)
                d["salary_m"] = round(min(45.0, d["salary_m"] + 2.5), 1)
            elif perf >= 1.1:
                # A-Tier Performance (+2 OVR)
                d["pace"] = min(max_stat, d["pace"] + 2)
                d["racecraft"] = min(max_stat, d["racecraft"] + 1)
                d["consistency"] = min(max_stat, d["consistency"] + 1)
                d["tire_mgmt"] = min(max_stat, d["tire_mgmt"] + 1)
                d["value_m"] = round(min(60.0, d["value_m"] + 3.5), 1)
                d["salary_m"] = round(min(40.0, d["salary_m"] + 1.5), 1)
            elif perf >= 0.35:
                # B-Tier Performance (+1 OVR)
                d["pace"] = min(max_stat, d["pace"] + 1)
                d["racecraft"] = min(max_stat, d["racecraft"] + 1)
                d["value_m"] = round(min(55.0, d["value_m"] + 2.0), 1)
                d["salary_m"] = round(min(35.0, d["salary_m"] + 0.8), 1)
            elif perf <= -1.4:
                # Significant Underperformance (-2 OVR)
                d["pace"] = max(min_stat, d["pace"] - 2)
                d["racecraft"] = max(min_stat, d["racecraft"] - 1)
                d["consistency"] = max(min_stat, d["consistency"] - 2)
                d["defense"] = max(min_stat, d["defense"] - 1)
                d["value_m"] = round(max(5.0, d["value_m"] - 4.5), 1)
                d["salary_m"] = round(max(1.5, d["salary_m"] - 1.8), 1)
            elif perf <= -0.4:
                # Moderate Underperformance (-1 OVR)
                d["pace"] = max(min_stat, d["pace"] - 1)
                d["consistency"] = max(min_stat, d["consistency"] - 1)
                d["value_m"] = round(max(5.0, d["value_m"] - 2.0), 1)
                d["salary_m"] = round(max(1.5, d["salary_m"] - 0.8), 1)

            new_ovr = driver_overall(d)
            diff = round(new_ovr - old_ovr, 1)
            d["last_ovr_change"] = diff

            if diff >= 1.0:
                upgraded_drivers.append((d["name"], tmap[tid]["short"], old_ovr, new_ovr, diff))
            elif diff <= -1.0:
                downgraded_drivers.append((d["name"], tmap[tid]["short"], old_ovr, new_ovr, diff))

        if upgraded_drivers:
            upgraded_drivers.sort(key=lambda x: -x[4])
            top_ups = [f"{name} ({team} {new_ovr:.0f} OVR, +{diff:+.1f})" for name, team, old, new_ovr, diff in upgraded_drivers[:3]]
            self._push_event(
                "UPGRADE",
                f"DRIVER DEVELOPMENT: Season performance score adjustments awarded — {'; '.join(top_ups)}!",
            )

        if downgraded_drivers:
            downgraded_drivers.sort(key=lambda x: x[4])
            top_downs = [f"{name} ({team} {new_ovr:.0f} OVR, {diff:+.1f})" for name, team, old, new_ovr, diff in downgraded_drivers[:2]]
            self._push_event(
                "NEWS",
                f"DRIVER RATINGS: Performance downgrades following difficult campaign — {'; '.join(top_downs)}.",
            )

"""

# Insert _adjust_driver_scores_from_performance right above _start_next_season
target_start_season = "    def _start_next_season(self) -> None:"
assert target_start_season in text, "target_start_season not found in championship.py"
text = text.replace(target_start_season, method_to_insert + target_start_season, 1)

# Inside _start_next_season, call _adjust_driver_scores_from_performance and remove old stat lines
old_start_body = """    def _start_next_season(self) -> None:
        free_pool = sorted(self._free_agents(), key=driver_overall, reverse=True)
        for d in self.drivers:
            d["age"] += 1
            d["penalty_points"] = max(0, d.get("penalty_points", 0) - 6)
            if d["team_id"] is not None and d["contract_years"] > 0:
                d["contract_years"] -= 1

            if d["age"] <= 23:
                for stat in ("pace", "racecraft", "consistency", "tire_mgmt"):
                    d[stat] = min(98, d[stat] + random.randint(0, 2))
                d["value_m"] = round(min(58.0, d["value_m"] + 2.5), 1)
            elif d["age"] >= 39:
                for stat in ("pace", "racecraft"):
                    d[stat] = max(76, d[stat] - random.randint(0, 2))
                if d["age"] >= 42 and d["team_id"] is not None and d["team_id"] != self.player_team_id and free_pool:"""

new_start_body = """    def _start_next_season(self) -> None:
        wdc_table = self.get_wdc_table()
        wcc_table = self.get_wcc_table()
        self._adjust_driver_scores_from_performance(wdc_table, wcc_table)

        free_pool = sorted(self._free_agents(), key=driver_overall, reverse=True)
        for d in self.drivers:
            d["age"] += 1
            d["penalty_points"] = max(0, d.get("penalty_points", 0) - 6)
            if d["team_id"] is not None and d["contract_years"] > 0:
                d["contract_years"] -= 1

            if d["age"] >= 42 and d["team_id"] is not None and d["team_id"] != self.player_team_id and free_pool:"""

assert old_start_body in text, "old_start_body not found in championship.py"
text = text.replace(old_start_body, new_start_body, 1)

# In build_full_state_payload, include last_ovr_change
old_payload_driver = '"overall": driver_overall(d),'
new_payload_driver = '"overall": driver_overall(d),\n                        "last_ovr_change": d.get("last_ovr_change", 0.0),'
assert old_payload_driver in text, "old_payload_driver not found in championship.py"
text = text.replace(old_payload_driver, new_payload_driver, 1)

p_champ.write_text(text, encoding="utf-8")
print("sim/championship.py successfully patched with performance-based driver score adjustments!")

# 2. Patch public/app.js
p_app = Path("public/app.js")
text_app = p_app.read_text(encoding="utf-8")

old_ovr_td = '<td><strong style="color:${d.overall >= 95 ? "#e10600" : "#ffffff"}">${d.overall}</strong></td>'
new_ovr_td = """<td>
            <strong style="color:${d.overall >= 95 ? "#e10600" : "#ffffff"}">${d.overall}</strong>${d.last_ovr_change ? ` <span style="font-size:10px;font-weight:700;color:${d.last_ovr_change > 0 ? '#00e676' : '#ff5252'}">${d.last_ovr_change > 0 ? '+' : ''}${d.last_ovr_change}</span>` : ""}
          </td>"""
assert old_ovr_td in text_app, "old_ovr_td not found in app.js"
text_app = text_app.replace(old_ovr_td, new_ovr_td, 1)

p_app.write_text(text_app, encoding="utf-8")
print("public/app.js successfully patched with driver score change indicators!")

