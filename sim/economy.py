"""Season funding and payroll, in millions of USD (not FIA cost-cap accounting)."""

from sim.data import INITIAL_TEAMS, SPONSORS

BALANCE_VERSION = 1
# Rounded from $401.6M: mean of revenue minus operating profit for ten teams
# in Forbes' 2025 valuations (2024 F1 operations, excluding engine businesses).
# Team allocations are gameplay estimates around that benchmark, not disclosures.
ANNUAL_OPERATIONS_SHARE = 0.60
SALARY_SOURCE = "https://racingnews365.com/f1-drivers-salaries-2026"
BUDGET_SOURCE = "https://www.forbes.com.au/news/sport/ranked-most-valuable-formula-1-teams-2025/"

# Previous launch specification, retained solely for one-time save migration.
LEGACY_TEAMS = {
    "mercedes": (138, [8, 7, 7, 7, 8, 7]),
    "ferrari": (138, [8, 7, 7, 7, 7, 7]),
    "redbull": (135, [7, 8, 7, 7, 6, 7]),
    "mclaren": (134, [7, 7, 8, 7, 6, 7]),
    "racingbulls": (104, [6, 6, 5, 5, 5, 5]),
    "alpine": (105, [6, 5, 5, 6, 5, 5]),
    "audi": (112, [5, 6, 5, 5, 6, 5]),
    "haas": (94, [5, 4, 4, 4, 5, 4]),
    "williams": (102, [5, 4, 4, 4, 4, 4]),
    "aston": (114, [4, 5, 4, 4, 3, 4]),
    "cadillac": (108, [5, 3, 4, 4, 5, 4]),
}
LEGACY_SALARIES = dict(zip(
    ("russell", "antonelli", "leclerc", "hamilton", "verstappen", "hadjar",
     "norris", "piastri", "lawson", "lindblad", "gasly", "colapinto",
     "hulkenberg", "bortoleto", "ocon", "bearman", "sainz", "albon",
     "alonso", "stroll", "perez", "bottas"),
    (22, 7.5, 27, 32, 36, 5.5, 24, 19, 5, 2.8, 10, 4.5,
     9.5, 4, 8, 4.2, 14, 9, 18, 6, 11, 8.5),
))


def annual_budget_m(team):
    if "annual_budget_m" in team:
        return float(team["annual_budget_m"])
    return float(next((t["budget_m"] for t in INITIAL_TEAMS if t["id"] == team["id"]), team.get("budget_m", 150.0)))


def team_finances(team, drivers, race_count, rounds_remaining=None):
    races = max(1, race_count)
    annual = annual_budget_m(team)
    payroll = sum(d["salary_m"] for d in drivers if d.get("team_id") == team["id"])
    operations = annual * ANNUAL_OPERATIONS_SHARE
    sponsor = next((s for s in SPONSORS if s["id"] == team.get("sponsor_id")), SPONSORS[0])
    remaining = races if rounds_remaining is None else max(0, min(races, rounds_remaining))
    # Annual operations and payroll are settled as a fixed cost at season start,
    # so only a crash-repair and contingency buffer is needed mid-season.
    reserve = 22.0
    return {
        "annual_budget_m": round(annual, 2),
        "annual_operations_m": round(operations, 2),
        "annual_payroll_m": round(payroll, 2),
        "operations_per_race_m": operations / races,
        "payroll_per_race_m": payroll / races,
        "operating_reserve_m": round(reserve, 2),
        "race_count": races,
    }


def season_allocation_m(team, race_count, championship_prize_m=0.0):
    """Owner/core funding completes the annual envelope after sponsors and prize."""
    sponsor = next((s for s in SPONSORS if s["id"] == team.get("sponsor_id")), SPONSORS[0])
    return round(max(0.0, annual_budget_m(team) - sponsor["base_per_race_m"] * race_count - championship_prize_m), 2)


def migrate_legacy_balance(teams, drivers, season, opening_round):
    """Rebase cash once, preserve spending and earned development deltas."""
    from sim.data import INITIAL_DRIVERS
    initial = {t["id"]: t for t in INITIAL_TEAMS}
    for team in teams:
        base = initial.get(team["id"])
        if base is None:
            continue
        old_cash, old_levels = LEGACY_TEAMS[team["id"]]
        team["budget_m"] = round(team["budget_m"] + base["budget_m"] - old_cash, 2)
        team["annual_budget_m"] = base["budget_m"]
        if season == 2026:
            for (dept, new_base), old_base in zip(base["upgrades"].items(), old_levels):
                team["upgrades"][dept] = max(1, min(10, new_base + team["upgrades"][dept] - old_base))
        elif season == 2028 and opening_round:
            # The former V8 launch randomized levels 2..8. Compress that launch
            # while keeping additional levels already developed above level 8.
            compressed = {1: 4, 2: 5, 3: 5, 4: 6, 5: 6, 6: 6, 7: 7, 8: 7, 9: 8, 10: 9}
            team["upgrades"] = {dept: compressed[level] for dept, level in team["upgrades"].items()}
    salaries = {d["id"]: d["salary_m"] for d in INITIAL_DRIVERS}
    for driver in drivers:
        did = driver["id"]
        if did in LEGACY_SALARIES and driver["salary_m"] == LEGACY_SALARIES[did]:
            driver["salary_m"] = salaries[did]
