"""Authentic FIA Formula 1 Hall of Fame & Multi-Season Results Archives (2026-2030).

Provides complete race-by-race results, podiums, poles, fastest laps, and final classifications
for all Formula 1 seasons from 2026 through 2030, with seamless live career overwriting.
"""

from __future__ import annotations
import copy
from typing import Any

from sim.tracks import get_season_tracks
from sim.data import INITIAL_TEAMS, INITIAL_DRIVERS, RACE_POINTS, SPRINT_POINTS

# Quick lookup maps
TEAMS_MAP = {t["id"]: copy.deepcopy(t) for t in INITIAL_TEAMS}
DRIVERS_MAP = {d["id"]: copy.deepcopy(d) for d in INITIAL_DRIVERS}

# Canonical season narrative configurations for 2026 - 2030
SEASON_PRESETS: dict[int, dict[str, Any]] = {
    2026: {
        "era_name": "Active Aero Turbo-Hybrid Era",
        "engine_type": "1.6L V6 Turbo Hybrid + 350kW MGU-K",
        "has_active_aero": True,
        "has_classic_drs": False,
        "wdc_id": "norris",
        "wdc_name": "Lando Norris",
        "wdc_code": "NOR",
        "wdc_num": 4,
        "wdc_team": "McLaren",
        "wdc_team_id": "mclaren",
        "wdc_color": "#ff8000",
        "wdc_points": 412,
        "wdc_wins": 8,
        "wdc_podiums": 16,
        "wdc_poles": 7,
        "wcc_id": "mclaren",
        "wcc_name": "McLaren Formula 1 Team",
        "wcc_short": "McLaren",
        "wcc_color": "#ff8000",
        "wcc_engine": "Mercedes",
        "wcc_points": 724,
        "wcc_wins": 12,
        "narrative": "McLaren & Lando Norris capture their first modern World Championship in the debut season of Active Aero & Manual Override regulations.",
        "win_order": ["norris", "verstappen", "piastri", "leclerc", "norris", "norris", "verstappen", "leclerc", "norris", "russell", "norris", "verstappen", "piastri", "norris", "leclerc", "verstappen", "piastri", "norris", "norris", "leclerc", "hamilton", "verstappen", "piastri", "norris"],
    },
    2027: {
        "era_name": "Active Aero Turbo-Hybrid Era",
        "engine_type": "1.6L V6 Turbo Hybrid + 350kW MGU-K",
        "has_active_aero": True,
        "has_classic_drs": False,
        "wdc_id": "verstappen",
        "wdc_name": "Max Verstappen",
        "wdc_code": "VER",
        "wdc_num": 1,
        "wdc_team": "Red Bull",
        "wdc_team_id": "redbull",
        "wdc_color": "#3671c6",
        "wdc_points": 428,
        "wdc_wins": 9,
        "wdc_podiums": 17,
        "wdc_poles": 9,
        "wcc_id": "redbull",
        "wcc_name": "Oracle Red Bull Racing",
        "wcc_short": "Red Bull",
        "wcc_color": "#3671c6",
        "wcc_engine": "Red Bull Ford",
        "wcc_points": 710,
        "wcc_wins": 11,
        "narrative": "Max Verstappen delivers a masterclass season to regain the crown with 9 victories, holding off a fierce challenge from McLaren and Ferrari.",
        "win_order": ["verstappen", "verstappen", "norris", "leclerc", "verstappen", "norris", "verstappen", "leclerc", "norris", "verstappen", "hamilton", "verstappen", "norris", "piastri", "leclerc", "russell", "verstappen", "norris", "verstappen", "hamilton", "norris", "russell", "verstappen", "leclerc"],
    },
    2028: {
        "era_name": "2.4L Naturally Aspirated V8 Era",
        "engine_type": "2.4L V8 Naturally Aspirated (20,000 RPM) + Classic DRS",
        "has_active_aero": False,
        "has_classic_drs": True,
        "wdc_id": "leclerc",
        "wdc_name": "Charles Leclerc",
        "wdc_code": "LEC",
        "wdc_num": 16,
        "wdc_team": "Ferrari",
        "wdc_team_id": "ferrari",
        "wdc_color": "#e8002d",
        "wdc_points": 405,
        "wdc_wins": 8,
        "wdc_podiums": 15,
        "wdc_poles": 8,
        "wcc_id": "ferrari",
        "wcc_name": "Scuderia Ferrari HP",
        "wcc_short": "Ferrari",
        "wcc_color": "#e8002d",
        "wcc_engine": "Ferrari",
        "wcc_points": 688,
        "wcc_wins": 12,
        "narrative": "The glorious return of screaming 20,000 RPM V8 engines sees Scuderia Ferrari dominate the technical reset, crowning Charles Leclerc World Champion.",
        "win_order": ["leclerc", "verstappen", "hamilton", "leclerc", "verstappen", "norris", "leclerc", "leclerc", "hamilton", "verstappen", "hamilton", "verstappen", "norris", "leclerc", "leclerc", "russell", "verstappen", "leclerc", "verstappen", "hamilton", "norris", "russell", "verstappen", "leclerc"],
    },
    2029: {
        "era_name": "2.4L Naturally Aspirated V8 Era",
        "engine_type": "2.4L V8 Naturally Aspirated (20,000 RPM) + Classic DRS",
        "has_active_aero": False,
        "has_classic_drs": True,
        "wdc_id": "verstappen",
        "wdc_name": "Max Verstappen",
        "wdc_code": "VER",
        "wdc_num": 1,
        "wdc_team": "Red Bull",
        "wdc_team_id": "redbull",
        "wdc_color": "#3671c6",
        "wdc_points": 418,
        "wdc_wins": 9,
        "wdc_podiums": 16,
        "wdc_poles": 8,
        "wcc_id": "redbull",
        "wcc_name": "Oracle Red Bull Racing",
        "wcc_short": "Red Bull",
        "wcc_color": "#3671c6",
        "wcc_engine": "Red Bull Ford",
        "wcc_points": 695,
        "wcc_wins": 11,
        "narrative": "Max Verstappen conquers a titanic three-way title duel against McLaren's Piastri and Ferrari's Leclerc, winning the decider in Abu Dhabi.",
        "win_order": ["verstappen", "hadjar", "verstappen", "leclerc", "verstappen", "norris", "piastri", "verstappen", "leclerc", "verstappen", "hadjar", "hamilton", "verstappen", "leclerc", "antonelli", "verstappen", "piastri", "verstappen", "norris", "verstappen", "antonelli", "hadjar", "verstappen", "norris"],
    },
    2030: {
        "era_name": "2.4L Naturally Aspirated V8 Era",
        "engine_type": "2.4L V8 Naturally Aspirated (20,000 RPM) + Classic DRS",
        "has_active_aero": False,
        "has_classic_drs": True,
        "wdc_id": "antonelli",
        "wdc_name": "Kimi Antonelli",
        "wdc_code": "ANT",
        "wdc_num": 12,
        "wdc_team": "Mercedes",
        "wdc_team_id": "mercedes",
        "wdc_color": "#00d2be",
        "wdc_points": 395,
        "wdc_wins": 7,
        "wdc_podiums": 14,
        "wdc_poles": 6,
        "wcc_id": "mercedes",
        "wcc_name": "Mercedes-AMG PETRONAS F1 Team",
        "wcc_short": "Mercedes",
        "wcc_color": "#00d2be",
        "wcc_engine": "Mercedes",
        "wcc_points": 755,
        "wcc_wins": 12,
        "narrative": "A sensational new era dawns as prodigy Kimi Antonelli captures his maiden Formula 1 World Drivers' Championship alongside teammate George Russell.",
        "win_order": ["antonelli", "russell", "verstappen", "leclerc", "antonelli", "norris", "russell", "leclerc", "antonelli", "verstappen", "russell", "verstappen", "antonelli", "norris", "leclerc", "antonelli", "piastri", "russell", "verstappen", "antonelli", "norris", "russell", "antonelli", "leclerc"],
    },
}

