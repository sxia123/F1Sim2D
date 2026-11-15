"""Authentic 2026 FIA Formula 1 Teams, Drivers, Free Agents, Upgrades, Sponsors & Tire Specs."""

from __future__ import annotations
import copy

RACE_POINTS = [25, 18, 15, 12, 10, 8, 6, 4, 2, 1]
SPRINT_POINTS = [8, 7, 6, 5, 4, 3, 2, 1]
MAX_UPGRADES_PER_RACE = 3
UPGRADE_PRICE_MULTIPLIER = 1.10

# 2026 FIA Constructor Prize Pool at end of season ($ Millions)
WCC_PRIZE_POOL_M = [162.0, 148.0, 136.0, 125.0, 115.0, 106.0, 97.0, 89.0, 82.0, 75.0, 69.0]

TIRE_COMPOUNDS = {
    "SOFT": {
        "code": "S",
        "name": "Soft",
        "color": "#ff2800",
        "base_grip": 1.042,
        "wear_per_km": 0.0112,
        "cliff_wear": 0.68,
        "optimal_wet_min": 0.0,
        "optimal_wet_max": 0.12,
        "warmup_rate": 0.18,
        "opt_temp_min": 90.0,
        "opt_temp_max": 106.0,
        "ideal_temp": 98.0,
        "overheat_sens": 0.035,
    },
    "MEDIUM": {
        "code": "M",
        "name": "Medium",
        "color": "#ffd200",
        "base_grip": 1.008,
        "wear_per_km": 0.0074,
        "cliff_wear": 0.74,
        "optimal_wet_min": 0.0,
        "optimal_wet_max": 0.14,
        "warmup_rate": 0.12,
        "opt_temp_min": 95.0,
        "opt_temp_max": 113.0,
        "ideal_temp": 104.0,
        "overheat_sens": 0.028,
    },
    "HARD": {
        "code": "H",
        "name": "Hard",
        "color": "#f0f2f5",
        "base_grip": 0.980,
        "wear_per_km": 0.0049,
        "cliff_wear": 0.80,
        "optimal_wet_min": 0.0,
        "optimal_wet_max": 0.15,
        "warmup_rate": 0.08,
        "opt_temp_min": 100.0,
        "opt_temp_max": 120.0,
        "ideal_temp": 110.0,
        "overheat_sens": 0.022,
    },
    "INTER": {
        "code": "I",
        "name": "Intermediate",
        "color": "#38b000",
        "base_grip": 0.945,
        "wear_per_km": 0.0088,
        "cliff_wear": 0.75,
        "optimal_wet_min": 0.13,
        "optimal_wet_max": 0.62,
        "warmup_rate": 0.15,
        "opt_temp_min": 70.0,
        "opt_temp_max": 92.0,
        "ideal_temp": 81.0,
        "overheat_sens": 0.045,
    },
    "WET": {
        "code": "W",
        "name": "Full Wet",
        "color": "#0096ff",
        "base_grip": 0.895,
        "wear_per_km": 0.0070,
        "cliff_wear": 0.80,
        "optimal_wet_min": 0.50,
        "optimal_wet_max": 1.00,
        "warmup_rate": 0.16,
        "opt_temp_min": 60.0,
        "opt_temp_max": 85.0,
        "ideal_temp": 72.0,
        "overheat_sens": 0.050,
    },
}

# Official FIA Formula 1 Pirelli Weekend Tire Allocation per Driver (Total: 20 sets)
DEFAULT_WEEKEND_TIRE_SETS = {
    "SOFT": 8,
    "MEDIUM": 3,
    "HARD": 2,
    "INTER": 4,
    "WET": 3,
}

# 2026 FIA Power Unit & Gearbox Seasonal Allocation Limits
PU_COMPONENT_SPECS = {
    "ice": {
        "name": "Internal Combustion Engine (ICE)",
        "short": "ICE",
        "limit": 4,
        "wear_per_gp": 0.088,
        "first_penalty": 10,
        "extra_penalty": 5,
    },
    "turbo": {
        "name": "Turbocharger (TC)",
        "short": "TC",
        "limit": 4,
        "wear_per_gp": 0.082,
        "first_penalty": 10,
        "extra_penalty": 5,
    },
    "mgu_k": {
        "name": "MGU-K Hybrid (350 kW)",
        "short": "MGU-K",
        "limit": 3,
        "wear_per_gp": 0.072,
        "first_penalty": 10,
        "extra_penalty": 5,
    },
    "gearbox": {
        "name": "Gearbox Cassette (GBX)",
        "short": "GBX",
        "limit": 4,
        "wear_per_gp": 0.085,
        "first_penalty": 5,
        "extra_penalty": 5,
    },
}

# Pre-Weekend Aero Setup Presets (-2 = Monza Low Drag ... +2 = Monaco Max Downforce)
SETUP_LEVELS = {
    -2: {"label": "MIN DRAG", "short": "-2 LD", "corner_grip": -0.017, "straight_spd": 0.014, "wear_mult": 1.07, "fuel_mult": 0.97},
    -1: {"label": "LOW DF", "short": "-1 DF", "corner_grip": -0.0085, "straight_spd": 0.007, "wear_mult": 1.035, "fuel_mult": 0.985},
    0: {"label": "BALANCED", "short": "0 BAL", "corner_grip": 0.0, "straight_spd": 0.0, "wear_mult": 1.0, "fuel_mult": 1.0},
    1: {"label": "HIGH DF", "short": "+1 DF", "corner_grip": 0.0085, "straight_spd": -0.007, "wear_mult": 0.965, "fuel_mult": 1.015},
    2: {"label": "MAX DF", "short": "+2 HD", "corner_grip": 0.017, "straight_spd": -0.014, "wear_mult": 0.93, "fuel_mult": 1.03},
}

