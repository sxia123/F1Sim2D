"""Perpetual 2026+ F1 Championship Lifecycle, Sprint Weekends, Knockout Qualifying, R&D & Persistence."""

from __future__ import annotations
import json
import copy
import os
import random
import threading
import time
from pathlib import Path
from typing import Any

from sim.data import (
    INITIAL_DRIVERS,
    RACE_POINTS,
    SPONSORS,
    SPRINT_POINTS,
    TIRE_COMPOUNDS,
    UPGRADE_DEPARTMENTS,
    WCC_PRIZE_POOL_M,
    clone_initial_roster,
    driver_overall,
    team_car_rating,
    upgrade_cost_m,
)
from sim.physics import QualifyingSession, RaceSession
from sim.tracks import get_season_tracks, calendar_status
from sim.track_geometry import in_pit_tunnel
from sim.hall_of_fame import (
    generate_default_season_archives,
    record_live_race_to_archive,
    sync_live_season_status,
)

SAVE_PATH = Path(__file__).resolve().parent.parent / "data" / "championship_state.json"


DRIVER_DEFAULT_CAREER_NUMBERS: dict[str, int] = {
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


def get_season_regulations(year: int) -> dict[str, Any]:
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


class ChampionshipWorld:
    """Thread-safe perpetual background F1 Championship & Team Principal career simulator."""

    def __init__(self, save_path: Path = SAVE_PATH):
        self.lock = threading.RLock()
        self.save_path = save_path
        self.save_path.parent.mkdir(parents=True, exist_ok=True)

        self.sim_speed: float = 1.0  # 0.0 (paused), 0.5 (slow-mo), 1.0, 2.0, 4.0, 8.0, 16.0
        self.tick_counter: int = 0
        self.started_at: float = time.time()

        # Core persistent state
        self.season_year: int = 2026
        self._legacy_calendar: bool = False
        self.current_round: int = 1
        self.player_team_id: str = "williams"

        self.teams: list[dict] = []
        self.drivers: list[dict] = []
        self.driver_points: dict[str, int] = {}
        self.driver_wins: dict[str, int] = {}
        self.driver_podiums: dict[str, int] = {}
        self.driver_poles: dict[str, int] = {}
        self.driver_dnfs: dict[str, int] = {}
        self.team_points: dict[str, int] = {}
        self.team_wins: dict[str, int] = {}

        self.calendar_results: list[dict] = []
        self.season_archives: dict[str, dict] = {}
        self.hall_of_fame: list[dict] = []
        self.ledger: list[dict] = []
        self.event_feed: list[dict] = []
        self._event_seq: int = 0

        # Active weekend state
        # Phases: PRE_WEEKEND, SPRINT_QUALIFYING, SPRINT_RACE, QUALIFYING, GRID_WALK, RACE, PODIUM, OFF_SEASON
        self.phase: str = "PRE_WEEKEND"
        self.phase_timer: float = 7.0
        self.weekend_wetness: float = 0.0
        self.weekend_rain_forecast: float = 0.1
        self.quali_session: QualifyingSession | None = None
        self.race_session: RaceSession | None = None
        self.sprint_grid_order_ids: list[str] = []
        self.sprint_winner_code: str = ""
        self.grid_order_ids: list[str] = []
        self.last_podium_summary: dict | None = None
        self.temp_ban_subs: list[tuple[str, str, str]] = []
        self.starting_compounds: dict[str, str] = {}

        if not self._load_state():
            self._init_fresh_career("williams")
            self._begin_weekend()

    # -------------------------------------------------------------------------
    # Initialization & Persistence
    # -------------------------------------------------------------------------
    def _init_fresh_career(self, player_team_id: str = "williams", start_year: int = 2026) -> None:
        self._legacy_calendar = False
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
                f"FIA 2028 NEW REGULATIONS LAUNCH: Screaming 20,000 RPM 2.4L V8 engines & classic DRS era begins! Welcome to Round 1 in {self.current_track.city}.",
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

        self.season_archives = generate_default_season_archives()
        sync_live_season_status(
            self.season_archives,
            self.season_year,
            self.current_round,
            len(self.calendar),
            self.phase,
            self.get_wdc_table(),
            self.get_wcc_table(),
        )
        self._reset_season_tallies()

    def _reset_season_tallies(self) -> None:
        self.driver_points = {d["id"]: 0 for d in self.drivers}
        self.driver_wins = {d["id"]: 0 for d in self.drivers}
        self.driver_podiums = {d["id"]: 0 for d in self.drivers}
        self.driver_poles = {d["id"]: 0 for d in self.drivers}
        self.driver_dnfs = {d["id"]: 0 for d in self.drivers}
        self.team_points = {t["id"]: 0 for t in self.teams}
        self.team_wins = {t["id"]: 0 for t in self.teams}
        self.calendar_results = []

    def _save_state(self) -> None:
        try:
            payload = {
                "season_year": self.season_year,
                "calendar_version": 1,
                "legacy_calendar": self._legacy_calendar,
                "current_round": self.current_round,
                "player_team_id": self.player_team_id,
                "teams": self.teams,
                "drivers": self.drivers,
                "driver_points": self.driver_points,
                "driver_wins": self.driver_wins,
                "driver_podiums": self.driver_podiums,
                "driver_poles": self.driver_poles,
                "driver_dnfs": self.driver_dnfs,
                "team_points": self.team_points,
                "team_wins": self.team_wins,
                "calendar_results": self.calendar_results,
                "season_archives": self.season_archives,
                "reigning_wdc_id": getattr(self, "reigning_wdc_id", ""),
                "hall_of_fame": self.hall_of_fame[-25:],
                "ledger": self.ledger[-60:],
                "event_feed": self.event_feed[-80:],
                "event_seq": self._event_seq,
            }
            serialized = json.dumps(payload, indent=2)
            try:
                tmp = self.save_path.with_suffix(".tmp")
                tmp.write_text(serialized, encoding="utf-8")
                os.replace(tmp, self.save_path)
            except (PermissionError, OSError):
                # Fallback on Windows if championship_state.json is held open in an editor or viewer
                self.save_path.write_text(serialized, encoding="utf-8")
                if tmp.exists():
                    try:
                        tmp.unlink()
                    except Exception:
                        pass
        except Exception:
            pass

    def _load_state(self) -> bool:
        if not self.save_path.exists():
            return False
        try:
            data = json.loads(self.save_path.read_text(encoding="utf-8"))
            self.season_year = int(data["season_year"])
            self._legacy_calendar = bool(data.get('legacy_calendar', data.get('calendar_version') is None))
            self.current_round = int(data["current_round"])
            self.player_team_id = data["player_team_id"]
            self.teams = data["teams"]
            self.drivers = data["drivers"]
            self.driver_points = data["driver_points"]
            self.driver_wins = data["driver_wins"]
            self.driver_podiums = data["driver_podiums"]
            self.driver_poles = data["driver_poles"]
            self.driver_dnfs = data["driver_dnfs"]
            self.reigning_wdc_id = data.get("reigning_wdc_id", "")

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
                    self.driver_dnfs[did] = 0
            self.team_points = data["team_points"]
            self.team_wins = data["team_wins"]
            self.calendar_results = data.get("calendar_results", [])
            self.season_archives = data.get("season_archives")
            if not self.season_archives:
                self.season_archives = generate_default_season_archives()
            sync_live_season_status(
                self.season_archives,
                self.season_year,
                self.current_round,
                len(self.calendar),
                self.phase,
                self.get_wdc_table(),
                self.get_wcc_table(),
            )
            self.hall_of_fame = data.get("hall_of_fame", [])
            self.ledger = data.get("ledger", [])
            self.event_feed = data.get("event_feed", [])
            self._event_seq = int(data.get("event_seq", len(self.event_feed)))
            self._begin_weekend()
            self._push_event(
                "SERVER",
                f"Persistent Championship resumed at {self.season_year} Round {self.current_round} ({self.current_track.name}).",
            )
            return True
        except Exception:
            return False

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------
    @property
    def calendar(self):
        return get_season_tracks(self.season_year, self._legacy_calendar)

    @property
    def current_track(self):
        tracks = self.calendar
        return tracks[max(0, min(self.current_round - 1, len(tracks) - 1))]

    @property
    def regulations(self) -> dict[str, Any]:
        return get_season_regulations(self.season_year)

    def is_transfer_window_open(self) -> bool:
        """Transfer window is open only at the start of a season (Round 1 or Off-Season)."""
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
                car = self.race_session.cars_by_id.get(driver_id)
                if car:
                    car.next_compound = compound
            self._push_event("RADIO", f"GRID STRATEGY: #{drv_num} {drv_code} confirmed starting on {compound} tyres!")
            self._save_state()
            return {"ok": True, "driver_id": driver_id, "compound": compound}

    def _teams_by_id(self) -> dict[str, dict]:
        return {t["id"]: t for t in self.teams}

    def _drivers_by_id(self) -> dict[str, dict]:
        return {d["id"]: d for d in self.drivers}

    def _active_drivers(self) -> list[dict]:
        return [d for d in self.drivers if d["team_id"] is not None]

    def _free_agents(self) -> list[dict]:
        return [d for d in self.drivers if d["team_id"] is None]

    def _push_event(self, kind: str, message: str) -> None:
        self._event_seq += 1
        if self.phase == "RACE" and self.race_session and self.race_session.standings:
            ldr = self.race_session.standings[0]
            lap_tag = f"L{ldr.lap}/{self.race_session.total_laps}"
        elif self.phase == "SPRINT_RACE" and self.race_session and self.race_session.standings:
            ldr = self.race_session.standings[0]
            lap_tag = f"SPR {ldr.lap}/{self.race_session.total_laps}"
        elif self.phase in ("QUALIFYING", "SPRINT_QUALIFYING") and self.quali_session:
            lap_tag = self.quali_session.stage_name
        else:
            lap_tag = f"R{self.current_round}"

        self.event_feed.append(
            {
                "id": self._event_seq,
                "kind": kind,
                "tag": lap_tag,
                "msg": message,
                "ts": round(time.time(), 1),
            }
        )
        if len(self.event_feed) > 160:
            self.event_feed = self.event_feed[-160:]

    def _log_ledger(self, category: str, desc: str, amount_m: float) -> None:
        p_team = self._teams_by_id().get(self.player_team_id)
        bal = round(p_team["budget_m"], 2) if p_team else 0.0
        self.ledger.append(
            {
                "season": self.season_year,
                "round": self.current_round,
                "category": category,
                "desc": desc,
                "amount_m": round(amount_m, 2),
                "balance_m": bal,
            }
        )
        if len(self.ledger) > 75:
            self.ledger = self.ledger[-75:]

    # -------------------------------------------------------------------------
    # Perpetual Championship State Machine
    # -------------------------------------------------------------------------
    def step(self, real_dt: float) -> None:
        with self.lock:
            self.tick_counter += 1
            if self.sim_speed <= 0.0:
                return

            dt = min(real_dt, 0.1) * self.sim_speed
            remaining = dt
            while remaining > 1e-5:
                sub_dt = min(remaining, 0.05)
                remaining -= sub_dt
                self._step_sub(sub_dt)

    def _step_sub(self, dt: float) -> None:
        if self.phase == "PRE_WEEKEND":
            self.phase_timer -= dt
            if self.phase_timer <= 0.0:
                if self.current_track.is_sprint:
                    self._start_sprint_qualifying()
                else:
                    self._start_qualifying()

        elif self.phase == "SPRINT_QUALIFYING":
            assert self.quali_session is not None
            self.quali_session.step(dt, self._push_event)
            if self.quali_session.finished:
                self.sprint_grid_order_ids = [c.driver_id for c in self.quali_session.standings]
                self._start_sprint_race()

        elif self.phase == "SPRINT_RACE":
            assert self.race_session is not None
            self.race_session.step(dt, self._push_event)
            if self.race_session.finished:
                self._conclude_sprint_race()

        elif self.phase == "QUALIFYING":
            assert self.quali_session is not None
            self.quali_session.step(dt, self._push_event)
            if self.quali_session.finished:
                self._finish_qualifying_to_grid()

        elif self.phase == "GRID_WALK":
            self.phase_timer -= dt
            if self.phase_timer <= 0.0:
                self._start_race()

        elif self.phase == "RACE":
            assert self.race_session is not None
            self.race_session.step(dt, self._push_event)
            if self.race_session.finished:
                self._conclude_race()

        elif self.phase == "PODIUM":
            self.phase_timer -= dt
            if self.phase_timer <= 0.0:
                self._advance_after_podium()

        elif self.phase == "OFF_SEASON":
            self.phase_timer -= dt
            if self.phase_timer <= 0.0:
                self._start_next_season()

    def _begin_weekend(self) -> None:
        trk = self.current_track
        self.phase = "PRE_WEEKEND"
        self.phase_timer = 7.0
        self.quali_session = None
        self.race_session = None
        self.sprint_grid_order_ids = []
        self.sprint_winner_code = ""
        self.grid_order_ids = []
        self.last_podium_summary = None

        self.weekend_rain_forecast = trk.rain_chance
        if random.random() < trk.rain_chance:
            self.weekend_wetness = round(random.uniform(0.18, 0.72), 2)
        else:
            self.weekend_wetness = 0.0

        self._apply_race_bans_if_any()

        # AI rival teams invest surplus budget into R&D upgrades starting from Round 2 onward
        if self.current_round > 1:
            self._run_ai_rd_upgrades()

        cond = "WET / RAIN" if self.weekend_wetness > 0.15 else "DRY"
        fmt_tag = " [SPRINT WEEKEND]" if trk.is_sprint else ""
        self._push_event(
            "WEEKEND",
            f"ROUND {self.current_round}/24{fmt_tag}: Welcome to {trk.city} for the {self.season_year} {trk.name} ({cond}, {int(trk.rain_chance*100)}% rain risk)!",
        )

    def _apply_race_bans_if_any(self) -> None:
        self.temp_ban_subs = []
        free = sorted(self._free_agents(), key=driver_overall, reverse=True)
        for drv in list(self._active_drivers()):
            if drv.get("penalty_points", 0) >= 12 and free:
                sub = free.pop(0)
                team_id = drv["team_id"]
                t_short = self._teams_by_id()[team_id]["short"]
                drv["penalty_points"] = 0
                drv["team_id"] = None
                sub["team_id"] = team_id
                self.driver_points.setdefault(sub["id"], 0)
                self.driver_wins.setdefault(sub["id"], 0)
                self.driver_podiums.setdefault(sub["id"], 0)
                self.driver_poles.setdefault(sub["id"], 0)
                self.driver_dnfs.setdefault(sub["id"], 0)
                self.temp_ban_subs.append((drv["id"], sub["id"], team_id))
                self._push_event(
                    "PENALTY",
                    f"FIA 1-RACE BAN: {drv['name']} reached 12 Super Licence Penalty Points! Reserve {sub['name']} subs in at {t_short}!",
                )

    def _restore_race_bans(self) -> None:
        dmap = self._drivers_by_id()
        for reg_id, sub_id, team_id in self.temp_ban_subs:
            reg = dmap.get(reg_id)
            sub = dmap.get(sub_id)
            if reg and sub and sub["team_id"] == team_id and reg["team_id"] is None:
                sub["team_id"] = None
                reg["team_id"] = team_id
        self.temp_ban_subs = []

    def _run_ai_rd_upgrades(self) -> None:
        for team in self.teams:
            if team["id"] == self.player_team_id:
                continue
            if team["budget_m"] > 30.0 and random.random() < 0.42:
                candidates = [
                    (dept, lvl, upgrade_cost_m(dept, lvl))
                    for dept, lvl in team["upgrades"].items()
                    if lvl < UPGRADE_DEPARTMENTS[dept]["max_level"]
                ]
                affordable = [c for c in candidates if 0 < c[2] <= team["budget_m"] - 20.0]
                if affordable:
                    affordable.sort(key=lambda x: (x[1], x[2]))
                    dept, lvl, cost = random.choice(affordable[:3])
                    team["budget_m"] = round(team["budget_m"] - cost, 2)
                    team["upgrades"][dept] = lvl + 1
                    if lvl + 1 >= 8:
                        self._push_event(
                            "UPGRADE",
                            f"PADDOCK TECH: {team['short']} brings a major {UPGRADE_DEPARTMENTS[dept]['short']} Lv.{lvl+1} upgrade package!",
                        )

    def _start_sprint_qualifying(self) -> None:
        trk = self.current_track
        self.race_session = None
        self.quali_session = QualifyingSession(
            trk,
            self._teams_by_id(),
            self._active_drivers(),
            self.weekend_wetness,
            is_sprint_quali=True,
            regulations=self.regulations,
        )
        self.phase = "SPRINT_QUALIFYING"
        self._push_event(
            "RACE_CONTROL",
            f"SPRINT QUALIFYING (SQ1) GREEN LIGHT: 22 cars hit {trk.circuit} — bottom 6 eliminated in SQ1!",
        )

    def _ordered_grid_drivers(self, order_ids: list[str]) -> list[dict]:
        dmap = self._drivers_by_id()
        if order_ids:
            grid_drivers = [dmap[did] for did in order_ids if did in dmap and dmap[did]["team_id"] is not None]
        else:
            grid_drivers = self._active_drivers()
        in_grid = {d["id"] for d in grid_drivers}
        for d in self._active_drivers():
            if d["id"] not in in_grid:
                grid_drivers.append(d)
        return grid_drivers

    def _start_sprint_race(self) -> None:
        trk = self.current_track
        grid_drivers = self._ordered_grid_drivers(self.sprint_grid_order_ids)

        # Single rain event per race: probability of rain equals track rain_chance
        will_rain = random.random() < trk.rain_chance
        if will_rain:
            # 30% chance wet start, 70% chance single mid-race shower
            if random.random() < 0.30:
                sprint_wet = round(random.uniform(0.28, 0.65), 2)
            else:
                sprint_wet = 0.0
        else:
            sprint_wet = 0.0

        self.quali_session = None
        self.race_session = RaceSession(
            trk,
            self._teams_by_id(),
            grid_drivers,
            round(sprint_wet, 2),
            trk.rain_chance,
            self.player_team_id,
            is_sprint=True,
            regulations=self.regulations,
            starting_compounds=self.starting_compounds,
            rain_scheduled=will_rain,
        )
        self.phase = "SPRINT_RACE"
        self._push_event(
            "RACE_CONTROL",
            f"SPRINT RACE ({self.race_session.total_laps} LAPS): Top 8 score 8-7-6-5-4-3-2-1 Championship points — no mandatory stop!",
        )

    def _conclude_sprint_race(self) -> None:
        assert self.race_session is not None
        rs = self.race_session
        dmap = self._drivers_by_id()
        tmap = self._teams_by_id()

        team_repairs: dict[str, float] = {t["id"]: 0.0 for t in self.teams}
        team_pts_earned: dict[str, int] = {t["id"]: 0 for t in self.teams}

        for idx, car in enumerate(rs.standings):
            pts = SPRINT_POINTS[idx] if (idx < len(SPRINT_POINTS) and not car.dnf) else 0
            if pts > 0:
                self.driver_points[car.driver_id] = self.driver_points.get(car.driver_id, 0) + pts
                self.team_points[car.team_id] = self.team_points.get(car.team_id, 0) + pts
                team_pts_earned[car.team_id] += pts
            team_repairs[car.team_id] += car.repair_cost_m
            if car.driver_id in dmap:
                dmap[car.driver_id]["penalty_points"] = dmap[car.driver_id].get("penalty_points", 0) + car.penalty_points_added

        for team in self.teams:
            tid = team["id"]
            pts_bonus = team_pts_earned[tid] * 0.12
            repairs = team_repairs[tid]
            net = pts_bonus - repairs
            team["budget_m"] = round(max(1.5, team["budget_m"] + net), 2)
            if tid == self.player_team_id:
                if pts_bonus > 0.01:
                    self._log_ledger("SPRINT", f"R{self.current_round} Sprint Points Commercial Bonus", pts_bonus)
                if repairs > 0.01:
                    self._log_ledger("REPAIR", f"R{self.current_round} Sprint Carbon-Fibre Damage Repairs", -repairs)

        w = rs.standings[0]
        p2 = rs.standings[1]
        p3 = rs.standings[2]
        self.sprint_winner_code = w.code
        self._push_event(
            "PODIUM",
            f"SPRINT RESULT ({self.current_track.country}): P1 {w.name} ({w.team_short}, +8 pts) | P2 {p2.code} (+7) | P3 {p3.code} (+6)!",
        )
        self._save_state()
        # Parc Ferme re-opens -> advance into main Grand Prix Knockout Qualifying (Q1/Q2/Q3)
        self._start_qualifying()

    def _start_qualifying(self) -> None:
        trk = self.current_track
        self.race_session = None
        self.quali_session = QualifyingSession(
            trk,
            self._teams_by_id(),
            self._active_drivers(),
            self.weekend_wetness,
            is_sprint_quali=False,
            regulations=self.regulations,
        )
        self.phase = "QUALIFYING"
        self._push_event(
            "RACE_CONTROL",
            f"QUALIFYING (Q1) GREEN LIGHT: 22 cars hit {trk.circuit} — bottom 6 eliminated at the flag!",
        )

    def _finish_qualifying_to_grid(self) -> None:
        assert self.quali_session is not None
        self.grid_order_ids = [c.driver_id for c in self.quali_session.standings]
        pole_id = self.grid_order_ids[0]
        self.driver_poles[pole_id] = self.driver_poles.get(pole_id, 0) + 1
        self._prepare_race_grid()
        self.phase = "GRID_WALK"
        self.phase_timer = 18.0
        self.sim_speed = 1.0
        self._push_event(
            "RACE_CONTROL",
            f"STARTING GRID SET for the {self.current_track.name}! Cars rolling to their grid slots.",
        )

    def _prepare_race_grid(self) -> None:
        """Place the qualifying order once; grid walk and lights share these cars."""
        trk = self.current_track
        grid_drivers = self._ordered_grid_drivers(self.grid_order_ids)

        # Single rain event per race: probability of rain equals track rain_chance
        will_rain = random.random() < trk.rain_chance
        if will_rain:
            # 30% chance wet start, 70% chance single mid-race shower
            if random.random() < 0.30:
                race_wet = round(random.uniform(0.28, 0.65), 2)
            else:
                race_wet = 0.0
        else:
            race_wet = 0.0

        self.quali_session = None
        self.race_session = RaceSession(
            trk,
            self._teams_by_id(),
            grid_drivers,
            round(race_wet, 2),
            trk.rain_chance,
            self.player_team_id,
            is_sprint=False,
            regulations=self.regulations,
            starting_compounds=self.starting_compounds,
            rain_scheduled=will_rain,
        )

    def _start_race(self) -> None:
        if self.race_session is None or self.race_session.track is not self.current_track or self.race_session.is_sprint:
            self._prepare_race_grid()
        trk = self.current_track
        self.phase = "RACE"
        self._push_event("RACE_CONTROL", f"FIVE RED LIGHTS SEQUENCE: {self.season_year} {trk.name} ({trk.race_laps} Laps)!")

    def _conclude_race(self) -> None:
        assert self.race_session is not None
        rs = self.race_session
        dmap = self._drivers_by_id()
        sponsors_by_id = {s["id"]: s for s in SPONSORS}

        team_best_pos: dict[str, int] = {t["id"]: 99 for t in self.teams}
        team_pts_earned: dict[str, int] = {t["id"]: 0 for t in self.teams}
        team_repairs: dict[str, float] = {t["id"]: 0.0 for t in self.teams}

        classification = []
        for idx, car in enumerate(rs.standings):
            pos = idx + 1
            pts = RACE_POINTS[idx] if (idx < len(RACE_POINTS) and not car.dnf) else 0

            self.driver_points[car.driver_id] = self.driver_points.get(car.driver_id, 0) + pts
            self.team_points[car.team_id] = self.team_points.get(car.team_id, 0) + pts
            team_pts_earned[car.team_id] += pts
            team_repairs[car.team_id] += car.repair_cost_m

            if not car.dnf:
                team_best_pos[car.team_id] = min(team_best_pos[car.team_id], pos)
                if pos == 1:
                    self.driver_wins[car.driver_id] = self.driver_wins.get(car.driver_id, 0) + 1
                    self.team_wins[car.team_id] = self.team_wins.get(car.team_id, 0) + 1
                if pos <= 3:
                    self.driver_podiums[car.driver_id] = self.driver_podiums.get(car.driver_id, 0) + 1
            else:
                self.driver_dnfs[car.driver_id] = self.driver_dnfs.get(car.driver_id, 0) + 1

            if car.driver_id in dmap:
                dmap[car.driver_id]["penalty_points"] = dmap[car.driver_id].get("penalty_points", 0) + car.penalty_points_added

            classification.append(
                {
                    "pos": pos,
                    "driver_id": car.driver_id,
                    "code": car.code,
                    "name": car.name,
                    "number": car.number,
                    "team_id": car.team_id,
                    "team_short": car.team_short,
                    "team_color": car.team_color,
                    "points": pts,
                    "pit_stops": car.pit_stops,
                    "dnf": car.dnf,
                    "dnf_reason": car.dnf_reason,
                    "gap": "WINNER" if pos == 1 else ("DNF" if car.dnf else f"+{car.gap_to_leader:.3f}s"),
                }
            )

        for team in self.teams:
            tid = team["id"]
            sp = sponsors_by_id.get(team["sponsor_id"], SPONSORS[0])
            income = sp["base_per_race_m"]
            hit_bonus = team_best_pos[tid] <= sp["bonus_target_pos"]
            if hit_bonus:
                income += sp["bonus_payout_m"]
            pts_bonus = team_pts_earned[tid] * 0.14

            team_drivers = [d for d in self.drivers if d["team_id"] == tid]
            salaries_per_race = sum(d["salary_m"] / 24.0 for d in team_drivers)
            repairs = team_repairs[tid]

            net = income + pts_bonus - salaries_per_race - repairs
            team["budget_m"] = round(max(1.5, team["budget_m"] + net), 2)

            if tid == self.player_team_id:
                self._log_ledger(
                    "SPONSOR",
                    f"R{self.current_round} {sp['name']} {'(+Target Bonus!)' if hit_bonus else '(Base)'} & Points",
                    income + pts_bonus,
                )
                self._log_ledger("SALARY", f"R{self.current_round} Driver Payroll", -salaries_per_race)
                if repairs > 0.01:
                    self._log_ledger("REPAIR", f"R{self.current_round} Carbon-Fibre Crash Damage Repairs", -repairs)

        winner = classification[0]
        p2 = classification[1]
        p3 = classification[2]
        pole_code = dmap[self.grid_order_ids[0]]["code"] if self.grid_order_ids and self.grid_order_ids[0] in dmap else winner["code"]

        round_rec = {
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
        )
        self.last_podium_summary = {
            "round_rec": round_rec,
            "top10": classification[:10],
        }

        self._restore_race_bans()
        self.phase = "PODIUM"
        self.phase_timer = 13.0
        self._push_event(
            "PODIUM",
            f"PODIUM ({self.current_track.country}): P1 {winner['name']} ({winner['team_short']}) | P2 {p2['code']} | P3 {p3['code']}",
        )
        self._save_state()

    def _advance_after_podium(self) -> None:
        if self.current_round >= len(self.calendar):
            self._enter_off_season()
        else:
            self.current_round += 1
            self._begin_weekend()
            self._save_state()

    def _enter_off_season(self) -> None:
        self.phase = "OFF_SEASON"
        self.phase_timer = 15.0

        wdc = self.get_wdc_table()
        wcc = self.get_wcc_table()
        champ_drv = wdc[0]
        champ_team = wcc[0]
        self.reigning_wdc_id = champ_drv["id"]

        self.hall_of_fame.append(
            {
                "season": self.season_year,
                "wdc_name": champ_drv["name"],
                "wdc_code": champ_drv["code"],
                "wdc_team": champ_drv["team_short"],
                "wdc_points": champ_drv["points"],
                "wdc_wins": champ_drv["wins"],
                "wcc_name": champ_team["name"],
                "wcc_color": champ_team["color"],
                "wcc_points": champ_team["points"],
            }
        )

        tmap = self._teams_by_id()
        for rank_idx, row in enumerate(wcc):
            prize = WCC_PRIZE_POOL_M[min(rank_idx, len(WCC_PRIZE_POOL_M) - 1)] * 0.42
            team = tmap[row["id"]]
            team["budget_m"] = round(team["budget_m"] + prize, 2)
            if row["id"] == self.player_team_id:
                self._log_ledger(
                    "FIA PRIZE",
                    f"{self.season_year} FIA Constructors' P{rank_idx + 1} Championship Prize Payout",
                    prize,
                )

        sync_live_season_status(
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
        )
        self._save_state()

    def _adjust_driver_scores_from_performance(self, wdc: list[dict], wcc: list[dict]) -> None:
        """Adjust driver scores (pace, racecraft, consistency, tire_mgmt, defense) and market values
        based on their actual on-track performance in the concluded championship season."""
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
            top_ups = [f"{name} ({team} {new_ovr:.0f} OVR, {diff:+.1f})" for name, team, old, new_ovr, diff in upgraded_drivers[:3]]
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

    def _start_next_season(self) -> None:
        self._legacy_calendar = False
        wdc_table = self.get_wdc_table()
        wcc_table = self.get_wcc_table()
        self._adjust_driver_scores_from_performance(wdc_table, wcc_table)

        free_pool = sorted(self._free_agents(), key=driver_overall, reverse=True)
        for d in self.drivers:
            d["age"] += 1
            d["penalty_points"] = max(0, d.get("penalty_points", 0) - 6)
            if d["team_id"] is not None and d["contract_years"] > 0:
                d["contract_years"] -= 1

            if d["age"] >= 42 and d["team_id"] is not None and d["team_id"] != self.player_team_id and free_pool:
                    if random.random() < 0.45:
                        rep = free_pool.pop(0)
                        tid = d["team_id"]
                        t_short = self._teams_by_id()[tid]["short"]
                        d["team_id"] = None
                        rep["team_id"] = tid
                        rep["contract_years"] = 2
                        self._push_event("TRANSFER", f"RETIREMENT: {d['name']} steps back; {t_short} signs {rep['name']}!")

        ai_expiring = [
            d for d in self._active_drivers()
            if d["team_id"] != self.player_team_id and d["contract_years"] <= 0
        ]
        for d in ai_expiring:
            if random.random() < 0.35 and free_pool:
                cand = free_pool[0]
                if driver_overall(cand) >= driver_overall(d) - 1.5:
                    free_pool.pop(0)
                    tid = d["team_id"]
                    t_short = self._teams_by_id()[tid]["short"]
                    d["team_id"] = None
                    d["contract_years"] = 0
                    cand["team_id"] = tid
                    cand["contract_years"] = 2
                    free_pool.append(d)
                    self._push_event("TRANSFER", f"SILLY SEASON: {t_short} signs {cand['name']}, releasing {d['name']}!")
                else:
                    d["contract_years"] = 2
            else:
                d["contract_years"] = 2

        for d in self._active_drivers():
            if d["contract_years"] <= 0:
                d["contract_years"] = 1

        prev_year = self.season_year
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
        sync_live_season_status(
            self.season_archives,
            self.season_year,
            self.current_round,
            len(self.calendar),
            self.phase,
            self.get_wdc_table(),
            self.get_wcc_table(),
        )
        self._begin_weekend()
        self._save_state()

    # -------------------------------------------------------------------------
    # Team Principal Commands & Negotiations
    # -------------------------------------------------------------------------
    def select_team(self, team_id: str) -> dict:
        with self.lock:
            tmap = self._teams_by_id()
            if team_id not in tmap:
                return {"ok": False, "error": "Unknown team."}
            self.player_team_id = team_id
            team = tmap[team_id]
            self._log_ledger("TEAM", f"Took command as Team Principal of {team['name']}", 0.0)
            self._push_event("NEWS", f"TEAM PRINCIPAL APPOINTED: New leadership takes charge on the {team['short']} Pit Wall!")
            self._save_state()
            return {"ok": True, "team_id": team_id}

    def buy_upgrade(self, dept_key: str) -> dict:
        with self.lock:
            if dept_key not in UPGRADE_DEPARTMENTS:
                return {"ok": False, "error": "Invalid R&D department."}
            team = self._teams_by_id()[self.player_team_id]
            cur_lvl = team["upgrades"][dept_key]
            spec = UPGRADE_DEPARTMENTS[dept_key]
            if cur_lvl >= spec["max_level"]:
                return {"ok": False, "error": f"{spec['short']} is already at maximum FIA development level ({spec['max_level']})."}
            cost = upgrade_cost_m(dept_key, cur_lvl)
            if team["budget_m"] < cost:
                return {"ok": False, "error": f"Insufficient budget: need ${cost:.2f}M (available ${team['budget_m']:.2f}M)."}

            team["budget_m"] = round(team["budget_m"] - cost, 2)
            new_lvl = cur_lvl + 1
            team["upgrades"][dept_key] = new_lvl
            new_perf = team_car_rating(team)

            if self.race_session:
                for c in self.race_session.cars:
                    if c.team_id == self.player_team_id:
                        c.upgrades[dept_key] = new_lvl
                        c.car_perf_index = new_perf
            if self.quali_session:
                for c in self.quali_session.cars:
                    if c.team_id == self.player_team_id:
                        c.upgrades[dept_key] = new_lvl
                        c.car_perf_index = new_perf

            self._log_ledger("R&D UPGRADE", f"Upgraded {spec['name']} to Lv.{new_lvl}", -cost)
            self._push_event("UPGRADE", f"FACTORY UPGRADE: {team['short']} deploys {spec['short']} Lv.{new_lvl} (-${cost:.1f}M)!")
            self._save_state()
            return {"ok": True, "dept": dept_key, "level": new_lvl, "budget_m": team["budget_m"]}

    def evaluate_trade(self, my_driver_id: str, target_driver_id: str, cash_offer_m: float) -> dict:
        with self.lock:
            if not self.is_transfer_window_open():
                return {
                    "ok": False,
                    "error": "Transfer window is currently LOCKED. FIA regulations permit driver trades and free agent signings only at the start of each season (Round 1 or Off-Season).",
                }
            dmap = self._drivers_by_id()
            tmap = self._teams_by_id()
            my_drv = dmap.get(my_driver_id)
            tgt_drv = dmap.get(target_driver_id)
            if not my_drv or not tgt_drv:
                return {"ok": False, "error": "Driver not found."}
            if my_drv["team_id"] != self.player_team_id:
                return {"ok": False, "error": "Selected outgoing driver is not on your team."}
            if tgt_drv["team_id"] is None or tgt_drv["team_id"] == self.player_team_id:
                return {"ok": False, "error": "Target driver must belong to a rival Constructor."}

            my_team = tmap[self.player_team_id]
            rival_team = tmap[tgt_drv["team_id"]]

            my_ovr = driver_overall(my_drv)
            tgt_ovr = driver_overall(tgt_drv)
            youth_diff = max(0, 28 - tgt_drv["age"]) * 1.1 - max(0, 28 - my_drv["age"]) * 1.1
            contract_friction = tgt_drv["contract_years"] * 3.2 + 2.5
            required_cash_m = round(
                (tgt_drv["value_m"] - my_drv["value_m"])
                + (tgt_ovr - my_ovr) * 1.35
                + youth_diff
                + contract_friction,
                1,
            )

            can_player_afford = cash_offer_m <= my_team["budget_m"]
            can_rival_afford = (-cash_offer_m) <= (rival_team["budget_m"] - 12.0)
            accepted = (cash_offer_m >= required_cash_m) and can_player_afford and can_rival_afford

            if not can_player_afford:
                reason = f"Your budget (${my_team['budget_m']:.1f}M) cannot cover a ${cash_offer_m:.1f}M cash offer."
            elif not can_rival_afford:
                reason = f"{rival_team['short']} refuses to pay out ${-cash_offer_m:.1f}M in cash."
            elif accepted:
                reason = f"{rival_team['short']} Team Principal agrees! Package meets their ${required_cash_m:.1f}M valuation."
            else:
                shortfall = round(required_cash_m - cash_offer_m, 1)
                reason = f"{rival_team['short']} rejects: demands at least ${required_cash_m:.1f}M cash (+${shortfall:.1f}M more)."

            return {
                "ok": True,
                "accepted": accepted,
                "required_cash_m": required_cash_m,
                "rival_team": rival_team["short"],
                "my_ovr": my_ovr,
                "tgt_ovr": tgt_ovr,
                "reason": reason,
            }

    def execute_trade(self, my_driver_id: str, target_driver_id: str, cash_offer_m: float) -> dict:
        with self.lock:
            if not self.is_transfer_window_open():
                return {
                    "ok": False,
                    "error": "Transfer window is currently LOCKED. FIA regulations permit driver trades and free agent signings only at the start of each season (Round 1 or Off-Season).",
                }
            eval_res = self.evaluate_trade(my_driver_id, target_driver_id, cash_offer_m)
            if not eval_res.get("ok"):
                return eval_res
            if not eval_res["accepted"]:
                return {"ok": False, "error": eval_res["reason"]}

            dmap = self._drivers_by_id()
            tmap = self._teams_by_id()
            my_drv = dmap[my_driver_id]
            tgt_drv = dmap[target_driver_id]
            my_team = tmap[self.player_team_id]
            rival_team = tmap[tgt_drv["team_id"]]

            my_team["budget_m"] = round(my_team["budget_m"] - cash_offer_m, 2)
            rival_team["budget_m"] = round(rival_team["budget_m"] + cash_offer_m, 2)
            my_drv["team_id"] = rival_team["id"]
            tgt_drv["team_id"] = my_team["id"]
            my_drv["contract_years"] = max(2, my_drv["contract_years"])
            tgt_drv["contract_years"] = max(2, tgt_drv["contract_years"])

            cash_str = (
                f" + ${cash_offer_m:.1f}M cash" if cash_offer_m > 0 else (f" (receiving ${-cash_offer_m:.1f}M)" if cash_offer_m < 0 else "")
            )
            self._log_ledger(
                "DRIVER TRADE",
                f"Traded {my_drv['code']} to {rival_team['short']} for {tgt_drv['name']}",
                -cash_offer_m,
            )
            self._push_event(
                "TRANSFER",
                f"BREAKING TRADE: {my_team['short']} acquires #{tgt_drv['number']} {tgt_drv['name']} from {rival_team['short']} for {my_drv['name']}{cash_str}!",
            )
            self._save_state()
            return {"ok": True, "message": f"{tgt_drv['name']} signed! Takes the wheel starting next session."}

    def sign_free_agent(self, release_driver_id: str, free_agent_id: str) -> dict:
        with self.lock:
            if not self.is_transfer_window_open():
                return {
                    "ok": False,
                    "error": "Transfer window is currently LOCKED. FIA regulations permit driver trades and free agent signings only at the start of each season (Round 1 or Off-Season).",
                }
            dmap = self._drivers_by_id()
            tmap = self._teams_by_id()
            rel = dmap.get(release_driver_id)
            fa = dmap.get(free_agent_id)
            if not rel or not fa:
                return {"ok": False, "error": "Driver not found."}
            if rel["team_id"] != self.player_team_id:
                return {"ok": False, "error": "Outgoing driver is not on your team."}
            if fa["team_id"] is not None:
                return {"ok": False, "error": "Driver is already contracted to a team."}

            my_team = tmap[self.player_team_id]
            buyout_m = round(rel["salary_m"] * max(1, rel["contract_years"]) * 0.25, 2)
            signing_fee_m = round(fa["value_m"] * 0.30, 2)
            total_cost_m = round(buyout_m + signing_fee_m, 2)

            if my_team["budget_m"] < total_cost_m:
                return {
                    "ok": False,
                    "error": f"Need ${total_cost_m:.2f}M (${buyout_m:.1f}M buyout + ${signing_fee_m:.1f}M signing bonus).",
                }

            my_team["budget_m"] = round(my_team["budget_m"] - total_cost_m, 2)
            rel["team_id"] = None
            rel["contract_years"] = 0
            fa["team_id"] = self.player_team_id
            fa["contract_years"] = 2

            self.driver_points.setdefault(fa["id"], 0)
            self.driver_wins.setdefault(fa["id"], 0)
            self.driver_podiums.setdefault(fa["id"], 0)
            self.driver_poles.setdefault(fa["id"], 0)
            self.driver_dnfs.setdefault(fa["id"], 0)

            self._log_ledger(
                "SIGNING",
                f"Signed {fa['name']} & bought out {rel['name']} (-${total_cost_m:.1f}M)",
                -total_cost_m,
            )
            self._push_event(
                "TRANSFER",
                f"DRIVER SIGNING: {my_team['short']} signs Free Agent #{fa['number']} {fa['name']}, releasing {rel['name']}!",
            )
            self._save_state()
            return {"ok": True, "cost_m": total_cost_m}

    def select_sponsor(self, sponsor_id: str) -> dict:
        with self.lock:
            sp = next((s for s in SPONSORS if s["id"] == sponsor_id), None)
            if not sp:
                return {"ok": False, "error": "Unknown sponsor."}
            my_team = self._teams_by_id()[self.player_team_id]
            my_team["sponsor_id"] = sponsor_id
            self._log_ledger("SPONSOR", f"Signed commercial deal with {sp['name']}", 0.0)
            self._push_event("NEWS", f"COMMERCIAL DEAL: {my_team['short']} partners with {sp['name']}!")
            self._save_state()
            return {"ok": True}

    def pit_wall_command(self, driver_id: str, cmd: dict) -> dict:
        with self.lock:
            if not self.race_session:
                return {"ok": False, "error": "Pit Wall radio is active during Sprint and Grand Prix races."}
            car = self.race_session.cars_by_id.get(driver_id)
            if not car or car.team_id != self.player_team_id:
                return {"ok": False, "error": "Can only issue Pit Wall orders to your own team's cars."}

            if "auto_strategy" in cmd:
                car.auto_strategy = bool(cmd["auto_strategy"])
            if "start_compound" in cmd and cmd["start_compound"] in TIRE_COMPOUNDS:
                comp = cmd["start_compound"]
                self.starting_compounds[driver_id] = comp
                car.compound = comp
                car.next_compound = comp
                car.compounds_used = {comp}
                car.tire_age_laps = 0
                car.tire_wear = 0.01
                self._push_event("RADIO", f"GRID CALL: #{car.number} {car.code} fitted with {comp} tyres for race start!")
            elif "next_compound" in cmd and cmd["next_compound"] in TIRE_COMPOUNDS:
                comp = cmd["next_compound"]
                car.next_compound = comp
                # If race has not launched yet (standing on grid or lights sequence), also update starting compound!
                if self.phase in ("GRID_WALK", "PRE_WEEKEND") or (self.race_session and (self.race_session.flag_state in ("GRID", "LIGHTS") or self.race_session.lights_countdown > 0 or (car.lap <= 1 and car.v < 10.0))):
                    car.compound = comp
                    car.compounds_used = {comp}
                    car.tire_age_laps = 0
                    car.tire_wear = 0.01
                    self.starting_compounds[driver_id] = comp
                    self._push_event("RADIO", f"GRID STRATEGY: #{car.number} {car.code} starting tyres switched to {comp}!")
            if "box_this_lap" in cmd:
                car.box_this_lap = bool(cmd["box_this_lap"])
                if car.box_this_lap and not car.radio_box_announced:
                    self.race_session.radio_dispatcher.trigger_box_call(
                        car, self._push_event, self.race_session.race_clock, is_pit_wall=True
                    )
                car.radio_box_announced = car.box_this_lap
                if not car.box_this_lap:
                    car.inlap_push_announced = False
            if "pace_mode" in cmd and cmd["pace_mode"] in ("CONSERVE", "BALANCED", "PUSH", "ATTACK"):
                old_pace = getattr(car, "pace_mode", "BALANCED")
                car.pace_mode = cmd["pace_mode"]
                if self.race_session and hasattr(self.race_session, "radio_dispatcher"):
                    clk = getattr(self.race_session, "race_clock", 0.0)
                    trk = getattr(self.race_session, "track", None)
                    turn = trk.nearest_corner(car.s) if trk and hasattr(trk, "nearest_corner") else 1
                    if car.pace_mode in ("PUSH", "ATTACK") and old_pace != car.pace_mode:
                        self.race_session.radio_dispatcher.trigger_push_mode(
                            car, car.pace_mode, is_pit_wall=True, event_cb=self._push_event, clock=clk, turn=turn,
                            flag_state=self.race_session.flag_state
                        )
                    elif car.pace_mode == "CONSERVE" and old_pace != car.pace_mode:
                        self.race_session.radio_dispatcher.trigger_conserve_mode(
                            car, event_cb=self._push_event, clock=clk, turn=turn, is_pit_wall=True
                        )
            if "ers_mode" in cmd and cmd["ers_mode"] in ("HARVEST", "AUTO", "BOOST", "OVERTAKE"):
                old_ers = getattr(car, "ers_mode", "AUTO")
                car.ers_mode = cmd["ers_mode"]
                if self.race_session and hasattr(self.race_session, "radio_dispatcher"):
                    clk = getattr(self.race_session, "race_clock", 0.0)
                    trk = getattr(self.race_session, "track", None)
                    turn = trk.nearest_corner(car.s) if trk and hasattr(trk, "nearest_corner") else 1
                    if car.ers_mode in ("BOOST", "OVERTAKE") and old_ers != car.ers_mode:
                        self.race_session.radio_dispatcher.trigger_push_mode(
                            car, car.ers_mode, is_pit_wall=True, event_cb=self._push_event, clock=clk, turn=turn,
                            flag_state=self.race_session.flag_state
                        )
                    elif car.ers_mode == "HARVEST" and old_ers != car.ers_mode:
                        self.race_session.radio_dispatcher.trigger_conserve_mode(
                            car, event_cb=self._push_event, clock=clk, turn=turn,
                            is_pit_wall=True, mode_name="HARVEST"
                        )
            if "team_order" in cmd and cmd["team_order"] in ("FREE", "HOLD", "YIELD", "SWAP"):
                order = "YIELD" if cmd["team_order"] == "SWAP" else cmd["team_order"]
                teammate = None
                if self.race_session:
                    teammate = next(
                        (c for c in self.race_session.cars if c.team_id == car.team_id and c.driver_id != car.driver_id and not c.dnf),
                        None,
                    )
                if order == "YIELD":
                    # Determine which car is ahead and which is behind; the ahead car yields
                    if teammate:
                        if car.total_dist >= teammate.total_dist:
                            ahead_car = car
                            behind_car = teammate
                        else:
                            ahead_car = teammate
                            behind_car = car
                        ahead_car.team_order = "YIELD"
                        behind_car.team_order = "FREE"
                        ahead_car.swap_target_id = behind_car.driver_id
                        behind_car.swap_pass_id = ahead_car.driver_id
                        self._push_event(
                            "RADIO",
                            f"TEAM ORDERS RADIO ({car.team_short}): #{ahead_car.number} {ahead_car.code} instructed to swap positions and let #{behind_car.number} {behind_car.code} pass.",
                        )
                    else:
                        car.team_order = "YIELD"
                elif order == "HOLD":
                    car.team_order = "HOLD"
                    self._push_event("RADIO", f"TEAM ORDERS RADIO ({car.team_short}): #{car.number} {car.code} instructed to hold station.")
                elif order == "FREE":
                    car.team_order = "FREE"
                    if teammate and getattr(teammate, "swap_target_id", None) == car.driver_id:
                        teammate.team_order = "FREE"
                        teammate.swap_target_id = None
                    car.swap_target_id = None
                    car.swap_pass_id = None
                    self._push_event("RADIO", f"TEAM ORDERS RADIO ({car.team_short}): #{car.number} {car.code} instructed free to race.")

            return {"ok": True}

    def set_sim_speed(self, speed: float) -> dict:
        with self.lock:
            allowed = [0.0, 0.5, 1.0, 2.0, 4.0, 8.0, 16.0]
            best = min(allowed, key=lambda v: abs(v - float(speed)))
            self.sim_speed = best
            return {"ok": True, "sim_speed": self.sim_speed}

    def skip_session(self) -> dict:
        """Advance current session or knockout stage immediately (works in every phase, even when paused)."""
        with self.lock:
            if self.phase == "PRE_WEEKEND":
                if self.current_track.is_sprint:
                    self._start_sprint_qualifying()
                else:
                    self._start_qualifying()

            elif self.phase == "SPRINT_QUALIFYING" and self.quali_session:
                self.quali_session.advance_stage(self._push_event)
                if self.quali_session.finished:
                    self.sprint_grid_order_ids = [c.driver_id for c in self.quali_session.standings]
                    self._start_sprint_race()

            elif self.phase == "SPRINT_RACE" and self.race_session:
                guard = 0
                while not self.race_session.finished and guard < 12000:
                    self.race_session.step(0.35, self._push_event)
                    guard += 1
                if not self.race_session.finished:
                    self.race_session.finished = True
                self._conclude_sprint_race()

            elif self.phase == "QUALIFYING" and self.quali_session:
                self.quali_session.advance_stage(self._push_event)
                if self.quali_session.finished:
                    self._finish_qualifying_to_grid()

            elif self.phase == "GRID_WALK":
                self._start_race()

            elif self.phase == "RACE" and self.race_session:
                guard = 0
                while not self.race_session.finished and guard < 22000:
                    self.race_session.step(0.35, self._push_event)
                    guard += 1
                if not self.race_session.finished:
                    self.race_session.finished = True
                self._conclude_race()

            elif self.phase == "PODIUM":
                self._advance_after_podium()

            elif self.phase == "OFF_SEASON":
                self._start_next_season()

            return {"ok": True, "phase": self.phase}

    def reset_career(self, team_id: str = "williams", start_year: int = 2026) -> dict:
        with self.lock:
            t_id = team_id if team_id in self._teams_by_id() else "williams"
            year = 2028 if int(start_year) == 2028 else 2026
            self._init_fresh_career(t_id, start_year=year)
            self._begin_weekend()
            self._save_state()
            return {"ok": True, "season_year": self.season_year}

    # -------------------------------------------------------------------------
    # Serialization for Live SSE Stream & Management Views
    # -------------------------------------------------------------------------
    def get_wdc_table(self) -> list[dict]:
        tmap = self._teams_by_id()
        rows = []
        for d in self.drivers:
            pts = self.driver_points.get(d["id"], 0)
            wins = self.driver_wins.get(d["id"], 0)
            if d["team_id"] is None and pts == 0 and wins == 0:
                continue
            team = tmap.get(d["team_id"]) if d["team_id"] else None
            rows.append(
                {
                    "id": d["id"],
                    "name": d["name"],
                    "code": d["code"],
                    "number": d["number"],
                    "team_id": d["team_id"],
                    "team_short": team["short"] if team else "Reserve",
                    "team_color": team["color"] if team else "#64748b",
                    "points": pts,
                    "wins": wins,
                    "podiums": self.driver_podiums.get(d["id"], 0),
                    "poles": self.driver_poles.get(d["id"], 0),
                    "dnfs": self.driver_dnfs.get(d["id"], 0),
                    "penalty_points": d.get("penalty_points", 0),
                    "overall": driver_overall(d),
                        "last_ovr_change": d.get("last_ovr_change", 0.0),
                }
            )
        rows.sort(key=lambda r: (-r["points"], -r["wins"], -r["podiums"], -r["overall"]))
        for idx, r in enumerate(rows):
            r["rank"] = idx + 1
        return rows

    def get_wcc_table(self) -> list[dict]:
        rows = []
        for t in self.teams:
            tid = t["id"]
            rows.append(
                {
                    "id": tid,
                    "name": t["name"],
                    "short": t["short"],
                    "code": t["code"],
                    "engine": t["engine"],
                    "color": t["color"],
                    "points": self.team_points.get(tid, 0),
                    "wins": self.team_wins.get(tid, 0),
                    "car_rating": team_car_rating(t),
                    "budget_m": round(t["budget_m"], 2),
                }
            )
        rows.sort(key=lambda r: (-r["points"], -r["wins"], -r["car_rating"]))
        for idx, r in enumerate(rows):
            r["rank"] = idx + 1
        return rows

    def build_live_tick_payload(self) -> dict:
        """Compact 20Hz live frame streamed via SSE to all connected browser tabs."""
        with self.lock:
            trk = self.current_track
            cars_payload = []
            flag = "GREEN"
            yellow_sec = None
            wetness = self.weekend_wetness
            lap_cur = 0
            lap_tot = trk.race_laps
            clock = 0.0
            lights = 0.0
            sc_data = None
            fastest_id = None
            fastest_time = None
            quali_stage = ""
            quali_cut = 0

            active_cars: list = []
            maneuver_session = None
            if self.phase in ("GRID_WALK", "RACE", "SPRINT_RACE") and self.race_session:
                rs = self.race_session
                maneuver_session = rs
                active_cars = rs.standings
                flag = rs.flag_state
                yellow_sec = rs.yellow_sector
                wetness = rs.wetness
                lap_cur = rs.standings[0].lap if rs.standings else 1
                lap_tot = rs.total_laps
                clock = round(rs.race_clock, 1)
                lights = round(max(0.0, rs.lights_countdown), 2)
                fastest_id = rs.fastest_lap_driver_id
                fastest_time = rs.fastest_lap_time
                if self.phase == "GRID_WALK":
                    flag = "GRID"
                    lap_cur = 0
                    lights = 0.0
                if rs.flag_state == "SC":
                    sc_data = {"x": rs.sc_x, "y": rs.sc_y, "h": rs.sc_heading, "in_lap": rs.sc_in_this_lap}
            elif self.phase in ("QUALIFYING", "SPRINT_QUALIFYING") and self.quali_session:
                qs = self.quali_session
                active_cars = qs.standings
                flag = "GREEN"
                wetness = qs.wetness
                clock = round(qs.stage_time_left, 1)
                fastest_id = qs.fastest_driver_id
                fastest_time = qs.fastest_time
                quali_stage = qs.stage_name
                quali_cut = qs.cut_line

            sector_bests = [
                min((c.best_sector_times[i] for c in active_cars
                     if not c.eliminated and c.best_sector_times[i] is not None), default=None)
                for i in range(3)
            ]
            for c in active_cars:
                cars_payload.append(
                    {
                        "id": c.driver_id,
                        "code": c.code,
                        "name": c.name,
                        "num": c.number,
                        "tid": c.team_id,
                        "tcol": c.team_color,
                        "scol": c.secondary_color,
                        "helm": c.helmet,
                        "pos": c.pos,
                        "grid": c.grid_pos,
                        "x": c.x,
                        "y": c.y,
                        "h": c.heading,
                        "kph": int(round(c.v * 3.6)),
                        "lap": c.lap,
                        "braking": c.braking,
                        "sparks": c.sparks,
                        "smoke": round(c.smoke, 1),
                        "aero": c.aero_mode,
                        "ovt_elig": c.overtake_eligible,
                        "ovt": c.overtake_active,
                        "drs_elig": getattr(c, "drs_eligible", False),
                        "drs": getattr(c, "drs_active", False),
                        "boost": c.boost_active,
                        "rech": c.recharging,
                        "bat": max(0, min(100, int(round((c.battery_mj / max(getattr(c, "max_battery_mj", 4.0), 0.1)) * 100)))),
                        "comp": c.compound,
                        "wear": int(round(c.tire_wear * 100)),
                        "tage": c.tire_age_laps,
                        "ttemp": int(round(c.tire_temp)),
                        "dmg": int(round(c.wing_damage * 100)),
                        "dmg_side": getattr(c, "wing_damage_side", "NONE"),
                        "steer": round(getattr(c, "steer_angle", 0.0), 3),
                        "slip": round(getattr(c, "body_slip_angle", 0.0), 3),
                        "g_lat": round(getattr(c, "g_lat", 0.0), 2),
                        "pits": c.pit_stops,
                        "lpit": c.last_pit_duration,
                        "in_pit": c.in_pits,
                        "pit_ph": c.pit_phase,
                        "pit_tunnel": in_pit_tunnel(trk, c),
                        "box": c.box_this_lap,
                        "ncomp": c.next_compound,
                        "auto": c.auto_strategy,
                        "pace": c.pace_mode,
                        "ers": c.ers_mode,
                        "order": c.team_order,
                        "pen": c.time_penalty_s,
                        "dt_pen": c.drive_through_pending,
                        "blue_flag": getattr(c, "blue_flag", False),
                        "tl": c.track_limits_strikes,
                        "gap": c.gap_to_leader,
                        "intv": c.interval_ahead,
                        "last": c.last_lap_time,
                        "best": c.best_lap_time,
                        "sectors": c.current_sector_times[:],
                        "last_sectors": c.last_sector_times[:],
                        "best_sectors": c.best_sector_times[:],
                        "dnf": c.dnf,
                        "dnf_r": c.dnf_reason,
                        "vis": (not c.dnf) or (c.dnf_timer > 0),
                        "battle": c.battle_with,
                        "man": maneuver_session.display_maneuver(c) if maneuver_session else c.maneuver,
                        "elim": c.eliminated,
                        "estg": c.elim_stage,
                    }
                )

            p_team = self._teams_by_id()[self.player_team_id]
            return {
                "tick": self.tick_counter,
                "season": self.season_year,
                "round": self.current_round,
                "total_rounds": len(self.calendar),
                "track_id": trk.id,
                "gp_name": trk.name,
                "circuit_name": trk.circuit,
                "city": trk.city,
                "country": trk.country,
                "is_sprint_weekend": trk.is_sprint,
                "sprint_laps": trk.sprint_laps,
                "track_width_m": trk.track_width_m,
                "phase": self.phase,
                "phase_timer": round(max(0.0, self.phase_timer), 1),
                "quali_stage": quali_stage,
                "quali_cut": quali_cut,
                "sim_speed": self.sim_speed,
                "sim_time": round(time.time(), 4),
                "flag": flag,
                "yellow_sector": yellow_sec,
                "wetness": int(round(wetness * 100)),
                "rain_risk": int(round(trk.rain_chance * 100)),
                "temp_c": int(round(trk.base_temp_c)),
                "lap": lap_cur,
                "total_laps": lap_tot,
                "clock": clock,
                "lights": lights,
                "fastest_id": fastest_id,
                "fastest_time": fastest_time,
                "sector_bests": sector_bests,
                "sc": sc_data,
                "player_team_id": self.player_team_id,
                "player_team_short": p_team["short"],
                "player_team_color": p_team["color"],
                "player_budget_m": round(p_team["budget_m"], 2),
                "cars": cars_payload,
                "events": self.event_feed[-60:],
                "podium": self.last_podium_summary,
                "regulations": self.regulations,
                "transfer_window_open": self.is_transfer_window_open(),
            }

    def build_full_state_payload(self) -> dict:
        """Full Championship, HQ, R&D, Driver Market, Sponsors & Current Track geometry."""
        with self.lock:
            p_team = self._teams_by_id()[self.player_team_id]
            upgrades_info = []
            for key, spec in UPGRADE_DEPARTMENTS.items():
                lvl = p_team["upgrades"][key]
                upgrades_info.append(
                    {
                        "key": key,
                        "name": spec["name"],
                        "short": spec["short"],
                        "code": spec["code"],
                        "desc": spec["desc"],
                        "level": lvl,
                        "max_level": spec["max_level"],
                        "cost_m": upgrade_cost_m(key, lvl),
                    }
                )

            all_drivers = []
            tmap = self._teams_by_id()
            for d in self.drivers:
                tm = tmap.get(d["team_id"]) if d["team_id"] else None
                buyout_m = round(d["salary_m"] * max(1, d["contract_years"]) * 0.25, 2) if d["team_id"] else 0.0
                signing_m = round(d["value_m"] * 0.30, 2) if d["team_id"] is None else 0.0
                all_drivers.append(
                    {
                        **d,
                        "overall": driver_overall(d),
                        "team_short": tm["short"] if tm else "Free Agent",
                        "team_color": tm["color"] if tm else "#64748b",
                        "points": self.driver_points.get(d["id"], 0),
                        "wins": self.driver_wins.get(d["id"], 0),
                        "buyout_m": buyout_m,
                        "signing_m": signing_m,
                    }
                )
            all_drivers.sort(key=lambda x: (-x["overall"], x["age"]))

            teams_summary = [
                {
                    **t,
                    "car_rating": team_car_rating(t),
                    "points": self.team_points.get(t["id"], 0),
                    "wins": self.team_wins.get(t["id"], 0),
                }
                for t in self.teams
            ]
            teams_summary.sort(key=lambda x: -x["car_rating"])

            return {
                "season": self.season_year,
                "round": self.current_round,
                "player_team_id": self.player_team_id,
                "player_team": {**p_team, "car_rating": team_car_rating(p_team)},
                "upgrades": upgrades_info,
                "teams": teams_summary,
                "drivers": all_drivers,
                "sponsors": SPONSORS,
                "wdc": self.get_wdc_table(),
                "wcc": self.get_wcc_table(),
                "calendar_info": calendar_status(self.season_year, self._legacy_calendar),
                "calendar": [
                    {
                        "id": t.id,
                        "round": t.round,
                        "name": t.name,
                        "circuit": t.circuit,
                        "city": t.city,
                        "country": t.country,
                        "laps": t.race_laps,
                        "is_sprint": t.is_sprint,
                        "sprint_laps": t.sprint_laps,
                        "track_width_m": t.track_width_m,
                        "result": next((r for r in self.calendar_results if r["round"] == t.round), None),
                    }
                    for t in self.calendar
                ],
                "hall_of_fame": list(reversed(self.hall_of_fame)),
                "ledger": list(reversed(self.ledger[-40:])),
                "track": self.current_track.to_client_payload(),
                "regulations": self.regulations,
                "transfer_window_open": self.is_transfer_window_open(),
                "starting_compounds": self.starting_compounds,
                "season_archives": self.get_hall_of_fame_data(),
            }


    def get_hall_of_fame_data(self) -> dict:
        with self.lock:
            if not getattr(self, "season_archives", None):
                self.season_archives = generate_default_season_archives()
            return {
                "available_years": [2026, 2027, 2028, 2029, 2030],
                "current_year": self.season_year,
                "seasons": self.season_archives,
            }