# Pre-defined candidate pools for podium and top 10 generation
DEFAULT_PODIUM_CANDIDATES = [
    "norris", "verstappen", "leclerc", "piastri", "hamilton", "russell",
    "antonelli", "alonso", "sainz", "albon", "gasly"
]

MIDFIELD_CANDIDATES = [
    "albon", "sainz", "alonso", "gasly", "lawson", "colapinto",
    "stroll", "lindblad", "hulkenberg", "bearman", "ocon", "bortoleto",
    "bottas", "perez", "hadjar"
]


def _build_synthetic_race(
    round_num: int,
    track: Any,
    winner_id: str,
    preset: dict[str, Any],
) -> dict[str, Any]:
    """Builds a realistic 24-car/10-point synthetic race classification."""
    win_drv = DRIVERS_MAP.get(winner_id, DRIVERS_MAP["norris"])
    win_tm = TEAMS_MAP.get(win_drv["team_id"], TEAMS_MAP["mclaren"])

    # Pick P2 and P3 with natural champion podium weighting
    champ_id = preset["wdc_id"]
    p_pool = [d for d in DEFAULT_PODIUM_CANDIDATES if d != winner_id]

    if champ_id != winner_id and round_num % 2 == 0:
        p2_id = champ_id
        rem = [d for d in p_pool if d != champ_id]
        p3_id = rem[(round_num * 5 + 1) % len(rem)]
    elif champ_id != winner_id and round_num % 3 == 0:
        rem = [d for d in p_pool if d != champ_id]
        p2_id = rem[(round_num * 3) % len(rem)]
        p3_id = champ_id
    else:
        p2_id = p_pool[(round_num * 3) % len(p_pool)]
        p3_id = p_pool[(round_num * 7 + 1) % len(p_pool)]
        if p2_id == p3_id:
            p3_id = p_pool[(round_num * 7 + 2) % len(p_pool)]

    p2_drv = DRIVERS_MAP[p2_id]
    p2_tm = TEAMS_MAP[p2_drv["team_id"]]
    p3_drv = DRIVERS_MAP[p3_id]
    p3_tm = TEAMS_MAP[p3_drv["team_id"]]

    # Pole and Fastest Lap
    pole_id = winner_id if round_num % 2 == 1 else p2_id
    pole_drv = DRIVERS_MAP[pole_id]

    fl_pool = [winner_id, p2_id, p3_id, "norris", "verstappen", "hamilton", "russell"]
    fl_id = fl_pool[(round_num * 5) % len(fl_pool)]
    fl_drv = DRIVERS_MAP[fl_id]

    # Sprint winner if sprint round
    sprint_winner_code = None
    sprint_winner_name = None
    if getattr(track, "is_sprint", False):
        spr_id = winner_id if round_num % 3 != 0 else p2_id
        spr_drv = DRIVERS_MAP[spr_id]
        sprint_winner_code = spr_drv["code"]
        sprint_winner_name = spr_drv["name"]

    # Top 10 Classification
    top10_ids = [winner_id, p2_id, p3_id]
    remaining_pool = [d for d in DEFAULT_PODIUM_CANDIDATES + MIDFIELD_CANDIDATES if d not in top10_ids]
    for idx in range(7):
        pick = remaining_pool[(round_num * 2 + idx * 3) % len(remaining_pool)]
        if pick not in top10_ids:
            top10_ids.append(pick)

    # Pad if needed
    for d in DEFAULT_PODIUM_CANDIDATES + MIDFIELD_CANDIDATES:
        if len(top10_ids) >= 10:
            break
        if d not in top10_ids:
            top10_ids.append(d)

    top10 = []
    gaps = [
        "WINNER",
        f"+{round(1.2 + (round_num * 0.37) % 4.5, 3)}s",
        f"+{round(4.8 + (round_num * 0.52) % 6.2, 3)}s",
        f"+{round(11.4 + (round_num * 0.81) % 8.1, 3)}s",
        f"+{round(16.9 + (round_num * 0.95) % 9.4, 3)}s",
        f"+{round(23.2 + (round_num * 1.15) % 11.2, 3)}s",
        f"+{round(31.5 + (round_num * 1.34) % 12.8, 3)}s",
        f"+{round(42.1 + (round_num * 1.48) % 14.2, 3)}s",
        f"+{round(51.8 + (round_num * 1.62) % 15.5, 3)}s",
        f"+{round(62.4 + (round_num * 1.77) % 16.8, 3)}s",
    ]

    for rank, did in enumerate(top10_ids[:10], 1):
        d_obj = DRIVERS_MAP[did]
        t_obj = TEAMS_MAP[d_obj["team_id"]]
        pts = RACE_POINTS[rank - 1]
        if did == fl_id:
            pts += 1  # 1 bonus point for fastest lap in top 10
        top10.append({
            "pos": rank,
            "id": did,
            "code": d_obj["code"],
            "name": d_obj["name"],
            "number": d_obj.get("career_number", d_obj.get("number", 0)),
            "team": t_obj["short"],
            "team_id": t_obj["id"],
            "team_color": t_obj["color"],
            "points": pts,
            "gap": gaps[rank - 1],
            "fastest_lap": did == fl_id,
        })

    return {
        "round": track.round,
        "track_id": track.id,
        "gp": track.name,
        "circuit": track.circuit,
        "city": track.city,
        "country": track.country,
        "is_sprint": getattr(track, "is_sprint", False),
        "laps": track.race_laps,
        "status": "COMPLETED",
        "winner_id": win_drv["id"],
        "winner_name": win_drv["name"],
        "winner_code": win_drv["code"],
        "winner_number": win_drv.get("career_number", win_drv.get("number", 0)),
        "winner_team": win_tm["short"],
        "winner_team_id": win_tm["id"],
        "winner_color": win_tm["color"],
        "p2_name": p2_drv["name"],
        "p2_code": p2_drv["code"],
        "p2_team": p2_tm["short"],
        "p2_color": p2_tm["color"],
        "p3_name": p3_drv["name"],
        "p3_code": p3_drv["code"],
        "p3_team": p3_tm["short"],
        "p3_color": p3_tm["color"],
        "pole_code": pole_drv["code"],
        "pole_name": pole_drv["name"],
        "fastest_lap_code": fl_drv["code"],
        "fastest_lap_name": fl_drv["name"],
        "sprint_winner_code": sprint_winner_code,
        "sprint_winner_name": sprint_winner_name,
        "top10": top10,
    }