# Circuit DNA Upgrade Weighting Profiles
# Weights scale each department's performance impact relative to baseline (1.00 = nominal).
CIRCUIT_UPGRADE_PROFILES = {
    "italy": {
        "category": "POWER",
        "label": "Temple of Speed (Low Drag / Top Power)",
        "recommended_df": -2,
        "weights": {"power_unit": 1.50, "active_aero": 1.20, "chassis": 0.72, "suspension": 0.65, "reliability": 1.15, "pit_crew": 1.0},
    },
    "vegas": {
        "category": "POWER",
        "label": "High-Speed Night Street (Power & Braking)",
        "recommended_df": -2,
        "weights": {"power_unit": 1.42, "active_aero": 1.18, "chassis": 0.78, "suspension": 0.72, "reliability": 1.05, "pit_crew": 1.0},
    },
    "belgium": {
        "category": "POWER",
        "label": "High-Speed Power & Compression",
        "recommended_df": -1,
        "weights": {"power_unit": 1.32, "active_aero": 1.24, "chassis": 0.86, "suspension": 0.78, "reliability": 1.05, "pit_crew": 1.0},
    },
    "azerbaijan": {
        "category": "POWER",
        "label": "Long Straight & 90-Deg Braking Street",
        "recommended_df": -1,
        "weights": {"power_unit": 1.34, "active_aero": 1.12, "chassis": 0.84, "suspension": 0.86, "reliability": 1.05, "pit_crew": 1.05},
    },
    "saudi": {
        "category": "POWER",
        "label": "Flat-Out High-Speed Walls",
        "recommended_df": -1,
        "weights": {"power_unit": 1.28, "active_aero": 1.22, "chassis": 0.88, "suspension": 0.82, "reliability": 1.0, "pit_crew": 1.0},
    },
    "austria": {
        "category": "POWER",
        "label": "Short High-Altitude Power Sprint",
        "recommended_df": -1,
        "weights": {"power_unit": 1.30, "active_aero": 1.12, "chassis": 0.86, "suspension": 0.86, "reliability": 1.10, "pit_crew": 1.0},
    },
    "mexico": {
        "category": "POWER",
        "label": "High Altitude Thin-Air Power & Cooling",
        "recommended_df": 0,
        "weights": {"power_unit": 1.26, "active_aero": 1.08, "chassis": 0.90, "suspension": 0.86, "reliability": 1.25, "pit_crew": 1.0},
    },
    "canada": {
        "category": "POWER",
        "label": "Stop-Go Chicanes & Kerbs",
        "recommended_df": -1,
        "weights": {"power_unit": 1.22, "active_aero": 1.02, "chassis": 0.92, "suspension": 1.04, "reliability": 1.05, "pit_crew": 1.0},
    },
    "bahrain": {
        "category": "POWER",
        "label": "Traction, Rear Wear & Power",
        "recommended_df": 0,
        "weights": {"power_unit": 1.20, "active_aero": 1.04, "chassis": 0.94, "suspension": 0.96, "reliability": 1.05, "pit_crew": 1.05},
    },
    "monaco": {
        "category": "STREET",
        "label": "Tight Street Labyrinth (Mechanical & Max DF)",
        "recommended_df": 2,
        "weights": {"power_unit": 0.56, "active_aero": 1.15, "chassis": 1.42, "suspension": 1.48, "reliability": 0.90, "pit_crew": 1.15},
    },
    "singapore": {
        "category": "STREET",
        "label": "Bumpy Technical Street & Cooling",
        "recommended_df": 2,
        "weights": {"power_unit": 0.72, "active_aero": 1.18, "chassis": 1.32, "suspension": 1.38, "reliability": 1.18, "pit_crew": 1.10},
    },
    "hungary": {
        "category": "DOWNFORCE",
        "label": "Twisty High-Downforce Technical",
        "recommended_df": 2,
        "weights": {"power_unit": 0.74, "active_aero": 1.28, "chassis": 1.30, "suspension": 1.28, "reliability": 0.95, "pit_crew": 1.05},
    },
    "netherlands": {
        "category": "DOWNFORCE",
        "label": "Banked Corners & High Downforce",
        "recommended_df": 2,
        "weights": {"power_unit": 0.78, "active_aero": 1.26, "chassis": 1.26, "suspension": 1.26, "reliability": 0.95, "pit_crew": 1.10},
    },
    "madrid": {
        "category": "DOWNFORCE",
        "label": "Technical Multi-Apex Hybrid Street",
        "recommended_df": 1,
        "weights": {"power_unit": 0.84, "active_aero": 1.20, "chassis": 1.20, "suspension": 1.22, "reliability": 1.0, "pit_crew": 1.0},
    },
    "japan": {
        "category": "DOWNFORCE",
        "label": "High-Speed Sweeping Aero Test",
        "recommended_df": 1,
        "weights": {"power_unit": 0.92, "active_aero": 1.36, "chassis": 1.22, "suspension": 1.10, "reliability": 1.0, "pit_crew": 1.0},
    },
    "qatar": {
        "category": "DOWNFORCE",
        "label": "Sustained High-G Aero & Tyre Load",
        "recommended_df": 1,
        "weights": {"power_unit": 0.95, "active_aero": 1.34, "chassis": 1.20, "suspension": 1.12, "reliability": 1.0, "pit_crew": 1.05},
    },
    "brazil": {
        "category": "BALANCED",
        "label": "Elevation Changes & Infield Flow",
        "recommended_df": 1,
        "weights": {"power_unit": 1.04, "active_aero": 1.10, "chassis": 1.06, "suspension": 1.08, "reliability": 1.0, "pit_crew": 1.05},
    },
}

DEFAULT_CIRCUIT_PROFILE = {
    "category": "BALANCED",
    "label": "All-Round Grand Prix Circuit",
    "recommended_df": 0,
    "weights": {"power_unit": 1.00, "active_aero": 1.04, "chassis": 1.00, "suspension": 0.98, "reliability": 1.00, "pit_crew": 1.00},
}

UPGRADE_DEPARTMENTS = {
    "power_unit": {
        "name": "2026 Hybrid PU & MGU-K",
        "short": "Power Unit",
        "code": "PU-ERS",
        "desc": "Increases 350kW MGU-K deployment efficiency, delays >290 km/h derating, and raises Overtake Mode peak speed.",
        "base_cost_m": 8.5,
        "cost_scale": 1.32,
        "max_level": 10,
    },
    "active_aero": {
        "name": "Active Aerodynamics (X/Z Mode)",
        "short": "Active Aero",
        "code": "AERO",
        "desc": "Reduces Straight-Mode drag along straights while maximizing Corner-Mode floor and wing downforce.",
        "base_cost_m": 8.0,
        "cost_scale": 1.30,
        "max_level": 10,
    },
    "chassis": {
        "name": "Monocoque & Weight Reduction",
        "short": "Chassis",
        "code": "CHAS",
        "desc": "Brings dry mass down toward the 768 kg FIA minimum, improving transient response and tyre life.",
        "base_cost_m": 7.2,
        "cost_scale": 1.28,
        "max_level": 10,
    },
    "suspension": {
        "name": "Suspension & Mechanical Grip",
        "short": "Suspension",
        "code": "SUSP",
        "desc": "Improves slow-speed traction, kerb compliance, braking stability, and wet-weather balance.",
        "base_cost_m": 6.5,
        "cost_scale": 1.27,
        "max_level": 10,
    },
    "reliability": {
        "name": "Cooling & PU Reliability",
        "short": "Reliability",
        "code": "RELI",
        "desc": "Mitigates MGU-K inverter, energy store, turbocharger, and gearbox retirements under sustained thermal load.",
        "base_cost_m": 5.8,
        "cost_scale": 1.25,
        "max_level": 10,
    },
    "pit_crew": {
        "name": "Pit Crew & Wheel-Gun Gantry",
        "short": "Pit Crew",
        "code": "PIT",
        "desc": "Lowers stationary pit times toward 1.9s and reduces cross-threaded wheel nut and unsafe release incidents.",
        "base_cost_m": 4.8,
        "cost_scale": 1.24,
        "max_level": 10,
    },
}

SPONSORS = [
    {
        "id": "apex_cloud",
        "name": "Apex Quantum Cloud",
        "tier": "Title Partner",
        "base_per_race_m": 2.1,
        "bonus_target_pos": 3,
        "bonus_payout_m": 2.4,
        "desc": "$2.1M base per Grand Prix + $2.4M performance bonus for a Podium finish (P1-P3).",
    },
    {
        "id": "veloce_energy",
        "name": "Veloce Sustainable Fuels",
        "tier": "Technical Partner",
        "base_per_race_m": 2.5,
        "bonus_target_pos": 5,
        "bonus_payout_m": 1.5,
        "desc": "$2.5M base per Grand Prix + $1.5M performance bonus for any Top 5 classification.",
    },
    {
        "id": "chronos_swiss",
        "name": "Chronos Geneve Horology",
        "tier": "Official Timing Partner",
        "base_per_race_m": 1.8,
        "bonus_target_pos": 1,
        "bonus_payout_m": 4.2,
        "desc": "$1.8M base per Grand Prix + $4.2M victory bonus for winning a Grand Prix (P1).",
    },
    {
        "id": "hyperion_ai",
        "name": "Hyperion Silicon Systems",
        "tier": "Principal Partner",
        "base_per_race_m": 2.7,
        "bonus_target_pos": 8,
        "bonus_payout_m": 0.9,
        "desc": "$2.7M base per Grand Prix + $0.9M bonus for finishing inside the Top 8.",
    },
    {
        "id": "titan_logistics",
        "name": "Titan Global Freight",
        "tier": "Official Logistics Partner",
        "base_per_race_m": 3.0,
        "bonus_target_pos": 10,
        "bonus_payout_m": 0.5,
        "desc": "$3.0M guaranteed per Grand Prix + $0.5M bonus for scoring Championship points (Top 10).",
    },
    {
        "id": "nova_fintech",
        "name": "Nova Institutional Markets",
        "tier": "Commercial Partner",
        "base_per_race_m": 2.2,
        "bonus_target_pos": 6,
        "bonus_payout_m": 1.7,
        "desc": "$2.2M base per Grand Prix + $1.7M bonus for finishing inside the Top 6.",
    },
]

# Close opening field: approximately 79-86, with distinct department strengths.
# Opening cash averages $400M; individual envelopes are gameplay estimates.
# See sim/economy.py and README for the real-world benchmark and sources.
INITIAL_TEAMS = [
    {
        "id": "mercedes",
        "name": "Mercedes-AMG PETRONAS F1 Team",
        "short": "Mercedes",
        "code": "MER",
        "engine": "Mercedes",
        "color": "#00d2be",
        "secondary": "#c8d0d8",
        "budget_m": 460.0,
        "annual_budget_m": 460.0,
        "sponsor_id": "veloce_energy",
        "upgrades": {
            "power_unit": 7,
            "active_aero": 7,
            "chassis": 7,
            "suspension": 6,
            "reliability": 7,
            "pit_crew": 7,
        },
    },
    {
        "id": "ferrari",
        "name": "Scuderia Ferrari HP",
        "short": "Ferrari",
        "code": "FER",
        "engine": "Ferrari",
        "color": "#e8002d",
        "secondary": "#ffffff",
        "budget_m": 460.0,
        "annual_budget_m": 460.0,
        "sponsor_id": "chronos_swiss",
        "upgrades": {
            "power_unit": 7,
            "active_aero": 7,
            "chassis": 6,
            "suspension": 7,
            "reliability": 6,
            "pit_crew": 7,
        },
    },
    {
        "id": "redbull",
        "name": "Oracle Red Bull Racing",
        "short": "Red Bull",
        "code": "RBR",
        "engine": "Red Bull Ford",
        "color": "#3671c6",
        "secondary": "#ff1e42",
        "budget_m": 450.0,
        "annual_budget_m": 450.0,
        "sponsor_id": "apex_cloud",
        "upgrades": {
            "power_unit": 6,
            "active_aero": 7,
            "chassis": 7,
            "suspension": 6,
            "reliability": 6,
            "pit_crew": 7,
        },
    },
    {
        "id": "mclaren",
        "name": "McLaren Formula 1 Team",
        "short": "McLaren",
        "code": "MCL",
        "engine": "Mercedes",
        "color": "#ff8000",
        "secondary": "#181c24",
        "budget_m": 440.0,
        "annual_budget_m": 440.0,
        "sponsor_id": "apex_cloud",
        "upgrades": {
            "power_unit": 6,
            "active_aero": 6,
            "chassis": 7,
            "suspension": 7,
            "reliability": 6,
            "pit_crew": 7,
        },
    },
    {
        "id": "racingbulls",
        "name": "Visa Cash App Racing Bulls",
        "short": "Racing Bulls",
        "code": "VRB",
        "engine": "Red Bull Ford",
        "color": "#6692ff",
        "secondary": "#ffffff",
        "budget_m": 360.0,
        "annual_budget_m": 360.0,
        "sponsor_id": "nova_fintech",
        "upgrades": {
            "power_unit": 6,
            "active_aero": 6,
            "chassis": 6,
            "suspension": 6,
            "reliability": 6,
            "pit_crew": 6,
        },
    },
    {
        "id": "alpine",
        "name": "BWT Alpine F1 Team",
        "short": "Alpine",
        "code": "ALP",
        "engine": "Mercedes",
        "color": "#0093cc",
        "secondary": "#ff87bc",
        "budget_m": 370.0,
        "annual_budget_m": 370.0,
        "sponsor_id": "nova_fintech",
        "upgrades": {
            "power_unit": 6,
            "active_aero": 6,
            "chassis": 6,
            "suspension": 6,
            "reliability": 5,
            "pit_crew": 6,
        },
    },
    {
        "id": "audi",
        "name": "Audi F1 Team",
        "short": "Audi",
        "code": "AUD",
        "engine": "Audi",
        "color": "#f50537",
        "secondary": "#b8c0c8",
        "budget_m": 390.0,
        "annual_budget_m": 390.0,
        "sponsor_id": "hyperion_ai",
        "upgrades": {
            "power_unit": 6,
            "active_aero": 6,
            "chassis": 6,
            "suspension": 5,
            "reliability": 6,
            "pit_crew": 6,
        },
    },
    {
        "id": "haas",
        "name": "MoneyGram Haas F1 Team",
        "short": "Haas",
        "code": "HAA",
        "engine": "Ferrari",
        "color": "#b6babd",
        "secondary": "#e6002b",
        "budget_m": 330.0,
        "annual_budget_m": 330.0,
        "sponsor_id": "titan_logistics",
        "upgrades": {
            "power_unit": 6,
            "active_aero": 5,
            "chassis": 6,
            "suspension": 5,
            "reliability": 6,
            "pit_crew": 6,
        },
    },
    {
        "id": "williams",
        "name": "Atlassian Williams Racing",
        "short": "Williams",
        "code": "WIL",
        "engine": "Mercedes",
        "color": "#1868db",
        "secondary": "#64c4ff",
        "budget_m": 350.0,
        "annual_budget_m": 350.0,
        "sponsor_id": "hyperion_ai",
        "upgrades": {
            "power_unit": 6,
            "active_aero": 5,
            "chassis": 5,
            "suspension": 6,
            "reliability": 6,
            "pit_crew": 6,
        },
    },
    {
        "id": "aston",
        "name": "Aston Martin Aramco F1 Team",
        "short": "Aston Martin",
        "code": "AMR",
        "engine": "Honda",
        "color": "#229971",
        "secondary": "#cedc00",
        "budget_m": 430.0,
        "annual_budget_m": 430.0,
        "sponsor_id": "titan_logistics",
        "upgrades": {
            "power_unit": 5,
            "active_aero": 6,
            "chassis": 5,
            "suspension": 6,
            "reliability": 5,
            "pit_crew": 6,
        },
    },
    {
        "id": "cadillac",
        "name": "Cadillac Formula 1 Team",
        "short": "Cadillac",
        "code": "CAD",
        "engine": "Ferrari",
        "color": "#d4af37",
        "secondary": "#1e3f8f",
        "budget_m": 360.0,
        "annual_budget_m": 360.0,
        "sponsor_id": "titan_logistics",
        "upgrades": {
            "power_unit": 6,
            "active_aero": 5,
            "chassis": 5,
            "suspension": 5,
            "reliability": 6,
            "pit_crew": 5,
        },
    },
]