def generate_default_season_archives() -> dict[str, dict[str, Any]]:
    """Generates the full authentic season archives for 2026 through 2030."""
    archives: dict[str, dict[str, Any]] = {}

    for year in range(2026, 2031):
        preset = SEASON_PRESETS[year]
        tracks = get_season_tracks(year)
        win_order = preset["win_order"]

        races: list[dict[str, Any]] = []
        d_points: dict[str, int] = {d["id"]: 0 for d in INITIAL_DRIVERS}
        d_wins: dict[str, int] = {d["id"]: 0 for d in INITIAL_DRIVERS}
        d_podiums: dict[str, int] = {d["id"]: 0 for d in INITIAL_DRIVERS}
        d_poles: dict[str, int] = {d["id"]: 0 for d in INITIAL_DRIVERS}

        t_points: dict[str, int] = {t["id"]: 0 for t in INITIAL_TEAMS}
        t_wins: dict[str, int] = {t["id"]: 0 for t in INITIAL_TEAMS}

        for idx, trk in enumerate(tracks):
            win_did = win_order[idx % len(win_order)]
            race_rec = _build_synthetic_race(trk.round, trk, win_did, preset)
            races.append(race_rec)

            # Tally
            d_wins[race_rec["winner_id"]] += 1
            t_wins[race_rec["winner_team_id"]] += 1

            for row in race_rec["top10"]:
                did = row["id"]
                pts = row["points"]
                d_points[did] += pts
                tid = row["team_id"]
                t_points[tid] += pts
                if row["pos"] <= 3:
                    d_podiums[did] += 1

            # Pole
            for did, d_obj in DRIVERS_MAP.items():
                if d_obj["code"] == race_rec["pole_code"]:
                    d_poles[did] += 1
                    break

        # Build final WDC table
        wdc_rows = []
        for did, pts in d_points.items():
            if pts > 0:
                d_obj = DRIVERS_MAP[did]
                t_obj = TEAMS_MAP[d_obj["team_id"]]
                wdc_rows.append({
                    "id": did,
                    "name": d_obj["name"],
                    "code": d_obj["code"],
                    "number": d_obj.get("career_number", d_obj.get("number", 0)),
                    "team": t_obj["short"],
                    "team_id": t_obj["id"],
                    "team_color": t_obj["color"],
                    "points": pts,
                    "wins": d_wins[did],
                    "podiums": d_podiums[did],
                    "poles": d_poles[did],
                })
        wdc_rows.sort(key=lambda r: (-r["points"], -r["wins"], -r["podiums"]))
        for rank, r in enumerate(wdc_rows, 1):
            r["rank"] = rank

        # Build final WCC table
        wcc_rows = []
        for tid, pts in t_points.items():
            t_obj = TEAMS_MAP[tid]
            wcc_rows.append({
                "id": tid,
                "name": t_obj["name"],
                "short": t_obj["short"],
                "color": t_obj["color"],
                "engine": t_obj["engine"],
                "points": pts,
                "wins": t_wins[tid],
            })
        wcc_rows.sort(key=lambda r: (-r["points"], -r["wins"]))
        for rank, r in enumerate(wcc_rows, 1):
            r["rank"] = rank

        top_wdc = wdc_rows[0] if wdc_rows else {
            "name": preset["wdc_name"], "code": preset["wdc_code"], "number": preset["wdc_num"],
            "team": preset["wdc_team"], "team_id": preset["wdc_team_id"], "team_color": preset["wdc_color"],
            "points": preset["wdc_points"], "wins": preset["wdc_wins"], "podiums": preset["wdc_podiums"], "poles": preset["wdc_poles"]
        }
        top_wcc = wcc_rows[0] if wcc_rows else {
            "name": preset["wcc_name"], "short": preset["wcc_short"], "color": preset["wcc_color"],
            "engine": preset["wcc_engine"], "points": preset["wcc_points"], "wins": preset["wcc_wins"]
        }

        archives[str(year)] = {
            "season": year,
            "era_name": preset["era_name"],
            "engine_type": preset["engine_type"],
            "has_active_aero": preset["has_active_aero"],
            "has_classic_drs": preset["has_classic_drs"],
            "status": "COMPLETED",
            "narrative": preset["narrative"],
            "total_rounds": len(tracks),
            "completed_rounds": len(tracks),
            "wdc_champion": top_wdc,
            "wcc_champion": top_wcc,
            "races": races,
            "wdc_standings": wdc_rows[:22],
            "wcc_standings": wcc_rows[:11],
        }

    return archives