# Reported 2026 USD base retainers, excluding bonuses and endorsements.
# RN365 (4 Feb 2026); $0.5-1M ranges use their $0.75M midpoint.
# Free agents and legends retain simulated contract demands.
INITIAL_DRIVERS = [
    # Mercedes
    {
        "id": "russell",
        "name": "George Russell",
        "code": "RUS",
        "number": 63,
        "team_id": "mercedes",
        "nationality": "GBR",
        "age": 28,
        "pace": 95,
        "racecraft": 92,
        "defense": 92,
        "consistency": 93,
        "tire_mgmt": 91,
        "wet_skill": 92,
        "salary_m": 34.0,
        "value_m": 46.0,
        "contract_years": 2,
        "helmet": "#00d2ff",
    },
    {
        "id": "antonelli",
        "name": "Kimi Antonelli",
        "code": "ANT",
        "number": 12,
        "team_id": "mercedes",
        "nationality": "ITA",
        "age": 20,
        "pace": 91,
        "racecraft": 89,
        "defense": 86,
        "consistency": 85,
        "tire_mgmt": 86,
        "wet_skill": 90,
        "salary_m": 2.0,
        "value_m": 36.0,
        "contract_years": 3,
        "helmet": "#00a86b",
    },
    # Ferrari
    {
        "id": "leclerc",
        "name": "Charles Leclerc",
        "code": "LEC",
        "number": 16,
        "team_id": "ferrari",
        "nationality": "MON",
        "age": 28,
        "pace": 96,
        "racecraft": 93,
        "defense": 91,
        "consistency": 91,
        "tire_mgmt": 91,
        "wet_skill": 90,
        "salary_m": 34.0,
        "value_m": 50.0,
        "contract_years": 3,
        "helmet": "#ffffff",
    },
    {
        "id": "hamilton",
        "name": "Lewis Hamilton",
        "code": "HAM",
        "number": 44,
        "team_id": "ferrari",
        "nationality": "GBR",
        "age": 41,
        "pace": 92,
        "racecraft": 95,
        "defense": 94,
        "consistency": 93,
        "tire_mgmt": 96,
        "wet_skill": 97,
        "salary_m": 60.0,
        "value_m": 38.0,
        "contract_years": 2,
        "helmet": "#ffd000",
    },
    # Red Bull Racing
    {
        "id": "verstappen",
        "name": "Max Verstappen",
        "code": "VER",
        "number": 3,
        "team_id": "redbull",
        "nationality": "NED",
        "age": 29,
        "pace": 98,
        "racecraft": 97,
        "defense": 96,
        "consistency": 96,
        "tire_mgmt": 95,
        "wet_skill": 98,
        "salary_m": 70.0,
        "value_m": 60.0,
        "contract_years": 3,
        "helmet": "#ff7300",
    },
    {
        "id": "hadjar",
        "name": "Isack Hadjar",
        "code": "HAD",
        "number": 6,
        "team_id": "redbull",
        "nationality": "FRA",
        "age": 22,
        "pace": 87,
        "racecraft": 86,
        "defense": 84,
        "consistency": 83,
        "tire_mgmt": 84,
        "wet_skill": 85,
        "salary_m": 5.0,
        "value_m": 22.0,
        "contract_years": 2,
        "helmet": "#f4d03f",
    },
    # McLaren
    {
        "id": "norris",
        "name": "Lando Norris",
        "code": "NOR",
        "number": 1,
        "team_id": "mclaren",
        "nationality": "GBR",
        "age": 26,
        "pace": 95,
        "racecraft": 91,
        "defense": 89,
        "consistency": 92,
        "tire_mgmt": 93,
        "wet_skill": 93,
        "salary_m": 30.0,
        "value_m": 48.0,
        "contract_years": 3,
        "helmet": "#ccff00",
    },
    {
        "id": "piastri",
        "name": "Oscar Piastri",
        "code": "PIA",
        "number": 81,
        "team_id": "mclaren",
        "nationality": "AUS",
        "age": 25,
        "pace": 94,
        "racecraft": 93,
        "defense": 92,
        "consistency": 93,
        "tire_mgmt": 90,
        "wet_skill": 89,
        "salary_m": 13.0,
        "value_m": 44.0,
        "contract_years": 3,
        "helmet": "#ff6b35",
    },
    # Racing Bulls
    {
        "id": "lawson",
        "name": "Liam Lawson",
        "code": "LAW",
        "number": 30,
        "team_id": "racingbulls",
        "nationality": "NZL",
        "age": 24,
        "pace": 87,
        "racecraft": 88,
        "defense": 88,
        "consistency": 86,
        "tire_mgmt": 86,
        "wet_skill": 87,
        "salary_m": 1.0,
        "value_m": 19.0,
        "contract_years": 2,
        "helmet": "#ff4d6d",
    },
    {
        "id": "lindblad",
        "name": "Arvid Lindblad",
        "code": "LIN",
        "number": 41,
        "team_id": "racingbulls",
        "nationality": "GBR",
        "age": 19,
        "pace": 86,
        "racecraft": 86,
        "defense": 82,
        "consistency": 80,
        "tire_mgmt": 81,
        "wet_skill": 85,
        "salary_m": 0.75,
        "value_m": 21.0,
        "contract_years": 3,
        "helmet": "#ffee32",
    },
    # Alpine
    {
        "id": "gasly",
        "name": "Pierre Gasly",
        "code": "GAS",
        "number": 10,
        "team_id": "alpine",
        "nationality": "FRA",
        "age": 30,
        "pace": 89,
        "racecraft": 88,
        "defense": 88,
        "consistency": 89,
        "tire_mgmt": 88,
        "wet_skill": 90,
        "salary_m": 12.0,
        "value_m": 24.0,
        "contract_years": 2,
        "helmet": "#3a86ff",
    },
    {
        "id": "colapinto",
        "name": "Franco Colapinto",
        "code": "COL",
        "number": 43,
        "team_id": "alpine",
        "nationality": "ARG",
        "age": 23,
        "pace": 86,
        "racecraft": 87,
        "defense": 84,
        "consistency": 82,
        "tire_mgmt": 84,
        "wet_skill": 85,
        "salary_m": 0.75,
        "value_m": 19.0,
        "contract_years": 2,
        "helmet": "#74c0fc",
    },
    # Audi
    {
        "id": "hulkenberg",
        "name": "Nico Hulkenberg",
        "code": "HUL",
        "number": 27,
        "team_id": "audi",
        "nationality": "GER",
        "age": 39,
        "pace": 89,
        "racecraft": 88,
        "defense": 89,
        "consistency": 91,
        "tire_mgmt": 88,
        "wet_skill": 90,
        "salary_m": 7.0,
        "value_m": 16.0,
        "contract_years": 2,
        "helmet": "#9ef01a",
    },
    {
        "id": "bortoleto",
        "name": "Gabriel Bortoleto",
        "code": "BOR",
        "number": 20,
        "team_id": "audi",
        "nationality": "BRA",
        "age": 22,
        "pace": 87,
        "racecraft": 87,
        "defense": 85,
        "consistency": 86,
        "tire_mgmt": 86,
        "wet_skill": 86,
        "salary_m": 2.0,
        "value_m": 22.0,
        "contract_years": 3,
        "helmet": "#00f5d4",
    },
    # Haas
    {
        "id": "ocon",
        "name": "Esteban Ocon",
        "code": "OCO",
        "number": 31,
        "team_id": "haas",
        "nationality": "FRA",
        "age": 30,
        "pace": 87,
        "racecraft": 87,
        "defense": 91,
        "consistency": 87,
        "tire_mgmt": 87,
        "wet_skill": 91,
        "salary_m": 7.0,
        "value_m": 19.0,
        "contract_years": 2,
        "helmet": "#ef233c",
    },
    {
        "id": "bearman",
        "name": "Oliver Bearman",
        "code": "BEA",
        "number": 87,
        "team_id": "haas",
        "nationality": "GBR",
        "age": 21,
        "pace": 87,
        "racecraft": 88,
        "defense": 85,
        "consistency": 84,
        "tire_mgmt": 84,
        "wet_skill": 86,
        "salary_m": 1.0,
        "value_m": 23.0,
        "contract_years": 3,
        "helmet": "#4cc9f0",
    },
    # Williams
    {
        "id": "sainz",
        "name": "Carlos Sainz",
        "code": "SAI",
        "number": 55,
        "team_id": "williams",
        "nationality": "ESP",
        "age": 32,
        "pace": 91,
        "racecraft": 92,
        "defense": 92,
        "consistency": 93,
        "tire_mgmt": 92,
        "wet_skill": 91,
        "salary_m": 13.0,
        "value_m": 32.0,
        "contract_years": 2,
        "helmet": "#ff2a2a",
    },
    {
        "id": "albon",
        "name": "Alexander Albon",
        "code": "ALB",
        "number": 23,
        "team_id": "williams",
        "nationality": "THA",
        "age": 30,
        "pace": 89,
        "racecraft": 89,
        "defense": 90,
        "consistency": 89,
        "tire_mgmt": 90,
        "wet_skill": 88,
        "salary_m": 12.0,
        "value_m": 25.0,
        "contract_years": 2,
        "helmet": "#ff758f",
    },
    # Aston Martin
    {
        "id": "alonso",
        "name": "Fernando Alonso",
        "code": "ALO",
        "number": 14,
        "team_id": "aston",
        "nationality": "ESP",
        "age": 45,
        "pace": 90,
        "racecraft": 96,
        "defense": 97,
        "consistency": 93,
        "tire_mgmt": 93,
        "wet_skill": 94,
        "salary_m": 20.0,
        "value_m": 24.0,
        "contract_years": 1,
        "helmet": "#00b4d8",
    },
    {
        "id": "stroll",
        "name": "Lance Stroll",
        "code": "STR",
        "number": 18,
        "team_id": "aston",
        "nationality": "CAN",
        "age": 28,
        "pace": 81,
        "racecraft": 82,
        "defense": 80,
        "consistency": 79,
        "tire_mgmt": 83,
        "wet_skill": 88,
        "salary_m": 12.0,
        "value_m": 11.0,
        "contract_years": 2,
        "helmet": "#1b4332",
    },
    # Cadillac
    {
        "id": "perez",
        "name": "Sergio Perez",
        "code": "PER",
        "number": 11,
        "team_id": "cadillac",
        "nationality": "MEX",
        "age": 36,
        "pace": 85,
        "racecraft": 89,
        "defense": 91,
        "consistency": 84,
        "tire_mgmt": 93,
        "wet_skill": 85,
        "salary_m": 8.0,
        "value_m": 16.0,
        "contract_years": 2,
        "helmet": "#b5e48c",
    },
    {
        "id": "bottas",
        "name": "Valtteri Bottas",
        "code": "BOT",
        "number": 77,
        "team_id": "cadillac",
        "nationality": "FIN",
        "age": 37,
        "pace": 87,
        "racecraft": 85,
        "defense": 86,
        "consistency": 91,
        "tire_mgmt": 89,
        "wet_skill": 87,
        "salary_m": 5.0,
        "value_m": 15.0,
        "contract_years": 2,
        "helmet": "#48cae4",
    },
    # Free Agents / Reserve & Academy Market (team_id = None)
    {
        "id": "tsunoda",
        "name": "Yuki Tsunoda",
        "code": "TSU",
        "number": 22,
        "team_id": None,
        "nationality": "JPN",
        "age": 26,
        "pace": 87,
        "racecraft": 87,
        "defense": 85,
        "consistency": 83,
        "tire_mgmt": 84,
        "wet_skill": 86,
        "salary_m": 5.5,
        "value_m": 14.0,
        "contract_years": 0,
        "helmet": "#ff5400",
    },
    {
        "id": "pourchaire",
        "name": "Theo Pourchaire",
        "code": "POU",
        "number": 98,
        "team_id": None,
        "nationality": "FRA",
        "age": 23,
        "pace": 84,
        "racecraft": 84,
        "defense": 83,
        "consistency": 83,
        "tire_mgmt": 83,
        "wet_skill": 84,
        "salary_m": 2.6,
        "value_m": 9.5,
        "contract_years": 0,
        "helmet": "#c77dff",
    },
    {
        "id": "drugovich",
        "name": "Felipe Drugovich",
        "code": "DRU",
        "number": 34,
        "team_id": None,
        "nationality": "BRA",
        "age": 26,
        "pace": 84,
        "racecraft": 83,
        "defense": 84,
        "consistency": 86,
        "tire_mgmt": 86,
        "wet_skill": 83,
        "salary_m": 2.8,
        "value_m": 9.0,
        "contract_years": 0,
        "helmet": "#ffd166",
    },
    {
        "id": "aron",
        "name": "Paul Aron",
        "code": "ARO",
        "number": 61,
        "team_id": None,
        "nationality": "EST",
        "age": 22,
        "pace": 85,
        "racecraft": 84,
        "defense": 82,
        "consistency": 82,
        "tire_mgmt": 82,
        "wet_skill": 84,
        "salary_m": 2.4,
        "value_m": 10.5,
        "contract_years": 0,
        "helmet": "#4ea8de",
    },
    {
        "id": "fornaroli",
        "name": "Leonardo Fornaroli",
        "code": "FOR",
        "number": 51,
        "team_id": None,
        "nationality": "ITA",
        "age": 21,
        "pace": 85,
        "racecraft": 85,
        "defense": 83,
        "consistency": 86,
        "tire_mgmt": 85,
        "wet_skill": 84,
        "salary_m": 2.5,
        "value_m": 12.0,
        "contract_years": 0,
        "helmet": "#38b000",
    },
    {
        "id": "browning",
        "name": "Luke Browning",
        "code": "BRO",
        "number": 46,
        "team_id": None,
        "nationality": "GBR",
        "age": 24,
        "pace": 84,
        "racecraft": 85,
        "defense": 82,
        "consistency": 82,
        "tire_mgmt": 82,
        "wet_skill": 86,
        "salary_m": 2.2,
        "value_m": 9.0,
        "contract_years": 0,
        "helmet": "#4361ee",
    },
    {
        "id": "palou",
        "name": "Alex Palou",
        "code": "PAL",
        "number": 49,
        "team_id": None,
        "nationality": "ESP",
        "age": 29,
        "pace": 88,
        "racecraft": 88,
        "defense": 87,
        "consistency": 91,
        "tire_mgmt": 90,
        "wet_skill": 86,
        "salary_m": 6.5,
        "value_m": 16.5,
        "contract_years": 0,
        "helmet": "#ff9f1c",
    },
    {
        "id": "oward",
        "name": "Pato O'Ward",
        "code": "OWA",
        "number": 29,
        "team_id": None,
        "nationality": "MEX",
        "age": 27,
        "pace": 87,
        "racecraft": 89,
        "defense": 85,
        "consistency": 83,
        "tire_mgmt": 84,
        "wet_skill": 85,
        "salary_m": 5.8,
        "value_m": 15.0,
        "contract_years": 0,
        "helmet": "#ff6d00",
    },
    {
        "id": "zhou",
        "name": "Zhou Guanyu",
        "code": "ZHO",
        "number": 24,
        "team_id": None,
        "nationality": "CHN",
        "age": 27,
        "pace": 82,
        "racecraft": 83,
        "defense": 84,
        "consistency": 87,
        "tire_mgmt": 85,
        "wet_skill": 83,
        "salary_m": 3.5,
        "value_m": 8.5,
        "contract_years": 0,
        "helmet": "#e71d36",
    },
    {
        "id": "doohan",
        "name": "Jack Doohan",
        "code": "DOO",
        "number": 17,
        "team_id": None,
        "nationality": "AUS",
        "age": 23,
        "pace": 82,
        "racecraft": 82,
        "defense": 81,
        "consistency": 80,
        "tire_mgmt": 81,
        "wet_skill": 82,
        "salary_m": 2.1,
        "value_m": 7.5,
        "contract_years": 0,
        "helmet": "#2ec4b6",
    },
    # FIA Hall of Fame Legends (Free Agents with OVR 95+)
    {
        "id": "senna",
        "name": "Ayrton Senna",
        "code": "SEN",
        "number": 8,
        "team_id": None,
        "nationality": "BRA",
        "age": 34,
        "pace": 99,
        "racecraft": 98,
        "defense": 96,
        "consistency": 95,
        "tire_mgmt": 94,
        "wet_skill": 100,
        "salary_m": 35.0,
        "value_m": 62.0,
        "contract_years": 0,
        "helmet": "#ffd000",
        "legend": True,
    },
    {
        "id": "lauda",
        "name": "Niki Lauda",
        "code": "LAU",
        "number": 2,
        "team_id": None,
        "nationality": "AUT",
        "age": 35,
        "pace": 96,
        "racecraft": 97,
        "defense": 95,
        "consistency": 99,
        "tire_mgmt": 98,
        "wet_skill": 92,
        "salary_m": 33.0,
        "value_m": 56.0,
        "contract_years": 0,
        "helmet": "#e10600",
        "legend": True,
    },
    {
        "id": "vettel",
        "name": "Sebastian Vettel",
        "code": "VET",
        "number": 5,
        "team_id": None,
        "nationality": "GER",
        "age": 37,
        "pace": 96,
        "racecraft": 96,
        "defense": 95,
        "consistency": 96,
        "tire_mgmt": 95,
        "wet_skill": 96,
        "salary_m": 31.0,
        "value_m": 52.0,
        "contract_years": 0,
        "helmet": "#f8f9fa",
        "legend": True,
    },
    {
        "id": "raikkonen",
        "name": "Kimi Räikkönen",
        "code": "RAI",
        "number": 7,
        "team_id": None,
        "nationality": "FIN",
        "age": 39,
        "pace": 97,
        "racecraft": 96,
        "defense": 96,
        "consistency": 94,
        "tire_mgmt": 95,
        "wet_skill": 95,
        "salary_m": 30.0,
        "value_m": 50.0,
        "contract_years": 0,
        "helmet": "#00b4d8",
        "legend": True,
    },
    {
        "id": "schumacher",
        "name": "Michael Schumacher",
        "code": "MSC",
        "number": 4,
        "team_id": None,
        "nationality": "GER",
        "age": 36,
        "pace": 98,
        "racecraft": 99,
        "defense": 98,
        "consistency": 98,
        "tire_mgmt": 97,
        "wet_skill": 99,
        "salary_m": 38.0,
        "value_m": 65.0,
        "contract_years": 0,
        "helmet": "#e10600",
        "legend": True,
    },
    {
        "id": "fangio",
        "name": "Juan Manuel Fangio",
        "code": "FAN",
        "number": 21,
        "team_id": None,
        "nationality": "ARG",
        "age": 43,
        "pace": 97,
        "racecraft": 99,
        "defense": 96,
        "consistency": 98,
        "tire_mgmt": 98,
        "wet_skill": 97,
        "salary_m": 36.0,
        "value_m": 60.0,
        "contract_years": 0,
        "helmet": "#415a77",
        "legend": True,
    },
    {
        "id": "prost",
        "name": "Alain Prost",
        "code": "PRO",
        "number": 15,
        "team_id": None,
        "nationality": "FRA",
        "age": 36,
        "pace": 96,
        "racecraft": 98,
        "defense": 95,
        "consistency": 99,
        "tire_mgmt": 99,
        "wet_skill": 91,
        "salary_m": 34.0,
        "value_m": 58.0,
        "contract_years": 0,
        "helmet": "#002b7f",
        "legend": True,
    },
    {
        "id": "hakkinen",
        "name": "Mika Häkkinen",
        "code": "HAK",
        "number": 9,
        "team_id": None,
        "nationality": "FIN",
        "age": 32,
        "pace": 98,
        "racecraft": 96,
        "defense": 95,
        "consistency": 94,
        "tire_mgmt": 94,
        "wet_skill": 96,
        "salary_m": 31.0,
        "value_m": 52.0,
        "contract_years": 0,
        "helmet": "#005bbb",
        "legend": True,
    },
    {
        "id": "mansell",
        "name": "Nigel Mansell",
        "code": "MAN",
        "number": 28,
        "team_id": None,
        "nationality": "GBR",
        "age": 39,
        "pace": 96,
        "racecraft": 97,
        "defense": 95,
        "consistency": 93,
        "tire_mgmt": 93,
        "wet_skill": 96,
        "salary_m": 29.0,
        "value_m": 48.0,
        "contract_years": 0,
        "helmet": "#0b3c5d",
        "legend": True,
    },
]


DRIVER_RISK_RATINGS: dict[str, int] = {
    # Active 2026 grid (22)
    "verstappen": 90,
    "lawson": 88,
    "lindblad": 88,
    "colapinto": 88,
    "antonelli": 87,
    "hadjar": 86,
    "bearman": 86,
    "leclerc": 84,
    "stroll": 84,
    "ocon": 80,
    "norris": 76,
    "gasly": 76,
    "perez": 76,
    "bortoleto": 75,
    "hamilton": 74,
    "russell": 72,
    "alonso": 70,
    "piastri": 68,
    "sainz": 66,
    "albon": 64,
    "hulkenberg": 62,
    "bottas": 55,
    # Free agents (10)
    "oward": 89,
    "doohan": 85,
    "tsunoda": 83,
    "aron": 78,
    "browning": 74,
    "pourchaire": 68,
    "fornaroli": 67,
    "palou": 64,
    "drugovich": 60,
    "zhou": 56,
    # Legends (9)
    "senna": 95,
    "mansell": 94,
    "schumacher": 89,
    "hakkinen": 80,
    "vettel": 79,
    "raikkonen": 77,
    "fangio": 60,
    "lauda": 54,
    "prost": 52,
}

for _drv in INITIAL_DRIVERS:
    _drv.setdefault("risk", DRIVER_RISK_RATINGS.get(_drv["id"], 70))