def record_live_race_to_archive(
    archives: dict[str, dict[str, Any]],
    season_year: int,
    round_rec: dict[str, Any],
    classification: list[dict[str, Any]],
    current_track: Any,
) -> None:
    """Updates the archive for the given season with the real in-game race result."""
    s_key = str(season_year)
    if s_key not in archives:
        archives[s_key] = generate_default_season_archives().get(s_key, {})

    season_data = archives[s_key]
    races = season_data.get("races", [])

    # Find the matching race by round
    target_round = round_rec.get("round", 1)
    race_entry = next((r for r in races if r["round"] == target_round), None)

    # Format Top 10 from classification
    formatted_top10 = []
    for rank, car in enumerate(classification[:10], 1):
        formatted_top10.append({
            "pos": rank,
            "id": car.get("driver_id", car.get("id", "")),
            "code": car.get("code", "F1"),
            "name": car.get("name", "Driver"),
            "number": car.get("number", 0),
            "team": car.get("team_short", car.get("team", "")),
            "team_id": car.get("team_id", ""),
            "team_color": car.get("team_color", "#888888"),
            "points": car.get("points", RACE_POINTS[rank - 1] if rank <= 10 else 0),
            "gap": "WINNER" if rank == 1 else car.get("gap", f"+{rank * 2.1:.3f}s"),
            "fastest_lap": car.get("fastest_lap", False),
        })

    live_record = {
        "round": target_round,
        "track_id": getattr(current_track, "id", f"r{target_round}"),
        "gp": getattr(current_track, "name", round_rec.get("gp", f"Grand Prix {target_round}")),
        "circuit": getattr(current_track, "circuit", round_rec.get("circuit", "Circuit")),
        "city": getattr(current_track, "city", round_rec.get("city", "City")),
        "country": getattr(current_track, "country", round_rec.get("country", "FIA")),
        "is_sprint": getattr(current_track, "is_sprint", round_rec.get("is_sprint", False)),
        "laps": getattr(current_track, "race_laps", round_rec.get("laps", 22)),
        "status": "COMPLETED",
        "winner_id": round_rec.get("winner_id", classification[0].get("driver_id", "")),
        "winner_name": round_rec.get("winner_name", classification[0].get("name", "")),
        "winner_code": round_rec.get("winner_code", classification[0].get("code", "")),
        "winner_number": classification[0].get("number", 0),
        "winner_team": round_rec.get("winner_team", classification[0].get("team_short", "")),
        "winner_team_id": classification[0].get("team_id", ""),
        "winner_color": round_rec.get("winner_color", classification[0].get("team_color", "#ffffff")),
        "p2_name": classification[1].get("name", round_rec.get("p2_code", "")) if len(classification) > 1 else "",
        "p2_code": round_rec.get("p2_code", ""),
        "p2_team": classification[1].get("team_short", "") if len(classification) > 1 else "",
        "p2_color": classification[1].get("team_color", "#ffffff") if len(classification) > 1 else "",
        "p3_name": classification[2].get("name", round_rec.get("p3_code", "")) if len(classification) > 2 else "",
        "p3_code": round_rec.get("p3_code", ""),
        "p3_team": classification[2].get("team_short", "") if len(classification) > 2 else "",
        "p3_color": classification[2].get("team_color", "#ffffff") if len(classification) > 2 else "",
        "pole_code": round_rec.get("pole_code", ""),
        "pole_name": round_rec.get("pole_name", round_rec.get("pole_code", "")),
        "fastest_lap_code": round_rec.get("fastest_lap_code", ""),
        "fastest_lap_name": round_rec.get("fastest_lap_code", ""),
        "sprint_winner_code": round_rec.get("sprint_winner_code"),
        "sprint_winner_name": round_rec.get("sprint_winner_code"),
        "top10": formatted_top10,
    }

    if race_entry is not None:
        idx = races.index(race_entry)
        races[idx] = live_record
    else:
        races.append(live_record)

    season_data["races"] = races
    season_data["completed_rounds"] = sum(1 for r in races if r.get("status") == "COMPLETED")


def sync_live_season_status(
    archives: dict[str, dict[str, Any]],
    season_year: int,
    current_round: int,
    total_rounds: int,
    phase: str,
    wdc_table: list[dict[str, Any]],
    wcc_table: list[dict[str, Any]],
) -> None:
    """Updates the archive metadata for the active career season."""
    s_key = str(season_year)
    if s_key not in archives:
        archives[s_key] = generate_default_season_archives().get(s_key, {})

    season_data = archives[s_key]

    if phase == "OFF_SEASON" or current_round > total_rounds:
        season_data["status"] = "COMPLETED"
    else:
        season_data["status"] = "IN_PROGRESS"

    season_data["current_round"] = current_round
    season_data["total_rounds"] = total_rounds

    if wdc_table:
        top_drv = wdc_table[0]
        season_data["wdc_champion"] = {
            "id": top_drv.get("id"),
            "name": top_drv.get("name"),
            "code": top_drv.get("code"),
            "number": top_drv.get("number"),
            "team": top_drv.get("team_short"),
            "team_id": top_drv.get("team_id"),
            "team_color": top_drv.get("team_color"),
            "points": top_drv.get("points"),
            "wins": top_drv.get("wins"),
            "podiums": top_drv.get("podiums"),
            "poles": top_drv.get("poles"),
        }
        season_data["wdc_standings"] = [
            {
                "rank": r.get("rank"),
                "id": r.get("id"),
                "name": r.get("name"),
                "code": r.get("code"),
                "number": r.get("number"),
                "team": r.get("team_short"),
                "team_id": r.get("team_id"),
                "team_color": r.get("team_color"),
                "points": r.get("points"),
                "wins": r.get("wins"),
                "podiums": r.get("podiums"),
                "poles": r.get("poles"),
            }
            for r in wdc_table[:22]
        ]

    if wcc_table:
        top_tm = wcc_table[0]
        season_data["wcc_champion"] = {
            "id": top_tm.get("id"),
            "name": top_tm.get("name"),
            "short": top_tm.get("short", top_tm.get("name")),
            "color": top_tm.get("color"),
            "engine": top_tm.get("engine"),
            "points": top_tm.get("points"),
            "wins": top_tm.get("wins"),
        }
        season_data["wcc_standings"] = [
            {
                "rank": r.get("rank"),
                "id": r.get("id"),
                "name": r.get("name"),
                "short": r.get("short", r.get("name")),
                "color": r.get("color"),
                "engine": r.get("engine"),
                "points": r.get("points"),
                "wins": r.get("wins"),
            }
            for r in wcc_table[:11]
        ]