def driver_overall(driver: dict) -> float:
    """Weighted overall driver rating (0-100)."""
    return round(
        driver["pace"] * 0.30
        + driver["racecraft"] * 0.20
        + driver["consistency"] * 0.18
        + driver["tire_mgmt"] * 0.14
        + driver["defense"] * 0.10
        + driver["wet_skill"] * 0.08,
        1,
    )


def driver_risk(driver: dict) -> int:
    """Resolve a driver's risk appetite (40-99), separate from skill OVR."""
    raw = driver.get("risk")
    if raw is None:
        raw = DRIVER_RISK_RATINGS.get(driver.get("id", ""), 70)
    return max(40, min(99, int(round(raw))))


def upgrade_cost_m(dept_key: str, current_level: int) -> float:
    """Cost in $M to upgrade from current_level to current_level + 1."""
    spec = UPGRADE_DEPARTMENTS[dept_key]
    if current_level >= spec["max_level"]:
        return 0.0
    return round(spec["base_cost_m"] * (spec["cost_scale"] ** (current_level - 1)) * UPGRADE_PRICE_MULTIPLIER, 2)


def team_car_rating(team: dict) -> float:
    """Overall car performance index (0-100) derived from department levels."""
    u = team["upgrades"]
    weighted = (
        u["power_unit"] * 0.25
        + u["active_aero"] * 0.25
        + u["chassis"] * 0.20
        + u["suspension"] * 0.15
        + u["reliability"] * 0.08
        + u["pit_crew"] * 0.07
    )
    return round(55.0 + weighted * 4.5, 1)


def clone_initial_roster() -> tuple[list[dict], list[dict]]:
    return copy.deepcopy(INITIAL_TEAMS), copy.deepcopy(INITIAL_DRIVERS)


def tire_thermal_wear_mult(compound: str, temp_c: float) -> float:
    """Thermal degradation multiplier on tire wear rate.

    Inside [opt_temp_min, opt_temp_max]: 1.0 (nominal degradation rate).
    Overheating (> opt_temp_max): Non-linear accelerated degradation & blistering.
    Cold (< opt_temp_min): Cold surface graining under heavy shear loads.
    """
    spec = TIRE_COMPOUNDS.get(compound, TIRE_COMPOUNDS["MEDIUM"])
    t_min = spec.get("opt_temp_min", 95.0)
    t_max = spec.get("opt_temp_max", 113.0)
    sens = spec.get("overheat_sens", 0.028)

    if t_min <= temp_c <= t_max:
        return 1.0
    elif temp_c > t_max:
        excess = temp_c - t_max
        # Quadratic thermal degradation runaway (blistering & carcass overheating)
        return round(min(3.2, 1.0 + excess * sens + 0.0016 * (excess ** 2)), 3)
    else:
        deficit = t_min - temp_c
        # Cold graining: stiff glassy rubber under shear loads
        return round(min(1.35, 1.0 + deficit * 0.009), 3)


def tire_thermal_grip_mult(compound: str, temp_c: float) -> float:
    """Thermal effect on tire surface friction / grip.

    Inside [opt_temp_min, opt_temp_max]: 1.00 (peak chemical adhesion).
    Overheating (> opt_temp_max): Thermal fading / surface greasing (up to -15% grip).
    Cold (< opt_temp_min): Glass transition stiffness / lack of mechanical keying.
    """
    spec = TIRE_COMPOUNDS.get(compound, TIRE_COMPOUNDS["MEDIUM"])
    t_min = spec.get("opt_temp_min", 95.0)
    t_max = spec.get("opt_temp_max", 113.0)

    if t_min <= temp_c <= t_max:
        return 1.0
    elif temp_c > t_max:
        excess = temp_c - t_max
        return round(max(0.85, 1.0 - excess * 0.0055 - 0.00015 * (excess ** 2)), 3)
    else:
        deficit = t_min - temp_c
        return round(max(0.84, 1.0 - deficit * 0.0075), 3)


def tire_temp_status(compound: str, temp_c: float) -> str:
    """Human-readable temperature status string."""
    spec = TIRE_COMPOUNDS.get(compound, TIRE_COMPOUNDS["MEDIUM"])
    t_min = spec.get("opt_temp_min", 95.0)
    t_max = spec.get("opt_temp_max", 113.0)
    if temp_c > t_max + 14.0:
        return "BLISTERING"
    elif temp_c > t_max:
        return "OVERHEATING"
    elif temp_c < t_min - 10.0:
        return "COLD"
    elif temp_c < t_min:
        return "WARMING"
    else:
        return "OPTIMAL"


def track_upgrade_profile(track_or_id) -> dict:
    """Return circuit DNA upgrade weights and recommended downforce setup."""
    track_id = track_or_id if isinstance(track_or_id, str) else getattr(track_or_id, "id", "")
    if track_id in CIRCUIT_UPGRADE_PROFILES:
        return copy.deepcopy(CIRCUIT_UPGRADE_PROFILES[track_id])

    # Geometric fallback for custom/unknown circuits using straight-mode ratio
    if track_or_id is not None and not isinstance(track_or_id, str) and getattr(track_or_id, "stations", None):
        stations = track_or_id.stations
        straight_frac = sum(1 for st in stations if st.get("straight_mode")) / max(1, len(stations))
        if straight_frac >= 0.44:
            return {
                "category": "POWER",
                "label": "High-Speed Power Bias",
                "recommended_df": -1,
                "weights": {"power_unit": 1.32, "active_aero": 1.15, "chassis": 0.85, "suspension": 0.80, "reliability": 1.05, "pit_crew": 1.0},
            }
        if straight_frac <= 0.22:
            return {
                "category": "DOWNFORCE",
                "label": "High-Downforce Technical Bias",
                "recommended_df": 1,
                "weights": {"power_unit": 0.76, "active_aero": 1.24, "chassis": 1.28, "suspension": 1.28, "reliability": 1.0, "pit_crew": 1.05},
            }
    return copy.deepcopy(DEFAULT_CIRCUIT_PROFILE)


def effective_track_upgrades(upgrades: dict, track_or_id) -> dict[str, float]:
    """Scale upgrade levels relative to baseline 5.0 by circuit-specific department weights."""
    src = upgrades.get("upgrades") if isinstance(upgrades.get("upgrades"), dict) else upgrades
    profile = track_upgrade_profile(track_or_id)
    weights = profile["weights"]
    scaled: dict[str, float] = {}
    for k, raw_val in src.items():
        w = weights.get(k, 1.0)
        scaled[k] = round(max(0.5, 5.0 + (float(raw_val) - 5.0) * w), 3)
    return scaled


def circuit_car_rating(team: dict, track_or_id) -> float:
    """Circuit-adjusted performance index (0-100) emphasizing track-relevant departments."""
    eff = effective_track_upgrades(team["upgrades"], track_or_id)
    weighted = (
        eff["power_unit"] * 0.25
        + eff["active_aero"] * 0.25
        + eff["chassis"] * 0.20
        + eff["suspension"] * 0.15
        + eff["reliability"] * 0.08
        + eff["pit_crew"] * 0.07
    )
    return round(55.0 + weighted * 4.5, 1)


def create_pu_pool() -> dict:
    """Create a fresh seasonal Power Unit & Gearbox component allocation pool for one driver."""
    return {
        comp: {
            "wear": 0.0,
            "used": 1,
            "limit": spec["limit"],
            "active_idx": 1,
            "pending_penalty": 0,
        }
        for comp, spec in PU_COMPONENT_SPECS.items()
    }


def create_weekend_tire_sets(alloc_counts: dict | None = None) -> dict[str, list[dict]]:
    """Build per-set weekend tyre inventory tracking Fresh vs. Scrubbed state and residual wear."""
    counts = alloc_counts or DEFAULT_WEEKEND_TIRE_SETS
    sets: dict[str, list[dict]] = {}
    for comp, count in counts.items():
        prefix = TIRE_COMPOUNDS.get(comp, {}).get("code", comp[:1])
        sets[comp] = [
            {
                "id": f"{prefix}{i + 1}",
                "wear": 0.0,
                "age_laps": 0,
                "scrubbed": False,
                "in_use": False,
            }
            for i in range(max(0, int(count)))
        ]
    return sets


def summarize_tire_sets(driver_sets: dict[str, list[dict]]) -> dict[str, dict]:
    """Return {compound: {'total': int, 'fresh': int, 'scrubbed': int, 'min_scrub_wear': float}}."""
    out: dict[str, dict] = {}
    for comp in TIRE_COMPOUNDS:
        items = [s for s in driver_sets.get(comp, []) if not s.get("in_use")]
        fresh = sum(1 for s in items if not s.get("scrubbed"))
        scrub_items = [s for s in items if s.get("scrubbed")]
        min_w = round(min((s.get("wear", 0.0) for s in scrub_items), default=0.0) * 100.0, 1)
        out[comp] = {
            "total": len(items),
            "fresh": fresh,
            "scrubbed": len(scrub_items),
            "min_scrub_wear": min_w,
        }
    return out

