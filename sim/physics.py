"""High-Fidelity 2D 2026 F1 Physics, Rigid Non-Overlap Solver, Knockout Qualifying, Maneuvers & Pit Variance."""

from __future__ import annotations
import math
import random
from typing import Any
from types import SimpleNamespace
from sim.data import TIRE_COMPOUNDS, team_car_rating
from sim.tracks import CompiledTrack
from sim.track_geometry import pit_lateral_offset, in_pit_tunnel
from sim.radio import RadioDispatcher
from sim.car_geometry import (CAR_LEN_PX,CAR_WID_PX,CAR_HALF_LENGTH,CAR_HALF_WIDTH,
                              CAR_PAIR_RADIUS_SQ,SC_HALF_LENGTH,SC_HALF_WIDTH)

GRAVITY = 9.81
PIT_SPEED_LIMIT_MS = 22.22  # 80 km/h FIA pit lane limit
DERATE_START_MS = 80.56     # 290 km/h standard 2026 MGU-K derating threshold
DERATE_END_MS = 96.00       # 345.6 km/h standard ceiling
OVERTAKE_MAX_MS = 101.50    # 365.4 km/h Strong Overtake Mode + electrical punch + slipstream ceiling

TEAM_GARAGE_INDEX = {
    "mercedes": 0,
    "ferrari": 1,
    "redbull": 2,
    "mclaren": 3,
    "racingbulls": 4,
    "alpine": 5,
    "audi": 6,
    "haas": 7,
    "williams": 8,
    "aston": 9,
    "cadillac": 10,
}


def build_speed_envelope(track: CompiledTrack) -> tuple[list[float], list[bool]]:
    """Precompute reference cornering + backward-integrated 4.5G braking speed envelope (m/s)."""
    m = track.NUM_STATIONS
    ds = track.ds_m
    mu_ref = 3.95
    v_corner = []
    for k in range(m):
        curv = track.stations[k]["curv"]
        if curv < 0.0022:
            v_c = 98.5
        else:
            # Low-speed hairpins are purely mechanical-grip limited; high-speed sweepers enjoy massive aero downforce
            aero_factor = 0.38 + 0.68 * min(1.0, 0.0058 / max(curv, 0.002))
            v_c = math.sqrt((mu_ref * aero_factor * GRAVITY) / max(curv, 1e-4))
            # Authentic F1 hairpin apex speeds: slow hairpins (Monaco, Montreal T10) drop to 58-75 km/h
            v_c = min(98.5, max(15.2, v_c))
        v_corner.append(v_c)

    v_env = list(v_corner)
    a_brake = 43.0
    for _ in range(2):
        for step in range(m - 1, -1, -1):
            nxt = (step + 1) % m
            v_max_brake = math.sqrt(v_env[nxt] * v_env[nxt] + 2.0 * a_brake * ds)
            if v_max_brake < v_env[step]:
                v_env[step] = v_max_brake

    is_braking = [v_env[k] < v_corner[k] - 2.2 for k in range(m)]
    return v_env, is_braking


def compute_lateral_screen_px(track: CompiledTrack, d: float, s_m:float|None=None) -> float:
    """Continuous lateral mapping from normalized lane coordinate d to screen pixels."""
    return track.lateral_to_px(d,s_m)


def _sat_obb_penetration(c1: "CarState", c2: "CarState", half_l: float = CAR_HALF_LENGTH, half_w: float = CAR_HALF_WIDTH,
                         other_half_l:float|None=None,other_half_w:float|None=None) -> tuple[float, float, float, float] | None:
    """Exact 4-axis 2D Separating Axis Theorem check for two oriented F1 car bounding boxes."""
    ch1, sh1 = math.cos(c1.heading), math.sin(c1.heading)
    ch2, sh2 = math.cos(c2.heading), math.sin(c2.heading)
    cx_d = c2.x-c1.x
    cy_d = c2.y-c1.y
    ac = abs(ch1 * ch2 + sh1 * sh2)
    as_ = abs(ch1 * sh2 - sh1 * ch2)
    hl2=half_l if other_half_l is None else other_half_l
    hw2=half_w if other_half_w is None else other_half_w
    req_l = half_l + hl2*ac + hw2*as_
    req_w = half_w + hw2*ac + hl2*as_

    pen_l1 = req_l - abs(cx_d * ch1 + cy_d * sh1)
    if pen_l1 <= 0.0:
        return None
    pen_w1 = req_w - abs(-cx_d * sh1 + cy_d * ch1)
    if pen_w1 <= 0.0:
        return None
    pen_l2 = hl2+half_l*ac+half_w*as_ - abs(cx_d * ch2 + cy_d * sh2)
    if pen_l2 <= 0.0:
        return None
    pen_w2 = hw2+half_w*ac+half_l*as_ - abs(-cx_d * sh2 + cy_d * ch2)
    if pen_w2 <= 0.0:
        return None
    return pen_l1, pen_w1, pen_l2, pen_w2


def enforce_2d_car_separation(
    track: CompiledTrack,
    cars: list["CarState"],
    allow_passing: bool,
    update_xy_fn,
    collision_cb=None,
) -> None:
    """
    Multi-lane traffic assignment + exact 4-axis SAT 2D oriented bounding-box non-overlap solver.
    Guarantees cars never overlap on screen while allowing smooth side-by-side overtaking.
    """
    L = track.length_m
    px_per_m = track.px_per_m
    min_long_m = (CAR_LEN_PX * 1.35) / px_per_m
    min_pit_long_m = (CAR_LEN_PX * 1.06) / track.pit_px_per_m
    half_usable = track.track_width_px * 0.39

    # 0. Sync world (x, y, heading) for all cars
    for c in cars:
        c._tick_lat_shift = 0.0
        c._tick_long_shift = 0.0
        update_xy_fn(c)

    # 1. Pit Fast-Lane longitudinal queue spacing (STOPPED cars sit in the separate garage apron)
    fast_pit_cars = [c for c in cars if c.in_pits and not c.dnf and c.pit_phase != "STOPPED"]
    if len(fast_pit_cars) > 1:
        pit_ref = track.pit_entry_s * 0.96
        fast_pit_cars.sort(key=lambda c: (c.s - pit_ref) % L, reverse=True)
        for i in range(1, len(fast_pit_cars)):
            ahead = fast_pit_cars[i - 1]
            behind = fast_pit_cars[i]
            ds_m = (ahead.s - behind.s) % L
            if 0.0 <= ds_m < min_pit_long_m and abs(ahead.pit_apron - behind.pit_apron) < 0.75:
                deficit = min_pit_long_m - ds_m
                budget_long = max(0.0, behind.v * 0.05 * 0.60 - getattr(behind, "_tick_long_shift", 0.0))
                soft_shift = min(deficit * 0.30, budget_long)
                behind._tick_long_shift = getattr(behind, "_tick_long_shift", 0.0) + soft_shift
                behind.total_dist -= soft_shift
                behind.s = behind.total_dist % L
                if behind.v > ahead.v:
                    behind.v = max(ahead.v, behind.v - 22.0 * 0.05)

    # 2. On-track multi-lane selection & spline separation
    on_track = [c for c in cars if not c.in_pits and not c.dnf and c.spin_timer <= 0.0]
    n_on = len(on_track)
    if n_on > 1:
        lane_candidates = [0.0, -0.74, 0.74, -0.46, 0.46, -0.86, 0.86]

        for c in on_track:
            blockers = []
            for o in on_track:
                if o is c:
                    continue
                ds_m = (o.s - c.s) % L
                if 0.0 <= ds_m < min_long_m * 1.65:
                    if ds_m > 0.01 or o.total_dist > c.total_dist:
                        blockers.append((ds_m, o))
            if not blockers:
                continue

            blockers.sort(key=lambda x: x[0])
            nearest_ds, nearest_ahead = blockers[0]

            if (c.lap > nearest_ahead.lap or getattr(nearest_ahead, "blue_flag", False)) and allow_passing:
                nearest_ahead.target_d = 0.82 * track.pit_side

            is_team_yield = (c.team_id == nearest_ahead.team_id and getattr(nearest_ahead, "team_order", "") == "YIELD")
            wants_pass = (
                allow_passing
                and not (c.team_id == nearest_ahead.team_id and c.team_order == "HOLD")
                and (
                    c.v > nearest_ahead.v + 0.35
                    or c.maneuver_pass_timer > 0.0
                    or c.battle_with == nearest_ahead.driver_id
                    or is_team_yield
                )
            )
            if wants_pass:
                cur_target_px = compute_lateral_screen_px(track, c.target_d,c.s)
                target_blocked = any(
                    abs(cur_target_px - compute_lateral_screen_px(track, b.d,b.s)) < CAR_WID_PX * 1.03
                    for _, b in blockers
                )
                if target_blocked:
                    best_lane = None
                    best_cost = 999.0
                    for cand in lane_candidates:
                        cand_px = compute_lateral_screen_px(track, cand,c.s)
                        if all(
                            abs(cand_px - compute_lateral_screen_px(track, b.d,b.s)) >= CAR_WID_PX * 1.03
                            for _, b in blockers
                        ):
                            cost = abs(cand - c.d) + abs(cand) * 0.15
                            if cost < best_cost:
                                best_cost = cost
                                best_lane = cand
                    if best_lane is not None:
                        c.target_d = best_lane

        on_track.sort(key=lambda c: c.total_dist, reverse=True)
        for _ in range(2):
            for i in range(n_on):
                c = on_track[i]
                for j in range(n_on):
                    if i == j:
                        continue
                    o = on_track[j]
                    ds_m = (o.s - c.s) % L
                    if ds_m >= min_long_m or ds_m > L * 0.45:
                        continue
                    if ds_m < 0.02 and c.total_dist > o.total_dist:
                        continue
                    lat_o = compute_lateral_screen_px(track, o.d,o.s)
                    lat_c = compute_lateral_screen_px(track, c.d,c.s)
                    lat_sep = abs(lat_o - lat_c)

                    is_team_swap = (c.team_id == o.team_id and getattr(o, "team_order", "") == "YIELD")
                    is_blue_yield = (c.lap > o.lap or getattr(o, "blue_flag", False) or is_team_swap)
                    req_lat = CAR_WID_PX * 0.62 if is_blue_yield else CAR_WID_PX * 0.84
                    is_passing = (
                        c.maneuver_pass_timer > 0.0
                        or getattr(o, "maneuver_pass_timer", 0.0) > 0.0
                        or c.maneuver_timer > 0.0
                        or is_team_swap
                    )
                    if (lat_sep >= req_lat or is_passing) and allow_passing:
                        if lat_sep < CAR_WID_PX:
                            need_d = min(0.12, (CAR_WID_PX - lat_sep) / half_usable)
                            if c.d >= o.d:
                                c.target_d = min(0.92, c.target_d + need_d * 0.40)
                                o.target_d = max(-0.92, o.target_d - need_d * 0.40)
                            else:
                                c.target_d = max(-0.92, c.target_d - need_d * 0.40)
                                o.target_d = min(0.92, o.target_d + need_d * 0.40)
                        if lat_sep >= CAR_WID_PX - 0.05 or is_passing:
                            continue

                    deficit = min_long_m - ds_m
                    if deficit > 0:
                        if c.v > o.v:
                            if c.accel > -22.0:
                                c.v = max(o.v * 0.98, c.v - 12.0 * 0.05)
                        # Strict budget guarantee: cumulative shift never causes negative forward displacement
                        budget_long = max(0.0, c.v * 0.05 * 0.60 - getattr(c, "_tick_long_shift", 0.0))
                        soft_shift = min(deficit * 0.20, budget_long)
                        c._tick_long_shift = getattr(c, "_tick_long_shift", 0.0) + soft_shift
                        c.total_dist -= soft_shift
                        c.s = c.total_dist % L

    # 3. Update world (x, y) and run exact 4-axis SAT OBB verification pass (handles hairpins, yaw & pit merges)
    for c in cars:
        update_xy_fn(c)

    vis_cars = [c for c in cars if (not c.dnf) or (c.dnf_timer > 0.0)]
    n_vis = len(vis_cars)
    for pass_idx in range(14):
        any_overlap = False
        for i in range(n_vis):
            c1 = vis_cars[i]
            for j in range(i + 1, n_vis):
                c2 = vis_cars[j]
                if in_pit_tunnel(track,c1) != in_pit_tunnel(track,c2):
                    continue
                dx = c2.x - c1.x
                dy = c2.y - c1.y
                if dx * dx + dy * dy >= CAR_PAIR_RADIUS_SQ:
                    continue

                arc_fwd = (c1.s - c2.s) % L
                arc_bwd = L - arc_fwd
                if track.has_overpass and min(arc_fwd, arc_bwd) > 250.0:
                    continue

                c1_off = c1.dnf or c1.spin_timer > 0.0
                c2_off = c2.dnf or c2.spin_timer > 0.0
                if c1_off and not c2_off:
                    avoid_side = 1.0 if c2.d >= c1.d else -1.0
                    c2.target_d = max(-0.93, min(0.93, c2.d + avoid_side * 0.15))
                elif c2_off and not c1_off:
                    avoid_side = 1.0 if c1.d >= c2.d else -1.0
                    c1.target_d = max(-0.93, min(0.93, c1.d + avoid_side * 0.15))

                sat = _sat_obb_penetration(c1, c2)
                if sat is None:
                    continue

                in_active_pass = (
                    (c1.maneuver_pass_timer > 0.0 and c1.maneuver_target_id == c2.driver_id)
                    or (c2.maneuver_pass_timer > 0.0 and c2.maneuver_target_id == c1.driver_id)
                    or (c1.battle_with == c2.driver_id and c2.battle_with == c1.driver_id)
                )
                severe_impact = (
                    abs(c1.v - c2.v) > 6.5
                    and min(sat[0], sat[2]) > 2.2
                    and min(sat[1], sat[3]) > 1.8
                )
                if pass_idx == 0 and severe_impact and collision_cb is not None and not in_active_pass and not c1.in_pits and not c2.in_pits and not c1.dnf and not c2.dnf:
                    collision_cb(c1, c2, sat)

                any_overlap = True
                pen_l1, pen_w1, pen_l2, pen_w2 = sat

                if arc_fwd < arc_bwd or (abs(arc_fwd - arc_bwd) < 0.05 and c1.total_dist >= c2.total_dist):
                    ahead, behind = c1, c2
                else:
                    ahead, behind = c2, c1

                # Case A: Pit entry/exit merge alongside an on-track car -> steer on-track car clear of pit blend line
                if ahead.in_pits != behind.in_pits and not c1_off and not c2_off:
                    c_trk = behind if not behind.in_pits else ahead
                    lat_budget = max(0.0, 0.10 - getattr(c_trk, "_tick_lat_shift", 0.0))
                    need_d = min(lat_budget, (max(pen_w1, pen_w2) + 0.20) / half_usable)
                    if need_d > 0.001:
                        new_d = max(-0.93, min(0.93, c_trk.d - track.pit_side * need_d))
                        c_trk._tick_lat_shift = getattr(c_trk, "_tick_lat_shift", 0.0) + abs(new_d - c_trk.d)
                        c_trk.d = new_d
                        c_trk.target_d = c_trk.d
                        update_xy_fn(c_trk)
                        if _sat_obb_penetration(c1, c2) is None:
                            continue

                # Case B: Side-by-side on track -> spread laterally with strict per-tick shift budgeting
                min_pen_w = min(pen_w1, pen_w2)
                min_pen_l = min(pen_l1, pen_l2)
                is_lateral = (min_pen_w <= min_pen_l) or (abs(ahead.d - behind.d) > 0.14)
                if is_lateral and not ahead.in_pits and not behind.in_pits and not c1_off and not c2_off and allow_passing:
                    lat_budget_a = max(0.0, 0.055 - getattr(ahead, "_tick_lat_shift", 0.0))
                    lat_budget_b = max(0.0, 0.055 - getattr(behind, "_tick_lat_shift", 0.0))
                    need_d = min(0.14, (max(pen_w1, pen_w2) + 0.15) / half_usable)
                    max_shift_a = min(lat_budget_a, need_d * 0.50)
                    max_shift_b = min(lat_budget_b, need_d * 0.50)
                    if max_shift_a > 0.001 or max_shift_b > 0.001:
                        if behind.d >= ahead.d:
                            new_a = max(-0.93, ahead.d - max_shift_a)
                            new_b = min(0.93, behind.d + max_shift_b)
                        else:
                            new_a = min(0.93, ahead.d + max_shift_a)
                            new_b = max(-0.93, behind.d - max_shift_b)
                        ahead._tick_lat_shift = getattr(ahead, "_tick_lat_shift", 0.0) + abs(new_a - ahead.d)
                        behind._tick_lat_shift = getattr(behind, "_tick_lat_shift", 0.0) + abs(new_b - behind.d)
                        ahead.d = new_a
                        behind.d = new_b
                        ahead.target_d = ahead.d
                        behind.target_d = behind.d
                        update_xy_fn(ahead)
                        update_xy_fn(behind)
                        continue

                # Case C: Soft longitudinal spline deceleration & damping (NO massive teleportation)
                if c1.in_pits and c2.in_pits:
                    # One car parked in garage stall and the other driving down the fast lane:
                    # They occupy distinct lateral lanes and must never block each other!
                    if (c1.pit_phase == "STOPPED" and c2.pit_phase != "STOPPED") or (c2.pit_phase == "STOPPED" and c1.pit_phase != "STOPPED"):
                        moving = c1 if c2.pit_phase == "STOPPED" else c2
                        moving.v = max(moving.v, PIT_SPEED_LIMIT_MS * 0.90)
                        continue

                mover = behind
                sign_dir = -1.0
                if behind.pit_phase == "STOPPED" and ahead.pit_phase != "STOPPED":
                    mover = ahead
                    sign_dir = -1.0 if ahead.pit_phase == "ENTRY" else 1.0

                for _ in range(2):
                    sat_now = _sat_obb_penetration(c1, c2)
                    if sat_now is None:
                        break
                    pl1, _pw1, pl2, _pw2 = sat_now
                    loc_px_m = max(0.18, track.px_per_m)
                    pen_l = min(max(pl1, pl2), 4.2)
                    budget_long = max(0.0, mover.v * 0.05 * 0.60 - getattr(mover, "_tick_long_shift", 0.0))
                    shift_m = min((pen_l + 0.20) / loc_px_m, budget_long)
                    if shift_m > 0.0001:
                        mover._tick_long_shift = getattr(mover, "_tick_long_shift", 0.0) + shift_m
                        mover.total_dist += sign_dir * shift_m
                        mover.s = mover.total_dist % L
                    if sign_dir < 0.0 and not mover.dnf and mover.pit_phase != "STOPPED":
                        if mover.v > ahead.v:
                            if mover.accel > -22.0:
                                mover.v = max(ahead.v, mover.v - 12.0 * 0.05)
                    update_xy_fn(mover)

        if not any_overlap:
            break

    # 4. Exact Minimum-Translation-Vector (MTV) world-coordinate failsafe for extreme multi-car 90-deg corner wedges
    for _ in range(8):
        mtv_hit = False
        for i in range(n_vis):
            c1 = vis_cars[i]
            for j in range(i + 1, n_vis):
                c2 = vis_cars[j]
                if in_pit_tunnel(track,c1) != in_pit_tunnel(track,c2):
                    continue
                dx = c2.x - c1.x
                dy = c2.y - c1.y
                if dx * dx + dy * dy >= CAR_PAIR_RADIUS_SQ:
                    continue
                if track.has_overpass and min((c1.s - c2.s) % L, (c2.s - c1.s) % L) > 250.0:
                    continue
                sat = _sat_obb_penetration(c1, c2)
                if sat is None:
                    continue
                mtv_hit = True
                pl1, pw1, pl2, pw2 = sat
                ch1, sh1 = math.cos(c1.heading), math.sin(c1.heading)
                ch2, sh2 = math.cos(c2.heading), math.sin(c2.heading)
                cx_d = c2.x-c1.x
                cy_d = c2.y-c1.y
                candidates = [
                    (pl1, ch1, sh1),
                    (pw1, -sh1, ch1),
                    (pl2, ch2, sh2),
                    (pw2, -sh2, ch2),
                ]
                pen_min, ax, ay = min(candidates, key=lambda item: item[0])
                if cx_d * ax + cy_d * ay < 0.0:
                    ax, ay = -ax, -ay
                push = 0.5 * (pen_min + 0.55)
                c1.x = round(c1.x - ax * push, 2)
                c1.y = round(c1.y - ay * push, 2)
                c2.x = round(c2.x + ax * push, 2)
                c2.y = round(c2.y + ay * push, 2)
        if not mtv_hit:
            break


class CarState:
    """Live state of a single F1 car on the 2D circuit."""

    def __init__(
        self,
        driver: dict,
        team: dict,
        grid_pos: int,
        start_compound: str,
        total_laps: int,
        max_battery_mj: float = 4.0,
    ):
        self.driver_id: str = driver["id"]
        self.name: str = driver["name"]
        self.code: str = driver["code"]
        self.number: int = driver["number"]
        self.helmet: str = driver["helmet"]

        self.team_id: str = team["id"]
        self.team_short: str = team["short"]
        self.team_color: str = team["color"]
        self.secondary_color: str = team["secondary"]

        self.skills = {
            "pace": driver["pace"],
            "racecraft": driver["racecraft"],
            "defense": driver["defense"],
            "consistency": driver["consistency"],
            "tire_mgmt": driver["tire_mgmt"],
            "wet_skill": driver["wet_skill"],
        }
        self.upgrades = dict(team["upgrades"])
        self.car_perf_index: float = team_car_rating(team)
        self.grip_snapshot: float = 1.0

        self.grid_pos: int = grid_pos
        self.pos: int = grid_pos
        self.s: float = 0.0
        self.total_dist: float = 0.0
        self.lap: int = 1
        self.laps_completed: int = 0
        self.crossed_start_line: bool = False
        self.d: float = 0.0
        self.target_d: float = 0.0
        self.grid_start_d: float = 0.0
        self.v: float = 0.0
        self.accel: float = 0.0
        self.braking: bool = False
        self.sparks: bool = False
        self.smoke: float = 0.0

        self.x: float = 0.0
        self.y: float = 0.0
        self.heading: float = 0.0
        self._heading_tick: int = -1
        self._has_initial_heading: bool = False

        # 2026 Active Aero & Hybrid ERS / Overtake Mode & Classic DRS
        self.aero_mode: str = "CORNER"
        self.max_battery_mj: float = float(max_battery_mj)
        self.battery_mj: float = float(max_battery_mj)

        self.overtake_eligible: bool = False
        self.overtake_active: bool = False
        self.drs_eligible: bool = False
        self.drs_eligible_zone: int | None = None
        self.drs_active: bool = False
        self.boost_active: bool = False
        self.recharging: bool = False

        # Tires, Fuel, Damage
        self.compound: str = start_compound
        self.compounds_used: set[str] = {start_compound}
        self.tire_wear: float = random.uniform(0.01, 0.04)
        self.tire_age_laps: int = 0
        self.tire_temp: float = 96.0
        self.fuel_kg: float = round(total_laps * 1.75 + 2.0, 2)
        self.wing_damage: float = 0.0
        self.wing_damage_side: str = "NONE"  # "NONE", "LEFT", "RIGHT", "BOTH"
        self.steer_angle: float = 0.0         # Dynamic steering wheel angle in radians
        self.body_slip_angle: float = 0.0     # Vehicle slip / yaw drift in radians
        self.g_lat: float = 0.0               # Lateral G-force
        self.pit_blend_active: bool = False   # True while bounded by pit exit line past Turn 1/2
        self.driver_line_bias: float = round(random.gauss(0.0, 0.032), 3)

        # Strategy & Pit Wall Controls
        self.auto_strategy: bool = True
        self.box_this_lap: bool = False
        self.next_compound: str = "HARD" if start_compound != "HARD" else "MEDIUM"
        self.pace_mode: str = "BALANCED"
        self.ers_mode: str = "AUTO"
        self.team_order: str = "FREE"
        self.swap_target_id: str | None = None
        self.swap_pass_id: str | None = None

        # Pit Lane State
        self.in_pits: bool = False
        self.pit_phase: str = "NONE"       # NONE, ENTRY, STOPPED, EXIT
        self.pit_entry_d: float = 0.0
        self.pit_apron: float = 0.0
        self.pit_stop_timer: float = 0.0
        self.pit_stops: int = 0
        self.last_pit_duration: float = 0.0
        self.pit_speed_checked: bool = False

        # Knockout Qualifying State
        self.eliminated: bool = False
        self.elim_stage: str = ""
        self.locked_grid_pos: int | None = None

        # Timing & Classification
        self.lap_start_time: float = 0.0
        self.last_lap_time: float | None = None
        self.best_lap_time: float | None = None
        self.current_sector_times: list[float | None] = [None, None, None]
        self.last_sector_times: list[float | None] = [None, None, None]
        self.best_sector_times: list[float | None] = [None, None, None]
        self.sector_start_time: float = 0.0
        self.quali_sector_plan: list[float] | None = None
        self.gap_to_leader: float = 0.0
        self.interval_ahead: float = 0.0
        self.finished: bool = False
        self.finish_time: float = 0.0
        self.dnf: bool = False
        self.dnf_reason: str = ""
        self.dnf_timer: float = 0.0

        # Overtaking Maneuvers, Incidents & FIA Stewards Penalties
        self.maneuver: str = ""
        self.maneuver_timer: float = 0.0
        self.maneuver_pass_timer: float = 0.0
        self.maneuver_target_id: str | None = None
        self.maneuver_attempt_cooldown: float = 0.0
        self.spin_timer: float = 0.0
        self.spin_omega: float = 0.0
        self.spin_lateral_dir: float = 0.0
        self.spin_rebound_done: bool = False
        self.track_limits_strikes: int = 0
        self.time_penalty_s: int = 0
        self.served_penalties_s: int = 0
        self.penalty_points_season: int = int(driver.get("penalty_points", 0))
        self.penalty_points_added: int = 0
        self.drive_through_pending: bool = False
        self.drive_through_laps_left: int = 0
        self.battle_with: str | None = None
        self.overtake_cooldown: float = 0.0
        self.contact_cooldown: float = 0.0
        self.repair_cost_m: float = 0.0

        # FIA Blue Flag AI
        self.blue_flag: bool = False
        self.blue_flag_timer: float = 0.0

        # FIA Rule 33.4 Defensive Maneuvers State
        self.defense_moves: int = 0
        self.defending_side: float = 0.0
        self.attacking_side: float = 0.0
        self.defense_timer: float = 0.0

        # Team Radio & Tailing Dynamics
        self.tailing_timer: float = 0.0
        self.last_radio_time: float = -99.0
        self.radio_box_announced: bool = False
        self.cliff_radio_triggered: bool = False
        self.inlap_push_announced: bool = False

        self.planned_pit_lap: int = max(5, int(total_laps * random.uniform(0.38, 0.56)))

    def record_sector(self, index: int, seconds: float) -> None:
        seconds = round(seconds, 3)
        self.current_sector_times[index] = seconds
        best = self.best_sector_times[index]
        if seconds > 0 and (best is None or seconds < best):
            self.best_sector_times[index] = seconds

    def complete_sector_lap(self) -> None:
        self.last_sector_times = self.current_sector_times[:]
        self.current_sector_times = [None, None, None]


class QualifyingSession:
    """3-Stage FIA Knockout Qualifying (Q1/Q2/Q3 or Sprint SQ1/SQ2/SQ3) with non-overlapping traffic."""

    def __init__(
        self,
        track: CompiledTrack,
        teams_by_id: dict[str, dict],
        active_drivers: list[dict],
        wetness: float,
        is_sprint_quali: bool = False,
        regulations: dict | None = None,
    ):
        self.track = track
        self.is_sprint_quali = is_sprint_quali
        self.regulations = regulations or {
            "era_id": "2026_HYBRID",
            "ice_power_mult": 1.0,
            "max_battery_mj": 4.0,
            "has_active_aero": True,
            "has_classic_drs": False,
        }
        self.v_env, self.is_braking = build_speed_envelope(track)
        # Qualifying uses modeled flying laps with accelerated on-track motion.
        # Split the same modeled time by each sector's reference driving time.
        sector_weights = [0.0, 0.0, 0.0]
        for station, speed in zip(track.stations, self.v_env):
            sector_weights[station["sector"] - 1] += track.ds_m / speed
        self.sector_fractions = [w / sum(sector_weights) for w in sector_weights]
        self.wetness: float = wetness
        self.finished: bool = False

        if is_sprint_quali:
            self.stages = [("SQ1", 180.0, 16), ("SQ2", 180.0, 10), ("SQ3", 180.0, 0)]
        else:
            self.stages = [("Q1", 180.0, 16), ("Q2", 180.0, 10), ("Q3", 180.0, 0)]

        self.stage_idx: int = 0
        self.stage_elapsed: float = 0.0
        self.elapsed: float = 0.0
        self.tick_count: int = 0
        self._current_dt: float = 0.05
        self.fastest_time: float | None = None
        self.fastest_driver_id: str | None = None

        start_comp = self._stage_compound()
        self.cars: list[CarState] = []
        shuffled = list(active_drivers)
        random.shuffle(shuffled)
        n_drv = max(len(shuffled), 1)
        for idx, drv in enumerate(shuffled):
            team = teams_by_id[drv["team_id"]]
            max_bat = float(self.regulations.get("max_battery_mj", 4.0))
            car = CarState(drv, team, idx + 1, start_comp, 3, max_battery_mj=max_bat)
            car.max_battery_mj = float(self.regulations.get("max_battery_mj", 4.0))
            car.battery_mj = car.max_battery_mj
            # Evenly space all 22 cars around 92% of the circuit (~220m+ apart, zero overlap)
            car.total_dist = ((0.06 + 0.90 * (idx / n_drv)) % 1.0) * track.length_m
            car.s = car.total_dist % track.length_m
            car.laps_completed = int(car.total_dist // track.length_m)
            car.v = 68.0
            car.pace_mode = "PUSH"
            car.ers_mode = "BOOST"
            self._update_xy(car)
            self.cars.append(car)

        self.standings: list[CarState] = list(self.cars)
        self._resort()

    @property
    def stage_name(self) -> str:
        return self.stages[self.stage_idx][0]

    @property
    def stage_duration(self) -> float:
        return self.stages[self.stage_idx][1]

    @property
    def cut_line(self) -> int:
        return self.stages[self.stage_idx][2]

    @property
    def stage_time_left(self) -> float:
        return max(0.0, self.stage_duration - self.stage_elapsed)

    def _stage_compound(self) -> str:
        if self.wetness > 0.55:
            return "WET"
        if self.wetness > 0.16:
            return "INTER"
        if self.is_sprint_quali and self.stage_idx in (0, 1):
            return "MEDIUM"
        return "SOFT"

    def _update_xy(self, car: CarState) -> None:
        if car.in_pits:
            psmp = self.track.sample_pit(car.s)
            # Generous clearance: fast-lane runs on track verge side (-2.8px); stopped car sits in garage stall (+8.6px)
            apron_px = pit_lateral_offset(self.track,car.s,car.pit_apron)
            nx_p, ny_p = -psmp["ty"], psmp["tx"]
            car.x = round(psmp["x"] + nx_p * apron_px, 2)
            car.y = round(psmp["y"] + ny_p * apron_px, 2)
            car.heading = round(math.atan2(psmp["ty"], psmp["tx"]), 4)
            return
        smp = self.track.sample(car.s)
        lat_px = compute_lateral_screen_px(self.track, car.d,car.s)
        car.x = round(smp["x"] + smp["nx"] * lat_px, 2)
        car.y = round(smp["y"] + smp["ny"] * lat_px, 2)

        curr_tick = getattr(self, "tick_count", 0)
        heading_stepped = (getattr(car, "_heading_tick", -1) == curr_tick)
        if not heading_stepped:
            car._heading_tick = curr_tick
            tx, ty = smp["tx"], smp["ty"]
            half_usable = self.track.width_px_at(car.s) * 0.39
            v_forward_px = max(6.0, car.v * self.track.px_per_m)
            v_lateral_px = (car.target_d - car.d) * 2.4 * half_usable * 0.18
            drift_angle = max(-0.065, min(0.065, math.atan2(v_lateral_px, v_forward_px)))
            track_heading = math.atan2(ty, tx)
            yaw_attitude = getattr(car, "steer_angle", 0.0) * 0.20
            target_heading = (track_heading + drift_angle + yaw_attitude + math.pi) % (2.0 * math.pi) - math.pi

            prev_h = getattr(car, "heading", None)
            cur_dt = getattr(self, "_current_dt", 0.05)
            if prev_h is not None and getattr(car, "_has_initial_heading", False):
                dh = (target_heading - prev_h + math.pi) % (2.0 * math.pi) - math.pi
                max_dh = 4.8 * cur_dt
                dh_clamped = max(-max_dh, min(max_dh, dh))
                car.heading = round((prev_h + dh_clamped + math.pi) % (2.0 * math.pi) - math.pi, 4)
            else:
                car.heading = round(target_heading, 4)
                car._has_initial_heading = True

    def _compute_flying_lap(self, car: CarState, fallback_penalty: float = 0.0) -> float:
        u = car.upgrades
        sk = car.skills
        track_evo = -0.15 * self.stage_idx
        comp_delta = 0.42 if car.compound == "MEDIUM" else 0.0
        base_lap = (self.track.length_m / 62.5) * (1.0 + self.wetness * 0.14) + track_evo + comp_delta
        perf_delta = (
            (5.8 - (u["power_unit"] * 0.28 + u["active_aero"] * 0.28 + u["chassis"] * 0.24 + u["suspension"] * 0.20)) * 0.44
            + (90.0 - sk["pace"]) * 0.042
            + (90.0 - sk["wet_skill"]) * (0.045 if self.wetness > 0.15 else 0.0)
            + random.gauss(fallback_penalty, 0.145 * (1.15 - sk["consistency"] / 200.0))
        )
        return round(max(62.0, base_lap + perf_delta), 3)

    def step(self, dt: float, event_cb) -> None:
        if self.finished:
            return
        self.tick_count += 1
        self._current_dt = dt
        self.elapsed += dt
        self.stage_elapsed += dt

        if self.wetness > 0.02 or random.random() < self.track.rain_chance * 0.008:
            self.wetness = max(0.0, min(1.0, self.wetness + random.uniform(-0.003, 0.003) * dt))

        L = self.track.length_m
        for car in self.cars:
            if car.eliminated:
                continue

            if car.quali_sector_plan is None:
                car.quali_sector_plan = self._plan_sector_times(self._compute_flying_lap(car))
            prev_dist = car.total_dist
            smp = self.track.sample(car.s)
            st = smp["station"]
            u = car.upgrades
            sk = car.skills

            car_grip = (
                1.0
                + (u["active_aero"] - 5) * 0.011
                + (u["chassis"] - 5) * 0.009
                + (u["suspension"] - 5) * 0.008
                + (sk["pace"] - 88) * 0.0038
            )
            if self.wetness > 0.12:
                car_grip += (sk["wet_skill"] - 88) * 0.0042 - self.wetness * 0.09

            ice_mult = float(self.regulations.get("ice_power_mult", 1.0))
            target_v = self.v_env[st] * math.sqrt(max(0.65, car_grip))
            if self.regulations.get("has_classic_drs"):
                if smp["straight_mode"] and self.wetness < 0.30 and not self.is_braking[st]:
                    car.aero_mode = "DRS"
                    car.drs_active = True
                    pu_bonus = 1.0 + (u["power_unit"] - 5) * 0.009
                    target_v = min(99.5 * pu_bonus * ice_mult, target_v * 1.07)
                else:
                    car.aero_mode = "CORNER"
                    car.drs_active = False
            elif smp["straight_mode"] and self.wetness < 0.30 and not self.is_braking[st]:
                car.aero_mode = "STRAIGHT"
                car.drs_active = False
                pu_bonus = 1.0 + (u["power_unit"] - 5) * 0.009
                target_v = min(96.5 * pu_bonus, target_v * 1.05)
            else:
                car.aero_mode = "CORNER"
                car.drs_active = False

            if car.v < target_v:
                acc = 13.5 * ice_mult * (1.0 + (u["power_unit"] - 5) * 0.018) * max(0.28, 1.0 - (max(0.0, car.v) / 104.0) ** 1.8)
                car.v = min(target_v, car.v + acc * dt)
                car.braking = False
            else:
                car.v = max(target_v, car.v - 42.0 * dt)
                car.braking = car.v - target_v > 3.5

            ds = car.v * dt * 1.42
            car.total_dist += ds
            car.s = car.total_dist % L
            car.target_d = smp.get("racing_line_d", 0.0) + car.driver_line_bias
            car.d += (car.target_d - car.d) * min(1.0, dt * 3.2)

            # Vehicle dynamics in qualifying session
            a_lat = (car.v * car.v) * smp["curv"]
            car.g_lat = round((a_lat / GRAVITY) * smp["inside_sign"], 2)
            car.body_slip_angle = 0.0
            ackerman_steer = math.atan(3.6 * smp["curv"] * smp["inside_sign"])
            car.steer_angle = round(max(-0.35, min(0.35, ackerman_steer + (car.target_d - car.d) * 0.12)), 4)
            # Battery state in qualifying session (cycles between 50% and 95% of max era capacity, never exceeding 100%)
            charge_ratio = 0.50 + 0.45 * (0.5 + 0.5 * math.sin(self.elapsed * 0.4 + car.number))
            car.battery_mj = max(0.0, min(car.max_battery_mj, round(car.max_battery_mj * charge_ratio, 3)))

            new_laps = int(car.total_dist // L)
            for sector_idx in range(2):
                gate = (car.laps_completed + (sector_idx + 1) / 3) * L
                if prev_dist < gate <= car.total_dist:
                    car.record_sector(sector_idx, car.quali_sector_plan[sector_idx])
            if new_laps > car.laps_completed:
                car.laps_completed = new_laps
                if self.stage_elapsed > 2.5:
                    # Cars start distributed around the circuit on flying laps;
                    # fill any unseen opening splits from that lap's model.
                    for sector_idx, seconds in enumerate(car.quali_sector_plan):
                        car.record_sector(sector_idx, seconds)
                    lap_t = round(sum(car.quali_sector_plan), 3)
                    car.complete_sector_lap()
                    car.last_lap_time = lap_t
                    if car.best_lap_time is None or lap_t < car.best_lap_time:
                        car.best_lap_time = lap_t
                        if self.fastest_time is None or lap_t < self.fastest_time:
                            self.fastest_time = lap_t
                            self.fastest_driver_id = car.driver_id
                            event_cb(
                                "PURPLE",
                                f"{self.stage_name} PURPLE: {car.code} ({car.team_short}) goes P1 with {_fmt_lap(lap_t)}!",
                            )
                car.quali_sector_plan = None
                car.current_sector_times = [None, None, None]

        enforce_2d_car_separation(self.track, self.cars, True, self._update_xy)

        if self.stage_elapsed >= self.stage_duration:
            self._complete_current_stage(event_cb)
            return

        self._resort()

    def _plan_sector_times(self, lap_time: float) -> list[float]:
        first = round(lap_time * self.sector_fractions[0], 3)
        second = round(lap_time * self.sector_fractions[1], 3)
        return [first, second, round(lap_time - first - second, 3)]

    def _complete_current_stage(self, event_cb) -> None:
        for car in self.cars:
            if not car.eliminated and car.best_lap_time is None:
                lap_t = self._compute_flying_lap(car, fallback_penalty=0.06)
                car.best_lap_time = lap_t
                car.last_lap_time = lap_t
                for sector_idx, seconds in enumerate(self._plan_sector_times(lap_t)):
                    car.record_sector(sector_idx, seconds)
                car.complete_sector_lap()
                if self.fastest_time is None or lap_t < self.fastest_time:
                    self.fastest_time = lap_t
                    self.fastest_driver_id = car.driver_id

        self._resort()
        st_name = self.stage_name
        cut = self.cut_line

        if cut > 0:
            eliminated_codes = []
            for idx, car in enumerate(self.standings):
                pos = idx + 1
                if not car.eliminated and pos > cut:
                    car.eliminated = True
                    car.elim_stage = st_name
                    car.locked_grid_pos = pos
                    car.in_pits = True
                    car.pit_phase = "STOPPED"
                    car.pit_apron = 1.0
                    car.v = 0.0
                    car.aero_mode = "CORNER"
                    car.d = 2.0 * self.track.pit_side
                    car.total_dist = self.track.pit_garages[TEAM_GARAGE_INDEX.get(car.team_id,5)]['s_m']
                    car.s = car.total_dist
                    self._update_xy(car)
                    eliminated_codes.append(f"P{pos} {car.code}")

            event_cb(
                "RACE_CONTROL",
                f"{st_name} CHEQUERED FLAG â€” ELIMINATED: {', '.join(eliminated_codes)}.",
            )

            self.stage_idx += 1
            self.stage_elapsed = 0.0
            self.fastest_time = None
            self.fastest_driver_id = None
            next_comp = self._stage_compound()
            advancing = [c for c in self.standings if not c.eliminated]
            n_adv = max(len(advancing), 1)
            for idx, car in enumerate(advancing):
                car.best_lap_time = None
                car.last_lap_time = None
                car.current_sector_times = [None, None, None]
                car.last_sector_times = [None, None, None]
                car.best_sector_times = [None, None, None]
                car.quali_sector_plan = None
                car.gap_to_leader = 0.0
                car.interval_ahead = 0.0
                car.compound = next_comp
                car.tire_wear = 0.01
                car.d = 0.0
                car.target_d = 0.0
                car.total_dist = ((0.06 + 0.90 * (idx / n_adv)) % 1.0) * self.track.length_m
                car.s = car.total_dist
                car.laps_completed = int(car.total_dist // self.track.length_m)
                car.v = 68.0
                self._update_xy(car)

            enforce_2d_car_separation(self.track, self.cars, True, self._update_xy)
            self._resort()
            event_cb(
                "RACE_CONTROL",
                f"{self.stage_name} GREEN LIGHT: Top {len(advancing)} cars head out on {next_comp} tyres!",
            )
        else:
            for idx, car in enumerate(self.standings):
                if not car.eliminated:
                    car.locked_grid_pos = idx + 1
            self._resort()
            self.finished = True
            pole = self.standings[0]
            p2 = self.standings[1]
            gap = round((p2.best_lap_time or 0) - (pole.best_lap_time or 0), 3)
            label = "SPRINT POLE" if self.is_sprint_quali else "POLE POSITION"
            event_cb(
                "POLE",
                f"{label}: #{pole.number} {pole.name} ({pole.team_short}) tops {st_name} by +{gap:.3f}s over {p2.code}!",
            )

    def advance_stage(self, event_cb) -> None:
        """Fast-forward the current knockout stage (Q1, Q2, or Q3) to completion."""
        target_stage = self.stage_idx
        guard = 0
        while not self.finished and self.stage_idx == target_stage and guard < 600:
            self.step(1.0, event_cb)
            guard += 1

    def _resort(self) -> None:
        active = [c for c in self.cars if not c.eliminated]
        eliminated = [c for c in self.cars if c.eliminated]
        active.sort(key=lambda c: (c.best_lap_time is None, c.best_lap_time or 9999.0, -c.skills["pace"]))
        eliminated.sort(key=lambda c: (c.locked_grid_pos or 99))

        leader_t = active[0].best_lap_time if active else None
        for idx, c in enumerate(active):
            c.pos = idx + 1
            if leader_t is not None and c.best_lap_time is not None:
                c.gap_to_leader = round(c.best_lap_time - leader_t, 3)
                prev_t = active[idx - 1].best_lap_time if idx > 0 else leader_t
                c.interval_ahead = round(c.best_lap_time - (prev_t or leader_t), 3)
            else:
                c.gap_to_leader = 0.0
                c.interval_ahead = 0.0

        for c in eliminated:
            c.pos = c.locked_grid_pos or c.pos

        self.standings = active + eliminated


class RaceSession:
    """Full 2D Grand Prix & Sprint Simulation with Zero-Overlap Multi-Lane Racing, Maneuvers & Pit Variance."""

    def __init__(
        self,
        track: CompiledTrack,
        teams_by_id: dict[str, dict],
        grid_drivers: list[dict],
        wetness: float,
        rain_forecast: float,
        player_team_id: str,
        is_sprint: bool = False,
        regulations: dict | None = None,
        starting_compounds: dict[str, str] | None = None,
    ):
        self.track = track
        self.is_sprint = is_sprint
        self.regulations = regulations or {
            "era_id": "2026_HYBRID",
            "ice_power_mult": 1.0,
            "max_battery_mj": 4.0,
            "ers_drain_rate": 0.28,
            "ers_harvest_rate": 0.42,
            "has_active_aero": True,
            "has_classic_drs": False,
            "drs_boost_kmh": 0.0,
        }
        self.starting_compounds = dict(starting_compounds or {})
        self.v_env, self.is_braking = build_speed_envelope(track)
        self.total_laps: int = max(6, track.sprint_laps) if (is_sprint and track.sprint_laps > 0) else track.race_laps
        self.race_clock: float = 0.0
        self.tick_count: int = 0
        self._current_dt: float = 0.05
        self.lights_countdown: float = 5.5
        self.lights_out: bool = False
        self.finished: bool = False
        self.post_finish_timer: float = 0.0

        self.wetness: float = wetness
        self.rain_intensity: float = wetness * 0.85 if wetness > 0.12 else 0.0
        self.rain_forecast: float = rain_forecast
        self.track_temp_c: float = round(track.base_temp_c + (8.0 if wetness < 0.1 else -4.0), 1)
        self.weather_timer: float = random.uniform(165.0, 290.0)

        self.flag_state: str = "LIGHTS"
        self.yellow_sector: int | None = None
        self.yellow_timer: float = 0.0
        self.vsc_timer: float = 0.0
        self.sc_laps_remaining: int = 0
        self.sc_in_this_lap: bool = False
        self.sc_s: float = 0.0
        self.sc_x: float = 0.0
        self.sc_y: float = 0.0
        self.sc_heading: float = 0.0
        self.restart_no_overtake_lap: int = 1

        self.fastest_lap_time: float | None = None
        self.fastest_lap_driver_id: str | None = None
        self.fastest_lap_code: str = ""

        self.stewards_queue: list[dict[str, Any]] = []
        self.radio_dispatcher = RadioDispatcher()

        self.cars: list[CarState] = []
        for idx, drv in enumerate(grid_drivers):
            team = teams_by_id[drv["team_id"]]
            grid_pos = idx + 1
            if drv["id"] in self.starting_compounds:
                comp = self.starting_compounds[drv["id"]]
            elif wetness > 0.55:
                comp = "WET"
            elif wetness > 0.16:
                comp = "INTER"
            elif is_sprint:
                comp = random.choice(["MEDIUM", "MEDIUM", "SOFT"]) if grid_pos <= 12 else random.choice(["MEDIUM", "SOFT"])
            else:
                if grid_pos <= 6:
                    comp = random.choice(["MEDIUM", "MEDIUM", "SOFT"])
                elif grid_pos <= 14:
                    comp = random.choice(["MEDIUM", "HARD", "SOFT"])
                else:
                    comp = random.choice(["HARD", "MEDIUM"])

            max_bat = float(self.regulations.get("max_battery_mj", 4.0))
            car = CarState(drv, team, grid_pos, comp, self.total_laps, max_battery_mj=max_bat)
            car.max_battery_mj = float(self.regulations.get("max_battery_mj", 4.0))
            car.battery_mj = car.max_battery_mj
            gb = track.grid_boxes[idx]
            car.total_dist = gb['progress_m']
            car.s = gb['s_m']
            car.d = gb['d']
            car.lap = 1
            car.laps_completed = 0
            car.crossed_start_line = car.total_dist >= 0
            car.grid_start_d = car.d
            car.target_d = car.d
            self._update_xy(car)
            self.cars.append(car)

        self.standings: list[CarState] = list(self.cars)
        self.cars_by_id: dict[str, CarState] = {c.driver_id: c for c in self.cars}
        self.wet_declared: bool = wetness > 0.15

    def set_starting_compound(self, driver_id: str, compound: str) -> bool:
        if compound in TIRE_COMPOUNDS and driver_id in self.cars_by_id:
            car = self.cars_by_id[driver_id]
            car.compound = compound
            car.next_compound = compound
            car.compounds_used = {compound}
            car.tire_age_laps = 0
            car.tire_wear = 0.01
            self.starting_compounds[driver_id] = compound
            return True
        return False

    def _team_pit_box_s(self, car: CarState) -> float:
        t_idx = TEAM_GARAGE_INDEX.get(car.team_id, 5)
        return self.track.pit_garages[t_idx]['s_m']

    def _update_xy(self, car: CarState) -> None:
        if car.in_pits:
            psmp = self.track.sample_pit(car.s)
            res_x = res_y = 0.0
            apron_px = pit_lateral_offset(self.track,car.s,car.pit_apron)
            nx_p, ny_p = -psmp["ty"], psmp["tx"]
            car.x = round(psmp["x"] + res_x + nx_p * apron_px, 2)
            car.y = round(psmp["y"] + res_y + ny_p * apron_px, 2)
            car.heading = round(math.atan2(psmp["ty"], psmp["tx"]), 4)
            return

        smp = self.track.sample(car.s)
        lat_px = compute_lateral_screen_px(self.track, car.d,car.s)
        car.x = round(smp["x"] + smp["nx"] * lat_px, 2)
        car.y = round(smp["y"] + smp["ny"] * lat_px, 2)

        if car.spin_timer > 0.0:
            omega = getattr(car, "spin_omega", 5.8)
            car.heading = round((math.atan2(smp["ty"], smp["tx"]) + car.spin_timer * omega) % (2.0 * math.pi) - math.pi, 4)
            return

        # Heading is integrated at most once per 50ms simulation tick to prevent multi-pass SAT multiplier artifacts
        curr_tick = getattr(self, "tick_count", 0)
        heading_stepped = (getattr(car, "_heading_tick", -1) == curr_tick)
        if not heading_stepped:
            car._heading_tick = curr_tick
            tx, ty = smp["tx"], smp["ty"]
            half_usable = self.track.width_px_at(car.s) * 0.39
            v_forward_px = max(6.0, car.v * self.track.px_per_m)
            steer_rate = 2.8 if (car.maneuver_pass_timer > 0.0 or car.maneuver_timer > 0.0) else 2.2
            v_lateral_px = (car.target_d - car.d) * steer_rate * half_usable * 0.18

            drift_angle = max(-0.065, min(0.065, math.atan2(v_lateral_px, v_forward_px)))
            track_heading = math.atan2(ty, tx)

            # Dynamic chassis yaw in corners: car nose turns naturally into apex
            yaw_attitude = getattr(car, "steer_angle", 0.0) * 0.20
            target_heading = (track_heading + drift_angle + yaw_attitude + math.pi) % (2.0 * math.pi) - math.pi

            prev_h = getattr(car, "heading", None)
            cur_dt = getattr(self, "_current_dt", 0.05)
            if prev_h is not None and getattr(car, "_has_initial_heading", False):
                dh = (target_heading - prev_h + math.pi) % (2.0 * math.pi) - math.pi
                max_dh = 4.8 * cur_dt
                dh_clamped = max(-max_dh, min(max_dh, dh))
                car.heading = round((prev_h + dh_clamped + math.pi) % (2.0 * math.pi) - math.pi, 4)
            else:
                car.heading = round(target_heading, 4)
                car._has_initial_heading = True

    def _update_sc_xy(self, sc_d: float = 0.0) -> None:
        smp = self.track.sample(self.sc_s)
        lat_px = compute_lateral_screen_px(self.track, sc_d,self.sc_s)
        self.sc_x = round(smp["x"] + smp["nx"] * lat_px, 2)
        self.sc_y = round(smp["y"] + smp["ny"] * lat_px, 2)
        self.sc_heading = round(math.atan2(smp["ty"], smp["tx"]), 4)

    def step(self, dt: float, event_cb) -> None:
        if self.finished:
            return
        self.tick_count += 1
        self._current_dt = dt

        if not self.lights_out:
            self.lights_countdown -= dt
            if self.lights_countdown <= 0.0:
                self.lights_out = True
                self.flag_state = "GREEN"
                for c in self.cars:
                    c.lap_start_time = 0.0
                    launch = 7.5 + (c.skills["racecraft"] - 80) * 0.14 + (c.car_perf_index - 80.0) * 0.09 + random.uniform(-1.1, 1.1)
                    c.v = 0.6
                    c.accel = launch * 1.5
                race_label = "SPRINT" if self.is_sprint else "GRAND PRIX"
                event_cb("RACE_CONTROL", f"LIGHTS OUT AND AWAY WE GO! {race_label} underway â€” 22 cars charge into Turn 1!")
            return

        self.race_clock += dt

        self._step_weather(dt, event_cb)
        self._step_race_control(dt, event_cb)
        self._step_stewards(dt, event_cb)
        self.radio_dispatcher.step(dt, self.race_clock, self.cars, self.track, self.wetness, self.flag_state, event_cb)

        leader = self.standings[0] if self.standings else None
        leader_finished = leader.finished if leader else False

        for idx, car in enumerate(self.standings):
            if car.dnf:
                if car.dnf_timer > 0:
                    car.dnf_timer = max(0.0, car.dnf_timer - dt)
                continue
            if car.finished:
                car.v = max(18.0, car.v - 14.0 * dt)
                ds_cool = car.v * dt
                car.total_dist += ds_cool
                car.s = car.total_dist % self.track.length_m
                car.d += (car.target_d - car.d) * min(1.0, dt * 4.5)
                continue

            car_ahead = self.standings[idx - 1] if idx > 0 and not self.standings[idx - 1].dnf else None
            self._step_car(car, car_ahead, leader, leader_finished, dt, event_cb)

        self._resolve_battles_and_incidents(dt, event_cb)
        if self.flag_state == "SC":
            min_sc_m = (CAR_LEN_PX * 1.38) / self.track.px_per_m
            L = self.track.length_m
            unlapping_near = False
            for c in self.cars:
                if c.dnf or c.in_pits or c.spin_timer > 0.0:
                    continue
                signed_sc = (self.sc_s - c.s + 0.5 * L) % L - 0.5 * L
                if abs(signed_sc) < min_sc_m:
                    if c.pos == 1:
                        shift = (min_sc_m - signed_sc) + 0.45
                        c.total_dist -= shift
                        c.s = c.total_dist % L
                        c.v = min(c.v, 46.5)
                    else:
                        unlapping_near = True
                        c.target_d = -0.84 * self.track.pit_side
                        c.d = -0.84 * self.track.pit_side
            self._update_sc_xy(0.46 * self.track.pit_side if unlapping_near else 0.0)
        allow_passing = self.flag_state not in ("VSC", "SC", "LIGHTS")
        def _col_cb(c1: CarState, c2: CarState, sat: tuple[float, float, float, float]) -> None:
            self._on_physical_contact(c1, c2, sat, event_cb)
        enforce_2d_car_separation(self.track, self.cars, allow_passing, self._update_xy, collision_cb=_col_cb)
        if self.flag_state == "SC":
            min_sc_m = (CAR_LEN_PX * 1.45) / self.track.px_per_m
            L = self.track.length_m
            any_unlap = False
            for c in self.cars:
                if c.dnf or c.in_pits or c.spin_timer > 0.0:
                    continue
                signed_sc = (self.sc_s - c.s + 0.5 * L) % L - 0.5 * L
                if abs(signed_sc) < min_sc_m and c.pos != 1:
                    any_unlap = True
                    c.d = -0.84 * self.track.pit_side
                    self._update_xy(c)
            if any_unlap:
                # Re-resolve so cars shifted into the unlapping lane never stack on each other
                enforce_2d_car_separation(self.track, self.cars, False, self._update_xy)
            sc_lane = 0.48 * self.track.pit_side if any_unlap else 0.0
            self._update_sc_xy(sc_lane)
            # Ensure Safety Car never clips P1 or any car across sharp chicane chords
            for _ in range(6):
                sc_close = False
                sc_body=SimpleNamespace(x=self.sc_x,y=self.sc_y,heading=self.sc_heading)
                for c in self.cars:
                    if c.dnf or c.in_pits:
                        continue
                    if _sat_obb_penetration(c,sc_body,other_half_l=SC_HALF_LENGTH,other_half_w=SC_HALF_WIDTH) is not None:
                        if self.track.has_overpass and min((c.s - self.sc_s) % L, (self.sc_s - c.s) % L) > 250.0:
                            continue
                        sc_close = True
                        break
                if not sc_close:
                    break
                # Never wrap across the line here; lap counting happens in _step_race_control
                self.sc_s = min(self.sc_s + 8.0, L - 0.05)
                self._update_sc_xy(sc_lane)
        self._update_standings(dt, event_cb)

    def _step_weather(self, dt: float, event_cb) -> None:
        self.weather_timer -= dt
        if self.weather_timer <= 0.0:
            self.weather_timer = random.uniform(165.0, 290.0)
            roll = random.random()
            prev_rain = self.rain_intensity
            forecast = self.rain_forecast[0] if isinstance(self.rain_forecast, list) else self.rain_forecast
            if roll < forecast:
                self.rain_intensity = min(1.0, self.rain_intensity + random.uniform(0.25, 0.55))
                if prev_rain < 0.10 and self.rain_intensity >= 0.18:
                    event_cb("WEATHER", "WEATHER RADAR: Rain front arriving over the circuit! Surface grip dropping.")
                    self.radio_dispatcher.trigger_weather_transition(
                        self.rain_intensity, self.wetness, event_cb, self.race_clock, self.standings, self.track
                    )
            else:
                self.rain_intensity = max(0.0, self.rain_intensity - random.uniform(0.25, 0.50))
                if prev_rain >= 0.18 and self.rain_intensity < 0.06:
                    event_cb("WEATHER", "WEATHER UPDATE: Rain shower passing. A dry racing line is emerging!")

        if self.rain_intensity > self.wetness:
            self.wetness = min(1.0, self.wetness + (self.rain_intensity - self.wetness) * 0.022 * dt)
        else:
            dry_rate = 0.0055 * (1.0 + (self.track_temp_c - 18.0) * 0.03)
            self.wetness = max(0.0, self.wetness - dry_rate * dt)

        if self.wetness > 0.15 and not self.wet_declared:
            self.wet_declared = True
            if not self.is_sprint:
                event_cb("RACE_CONTROL", "RACE CONTROL: Wet track declared. Mandatory 2-dry-compound rule waived.")

    def _step_race_control(self, dt: float, event_cb) -> None:
        if self.flag_state == "YELLOW":
            self.yellow_timer -= dt
            if self.yellow_timer <= 0.0:
                self.flag_state = "GREEN"
                self.yellow_sector = None
                event_cb("RACE_CONTROL", "GREEN FLAG: Track clear in all sectors.")

        elif self.flag_state == "VSC":
            self.vsc_timer -= dt
            if self.vsc_timer <= 0.0:
                self.flag_state = "GREEN"
                event_cb("RACE_CONTROL", "VSC ENDING -> GREEN FLAG! Racing resumes immediately!")

        elif self.flag_state == "SC":
            prev_sc_s = self.sc_s
            self.sc_s = (self.sc_s + 47.0 * dt) % self.track.length_m
            self._update_sc_xy()
            if self.sc_s < prev_sc_s:
                self.sc_laps_remaining -= 1
                if self.sc_laps_remaining == 1 and not self.sc_in_this_lap:
                    self.sc_in_this_lap = True
                    event_cb("RACE_CONTROL", "SAFETY CAR IN THIS LAP! Leader controls the pace to the Line.")
                    self.radio_dispatcher.trigger_safety_car_in(event_cb, self.race_clock, self.standings)
                elif self.sc_laps_remaining <= 0:
                    self.flag_state = "GREEN"
                    self.sc_in_this_lap = False
                    leader = next((c for c in self.standings if not c.dnf), None)
                    if leader:
                        self.restart_no_overtake_lap = leader.lap
                    for c in self.cars:
                        c.overtake_eligible = False
                        c.overtake_active = False
                    event_cb("RACE_CONTROL", "GREEN FLAG! Safety Car peels into the pits â€” full-throttle restart!")

    def _step_stewards(self, dt: float, event_cb) -> None:
        remaining = []
        for item in self.stewards_queue:
            item["timer"] -= dt
            if item["stage"] == "NOTED" and item["timer"] <= 3.5:
                item["stage"] = "INVESTIGATING"
                event_cb("STEWARDS", f"FIA STEWARDS: Turn {item['turn']} incident ({item['summary']}) â€” UNDER INVESTIGATION.")
            if item["timer"] <= 0.0:
                self._apply_stewards_verdict(item, event_cb)
            else:
                remaining.append(item)
        self.stewards_queue = remaining

    def _apply_stewards_verdict(self, item: dict, event_cb) -> None:
        culprit: CarState | None = self.cars_by_id.get(item["culprit_id"])
        if not culprit or culprit.dnf:
            event_cb("STEWARDS", f"FIA STEWARDS: Turn {item['turn']} incident ({item['summary']}) â€” No Further Action.")
            return

        verdict = item["verdict"]
        turn = item["turn"]
        if verdict == "NFA":
            event_cb("STEWARDS", f"FIA STEWARDS: Turn {turn} ({item['summary']}) â€” Racing Incident, No Further Action.")
        elif verdict == "5S":
            culprit.time_penalty_s += 5
            culprit.penalty_points_season += 1
            culprit.penalty_points_added += 1
            event_cb(
                "PENALTY",
                f"PENALTY: +5s Time Penalty for #{culprit.number} {culprit.code} ({item['reason']} at Turn {turn}).",
            )
        elif verdict == "10S":
            culprit.time_penalty_s += 10
            culprit.penalty_points_season += 2
            culprit.penalty_points_added += 2
            event_cb(
                "PENALTY",
                f"PENALTY: +10s Time Penalty for #{culprit.number} {culprit.code} ({item['reason']} at Turn {turn}) + 2 Penalty Pts!",
            )
        elif verdict == "DT":
            culprit.drive_through_pending = True
            culprit.drive_through_laps_left = 3
            culprit.penalty_points_season += 3
            culprit.penalty_points_added += 3
            event_cb(
                "PENALTY",
                f"SEVERE PENALTY: Drive-Through Penalty for #{culprit.number} {culprit.code} ({item['reason']} at Turn {turn})!",
            )

    def trigger_safety_car(self, mode: str, reason: str, event_cb) -> None:
        if self.flag_state in ("SC", "CHEQUERED"):
            return
        leader = next((c for c in self.standings if not c.dnf), None)
        if not leader or leader.lap >= self.total_laps - 1:
            self.flag_state = "YELLOW"
            self.yellow_sector = 1
            self.yellow_timer = 9.0
            return

        if mode == "VSC" and self.flag_state != "SC":
            self.flag_state = "VSC"
            self.vsc_timer = random.uniform(16.0, 25.0)
            self.yellow_sector = None
            event_cb("SC", f"VIRTUAL SAFETY CAR DEPLOYED: {reason}. Maintain VSC delta!")
            self.radio_dispatcher.trigger_safety_car("VSC", reason, event_cb, self.race_clock, self.standings)
        else:
            self.flag_state = "SC"
            self.sc_laps_remaining = 2
            self.sc_in_this_lap = False
            self.sc_s = (leader.s + 140.0) % self.track.length_m
            self._update_sc_xy()
            self.yellow_sector = None
            event_cb("SC", f"SAFETY CAR DEPLOYED: {reason}! Pack bunching up behind the Safety Car.")
            self.radio_dispatcher.trigger_safety_car("SC", reason, event_cb, self.race_clock, self.standings)

    def _evaluate_auto_strategy(self, car: CarState, laps_left: int) -> None:
        if car.in_pits or car.box_this_lap:
            return
        if car.drive_through_pending and car.drive_through_laps_left <= 2:
            car.box_this_lap = True
            return

        if not car.auto_strategy:
            return

        is_slick = car.compound in ("SOFT", "MEDIUM", "HARD")

        # Sprint format has no mandatory pit stops; stay out unless extreme weather change or severe structural damage
        if self.is_sprint:
            if self.wetness > 0.60 and car.compound != "WET" and laps_left >= 2:
                car.box_this_lap = True
                car.next_compound = "WET"
                return
            if 0.23 <= self.wetness <= 0.56 and is_slick and laps_left >= 2:
                car.box_this_lap = True
                car.next_compound = "INTER"
                return
            if self.wetness < 0.09 and not is_slick and car.tire_age_laps >= 2 and laps_left >= 2:
                car.box_this_lap = True
                car.next_compound = "SOFT"
                return
            if car.wing_damage >= 0.68 and laps_left >= 3:
                car.box_this_lap = True
                car.next_compound = self._best_compound_for_conditions(car, laps_left)
                return
            return

        if car.wing_damage >= 0.28 and laps_left >= 2:
            car.box_this_lap = True
            car.next_compound = self._best_compound_for_conditions(car, laps_left)
            return

        if car.tire_age_laps >= 2 or car.lap >= 2:
            if self.wetness > 0.60 and car.compound != "WET" and laps_left >= 2:
                car.box_this_lap = True
                car.next_compound = "WET"
                return
            if 0.23 <= self.wetness <= 0.56 and is_slick and laps_left >= 2:
                car.box_this_lap = True
                car.next_compound = "INTER"
                return
            if self.wetness < 0.09 and not is_slick and car.tire_age_laps >= 2 and laps_left >= 2:
                car.box_this_lap = True
                car.next_compound = "SOFT" if laps_left <= 8 else "MEDIUM"
                return

        need_second_dry = (
            (not self.is_sprint)
            and (not self.wet_declared)
            and len(car.compounds_used & {"SOFT", "MEDIUM", "HARD"}) < 2
        )
        if self.flag_state in ("VSC", "SC") and laps_left >= 4 and car.tire_age_laps >= 5 and not self.is_sprint:
            if car.tire_wear > 0.48 or (need_second_dry and car.lap >= max(6, int(self.total_laps * 0.34))):
                car.box_this_lap = True
                car.next_compound = self._best_compound_for_conditions(car, laps_left)
                return

        if car.tire_wear >= TIRE_COMPOUNDS[car.compound]["cliff_wear"] - 0.04 and laps_left >= 2:
            car.box_this_lap = True
            car.next_compound = self._best_compound_for_conditions(car, laps_left)
            return

        if need_second_dry and (car.lap >= car.planned_pit_lap or laps_left <= 2) and laps_left >= 1:
            car.box_this_lap = True
            car.next_compound = self._best_compound_for_conditions(car, laps_left)

    def _best_compound_for_conditions(self, car: CarState, laps_left: int) -> str:
        if self.wetness > 0.55:
            return "WET"
        if self.wetness > 0.17:
            return "INTER"
        used_dry = car.compounds_used & {"SOFT", "MEDIUM", "HARD"}
        if laps_left <= 7:
            pref = ["SOFT", "MEDIUM", "HARD"]
        elif laps_left <= 13:
            pref = ["MEDIUM", "HARD", "SOFT"]
        else:
            pref = ["HARD", "MEDIUM", "SOFT"]

        if not self.is_sprint and len(used_dry) == 1:
            for c in pref:
                if c not in used_dry:
                    return c
        return pref[0]

    def _advance_car_progress(self, car: CarState, ds: float, leader_finished: bool, event_cb) -> None:
        """Advance car total_dist & s monotonically, triggering Start/Finish lap events cleanly."""
        L = self.track.length_m
        prev_dist = car.total_dist
        car.total_dist += ds
        car.s = car.total_dist % L

        if not car.crossed_start_line and car.total_dist >= 0.0:
            car.crossed_start_line = True

        while ds > 0 and not car.finished:
            sector_idx = next(i for i, value in enumerate(car.current_sector_times) if value is None)
            gate = (car.laps_completed + (sector_idx + 1) / 3) * L
            if car.total_dist < gate:
                break
            # Interpolate within the physics tick, including pit-lane progress.
            fraction = max(0.0, min(1.0, (gate - prev_dist) / ds))
            crossing_time = round(self.race_clock - self._current_dt * (1.0 - fraction), 3)
            car.record_sector(sector_idx, crossing_time - car.sector_start_time)
            car.sector_start_time = crossing_time
            if sector_idx < 2:
                continue

            car.laps_completed += 1
            lap_time = round(crossing_time - car.lap_start_time, 3)
            car.complete_sector_lap()
            if lap_time > 35.0:
                car.last_lap_time = lap_time
                if car.best_lap_time is None or lap_time < car.best_lap_time:
                    car.best_lap_time = lap_time
                if self.fastest_lap_time is None or lap_time < self.fastest_lap_time:
                    self.fastest_lap_time = lap_time
                    self.fastest_lap_driver_id = car.driver_id
                    self.fastest_lap_code = car.code
                    if car.laps_completed >= 2:
                        event_cb("PURPLE", f"FASTEST LAP: {car.code} ({car.team_short}) clocks {_fmt_lap(lap_time)}!")
                        self.radio_dispatcher.trigger_fastest_lap(car, _fmt_lap(lap_time), event_cb)

            car.lap_start_time = crossing_time
            car.tire_age_laps += 1

            if car.drive_through_pending:
                car.drive_through_laps_left -= 1
                if car.drive_through_laps_left < 0:
                    car.drive_through_pending = False
                    car.time_penalty_s += 25
                    event_cb("PENALTY", f"PENALTY: #{car.number} {car.code} failed to serve Drive-Through (+25s added)!")

            if car.laps_completed >= self.total_laps or leader_finished:
                car.finished = True
                if (
                    not self.is_sprint
                    and not self.wet_declared
                    and len(car.compounds_used & {"SOFT", "MEDIUM", "HARD"}) < 2
                ):
                    car.time_penalty_s += 30
                    event_cb(
                        "PENALTY",
                        f"FIA STEWARDS: #{car.number} {car.code} penalised +30s for failing to use 2 dry tyre compounds!",
                    )
                car.finish_time = round(self.race_clock + car.time_penalty_s, 3)
                if self.flag_state != "CHEQUERED":
                    self.flag_state = "CHEQUERED"
                    race_lbl = "SPRINT" if self.is_sprint else "GRAND PRIX"
                    event_cb(
                        "CHEQUERED",
                        f"CHEQUERED FLAG ({race_lbl})! #{car.number} {car.name} ({car.team_short}) crosses the line P1!",
                    )
            else:
                car.lap = car.laps_completed + 1

    def _step_car(
        self,
        car: CarState,
        car_ahead: CarState | None,
        leader: CarState | None,
        leader_finished: bool,
        dt: float,
        event_cb,
    ) -> None:
        car.overtake_cooldown = max(0.0, car.overtake_cooldown - dt)
        car.contact_cooldown = max(0.0, car.contact_cooldown - dt)
        car.maneuver_attempt_cooldown = max(0.0, car.maneuver_attempt_cooldown - dt)
        if car.maneuver_pass_timer > 0.0:
            car.maneuver_pass_timer = max(0.0, car.maneuver_pass_timer - dt)
            if car.maneuver_pass_timer <= 0.0:
                car.maneuver_target_id = None
        if car.maneuver_timer > 0.0:
            car.maneuver_timer = max(0.0, car.maneuver_timer - dt)
            if car.maneuver_timer <= 0.0:
                car.maneuver = ""
        car.smoke = max(0.0, car.smoke - dt * 1.6)
        car.sparks = False

        if car.spin_timer > 0.0:
            car.spin_timer = max(0.0, car.spin_timer - dt)
            car.v = max(0.0, car.v - 22.0 * dt)
            s_dir = getattr(car, "spin_lateral_dir", 1.0 if car.d >= 0.0 else -1.0)
            car.d = max(-1.42, min(1.42, car.d + s_dir * 1.85 * dt))
            if abs(car.d) >= 1.35 and not getattr(car, "spin_rebound_done", False):
                car.spin_rebound_done = True
                car.spin_lateral_dir = -s_dir * 0.25
                car.sparks = True
            car.smoke = max(car.smoke, 2.5)
            ds = car.v * dt * 0.35
            self._advance_car_progress(car, ds, leader_finished, event_cb)
            return

        if car.in_pits:
            self._step_pit_lane(car, leader_finished, dt, event_cb)
            return

        laps_left = max(0, self.total_laps - car.lap)
        self._evaluate_auto_strategy(car, laps_left)

        smp = self.track.sample(car.s)
        st = smp["station"]
        sector = smp["sector"]
        u = car.upgrades
        sk = car.skills
        comp_spec = TIRE_COMPOUNDS[car.compound]

        prev_s = car.s
        if car.box_this_lap and not car.radio_box_announced and laps_left >= 1:
            car.radio_box_announced = True
            self.radio_dispatcher.trigger_box_call(car, event_cb)
            if not getattr(car, "inlap_push_announced", False):
                car.inlap_push_announced = True
                car.pace_mode = "ATTACK"
                turn = self.track.nearest_corner(car.s) if hasattr(self.track, "nearest_corner") else 1
                self.radio_dispatcher.trigger_push_mode(
                    car, "IN-LAP ATTACK", is_pit_wall=True, event_cb=event_cb, clock=self.race_clock, turn=turn
                )

        entry_gap=(self.track.pit_entry_s-prev_s)%self.track.length_m
        if car.box_this_lap and entry_gap <= car.v*dt:
            self._advance_car_progress(car,entry_gap,leader_finished,event_cb)
            car.in_pits = True
            car.pit_phase = "ENTRY"
            car.pit_entry_d = car.d
            car.pit_apron = 0.0
            car.pit_speed_checked = False
            car.box_this_lap = False
            car.overtake_active = False
            car.aero_mode = "CORNER"
            remaining=dt-entry_gap/max(car.v,1e-9)
            if remaining>0:self._step_pit_lane(car,leader_finished,remaining,event_cb)
            return

        wear = car.tire_wear
        cliff = comp_spec["cliff_wear"]
        if wear >= cliff and not getattr(car, "cliff_radio_triggered", False) and laps_left >= 2:
            car.cliff_radio_triggered = True
            self.radio_dispatcher.trigger_tyre_cliff(car, event_cb, self.race_clock)

        if wear <= cliff:
            wear_factor = 1.0 - wear * 0.11
        else:
            wear_factor = (1.0 - cliff * 0.11) - (wear - cliff) * 0.85

        w_min = comp_spec["optimal_wet_min"]
        w_max = comp_spec["optimal_wet_max"]
        if w_min <= self.wetness <= w_max:
            weather_grip = 1.0 - self.wetness * 0.08
        elif self.wetness > w_max:
            excess = self.wetness - w_max
            weather_grip = max(0.52, 1.0 - excess * 0.72)
        else:
            deficit = w_min - self.wetness
            weather_grip = max(0.76, 1.0 - deficit * 0.42)

        is_slick = car.compound in ("SOFT", "MEDIUM", "HARD")
        warmup_factor = 1.025 if (car.tire_age_laps == 0 and car.pit_stops > 0 and is_slick and self.wetness < 0.15) else 1.0
        pace_grip_mod = {"CONSERVE": 0.982, "BALANCED": 1.000, "PUSH": 1.014, "ATTACK": 1.024}.get(car.pace_mode, 1.0)
        pace_wear_mod = {"CONSERVE": 0.76, "BALANCED": 1.00, "PUSH": 1.24, "ATTACK": 1.48}.get(car.pace_mode, 1.0)

        slipstream_bonus = 0.0
        dirty_air_loss = 0.0
        gap_ahead_s = 99.0
        if car_ahead and not car_ahead.in_pits:
            dist_ahead = (car_ahead.s - car.s) % self.track.length_m
            if 2.0 < dist_ahead < 95.0:
                gap_ahead_s = dist_ahead / max(car.v, 25.0)
                # FIA DRS detection proximity (within 1.0s window)
                if gap_ahead_s < 1.0:
                    car.tailing_timer = min(15.0, car.tailing_timer + dt)
                else:
                    car.tailing_timer = max(0.0, car.tailing_timer - dt * 0.4)

                # Tow Balance: Only occurs if RIGHT BEHIND the car ahead on a straight
                # - Tight proximity: <= 20m and <= 0.28s gap
                # - Lateral wake alignment: lateral offset <= 0.16 (drops to zero if pulled out)
                # - Track condition: straight line / flat-out only (curv < 0.0038 and not in braking zone)
                # - Subtle authentic speed bonus: max 0.8% (~0.7-0.8 m/s or ~2.6 km/h)
                if (
                    3.0 <= dist_ahead <= 20.0
                    and gap_ahead_s <= 0.28
                    and smp["curv"] < 0.0038
                    and not self.is_braking[st]
                ):
                    lat_offset = abs(car.d - car_ahead.d)
                    if lat_offset <= 0.16:
                        align_factor = 1.0 - (lat_offset / 0.16) ** 1.5
                        prox_factor = 1.0 - (gap_ahead_s / 0.28)
                        slipstream_bonus = prox_factor * align_factor * 0.008

                # Dirty air downforce deficit in cornering wake
                if gap_ahead_s < 0.85 and smp["curv"] > 0.0065:
                    dirty_air_loss = (1.0 - gap_ahead_s / 0.85) * 0.032
        else:
            car.tailing_timer = max(0.0, car.tailing_timer - dt * 0.4)

        # AI dynamic push / attack / conserve mode switching based on proximity and tyres
        if car.auto_strategy and self.flag_state == "GREEN" and not car.box_this_lap:
            if car.pace_mode == "BALANCED" and 0.25 < gap_ahead_s < 1.05 and car.tire_wear < 0.45:
                if random.random() < 0.04 * dt:
                    car.pace_mode = "PUSH"
                    turn = self.track.nearest_corner(car.s) if hasattr(self.track, "nearest_corner") else 1
                    self.radio_dispatcher.trigger_push_mode(
                        car, "PUSH", is_pit_wall=False, event_cb=event_cb, clock=self.race_clock, turn=turn
                    )
            elif car.pace_mode in ("PUSH", "ATTACK") and (car.tire_wear > 0.65 or gap_ahead_s > 2.2):
                if car.tire_wear > 0.68:
                    car.pace_mode = "CONSERVE"
                    turn = self.track.nearest_corner(car.s) if hasattr(self.track, "nearest_corner") else 1
                    self.radio_dispatcher.trigger_conserve_mode(
                        car, event_cb=event_cb, clock=self.race_clock, turn=turn
                    )
                else:
                    car.pace_mode = "BALANCED"

        fw_grip_factor = 1.0 - car.wing_damage * (0.28 if smp["curv"] > 0.005 else 0.12)
        grip_mult = (
            comp_spec["base_grip"]
            * wear_factor
            * weather_grip
            * warmup_factor
            * pace_grip_mod
            * (1.0 - dirty_air_loss)
            * fw_grip_factor
            * (1.0 + (u["active_aero"] - 5) * 0.0036 + (u["chassis"] - 5) * 0.0030 + (u["suspension"] - 5) * 0.0026)
            * (1.0 + (sk["pace"] - 88) * 0.0008 + (sk["wet_skill"] - 88) * (0.0035 if self.wetness > 0.15 else 0.0))
            * (1.0 + (22.0 - car.fuel_kg) * 0.0007)
        )
        grip_mult = max(0.45, grip_mult)
        car.grip_snapshot = grip_mult

        in_yellow = (self.flag_state == "YELLOW" and self.yellow_sector == sector)
        has_active_aero = self.regulations.get("has_active_aero", True)
        has_classic_drs = self.regulations.get("has_classic_drs", False)
        ice_power_mult = float(self.regulations.get("ice_power_mult", 1.0))
        is_v8_era = (self.regulations.get("era_id") == "V8_DRS")

        # Check DRS active for classic DRS era
        car.drs_active = False
        drs_zones = getattr(self.track, "drs_zones", None)
        if has_classic_drs and car.drs_eligible and car.drs_eligible_zone is not None and drs_zones:
            active_z = next((z for z in drs_zones if z["id"] == car.drs_eligible_zone), None)
            if active_z:
                act_s = active_z["activation_s_m"]
                end_s = active_z["end_s_m"]
                z_len = (end_s - act_s) % self.track.length_m
                cur_off = (car.s - act_s) % self.track.length_m
                if cur_off <= z_len and not car.braking and not self.is_braking[st] and self.flag_state == "GREEN" and not in_yellow and self.wetness < 0.20:
                    car.drs_active = True

        # Aero mode determination
        if has_active_aero:
            if (
                smp["straight_mode"]
                and self.wetness < 0.35
                and not self.is_braking[st]
                and self.flag_state == "GREEN"
                and not in_yellow
            ):
                car.aero_mode = "STRAIGHT"
            else:
                car.aero_mode = "CORNER"
        elif has_classic_drs and car.drs_active:
            car.aero_mode = "DRS"
        else:
            car.aero_mode = "CORNER"

        target_v = self.v_env[st] * math.sqrt(grip_mult)

        car.overtake_active = False
        car.boost_active = False
        car.recharging = False

        if self.flag_state == "GREEN" and not in_yellow:
            if self.is_braking[st]:
                base_harvest = 0.22 if is_v8_era else 0.35
                harvest = base_harvest * dt * (1.0 + (u["power_unit"] - 5) * 0.03)
                car.battery_mj = max(0.0, min(car.max_battery_mj, car.battery_mj + harvest))
                car.recharging = True
            elif car.aero_mode in ("STRAIGHT", "DRS") or smp["curv"] < 0.0065:
                threshold_low = 0.15 if is_v8_era else 0.20
                threshold_bst = 0.25 if is_v8_era else 0.35
                want_overtake = (
                    car.overtake_eligible
                    and car.battery_mj > threshold_low
                    and car.ers_mode != "HARVEST"
                    and (gap_ahead_s < 1.35 or car.ers_mode in ("OVERTAKE", "BOOST"))
                )
                want_boost = (
                    not want_overtake
                    and car.battery_mj > threshold_bst
                    and (
                        car.ers_mode == "BOOST"
                        or (car.ers_mode == "AUTO" and (gap_ahead_s < 0.85 or car.pace_mode in ("PUSH", "ATTACK")))
                    )
                )
                if want_overtake:
                    car.overtake_active = True
                    drain_rate = 0.45 if is_v8_era else 0.85
                    drain = drain_rate * dt * (1.0 - (u["power_unit"] - 5) * 0.025)
                    car.battery_mj = max(0.0, car.battery_mj - drain)
                elif want_boost:
                    car.boost_active = True
                    drain_rate = 0.35 if is_v8_era else 0.55
                    drain = drain_rate * dt
                    car.battery_mj = max(0.0, car.battery_mj - drain)
                elif car.ers_mode != "HARVEST" and car.battery_mj > 0.30:
                    drain_rate = 0.15 if is_v8_era else 0.28
                    drain = drain_rate * dt
                    car.battery_mj = max(0.0, car.battery_mj - drain)
                elif car.ers_mode == "HARVEST" or car.battery_mj <= threshold_low:
                    car.recharging = True
                    car.battery_mj = max(0.0, min(car.max_battery_mj, car.battery_mj + (0.08 if is_v8_era else 0.12) * dt))
            else:
                if car.v < target_v and car.ers_mode != "HARVEST" and car.battery_mj > 0.25:
                    corner_drain = (0.12 if is_v8_era else 0.22) * dt
                    car.battery_mj = max(0.0, car.battery_mj - corner_drain)

        target_v = self.v_env[st] * math.sqrt(grip_mult)
        if has_active_aero and car.aero_mode == "STRAIGHT":
            pu_top = 1.0 + (u["power_unit"] - 5) * 0.0024 + (u["active_aero"] - 5) * 0.0018
            if car.overtake_active:
                top_cap = min(OVERTAKE_MAX_MS, 98.6 * pu_top * (1.0 + slipstream_bonus))
                target_v = max(target_v, top_cap)
            else:
                boost_add = 2.1 if car.boost_active else (0.0 if not car.recharging else -2.6)
                top_cap = (91.2 * pu_top + boost_add) * (1.0 + slipstream_bonus)
                target_v = min(max(target_v, 82.0), top_cap)
        elif has_classic_drs and car.drs_active:
            # Classic DRS open: +22 km/h drag reduction boost!
            pu_top = 1.0 + (u["power_unit"] - 5) * 0.0024
            drs_bonus_ms = 22.0 / 3.6  # +22 km/h (~6.11 m/s)
            top_cap = (93.5 * pu_top * ice_power_mult + drs_bonus_ms) * (1.0 + slipstream_bonus)
            target_v = max(target_v, min(OVERTAKE_MAX_MS, top_cap))
        elif has_classic_drs and smp["curv"] < 0.0065 and not self.is_braking[st]:
            # V8 NA Straight Top Speed without DRS
            pu_top = 1.0 + (u["power_unit"] - 5) * 0.0024
            boost_add = 1.6 if car.boost_active else 0.0
            top_cap = (90.2 * pu_top * ice_power_mult + boost_add) * (1.0 + slipstream_bonus)
            target_v = min(max(target_v, 82.0), top_cap)
        else:
            if car.overtake_active:
                target_v *= 1.052
            elif car.boost_active:
                target_v *= 1.020

        # Team Order: YIELD / SWAP Position to Teammate
        if car.team_order == "YIELD":
            teammate = next(
                (c for c in self.cars if c.team_id == car.team_id and c.driver_id != car.driver_id and not c.dnf),
                None,
            )
            if teammate:
                # Check if teammate has successfully passed (is now ahead in total_dist)
                if teammate.total_dist > car.total_dist:
                    car.team_order = "FREE"
                    car.swap_target_id = None
                    teammate.swap_pass_id = None
                    turn = self.track.nearest_corner(car.s) if hasattr(self.track, "nearest_corner") else 1
                    event_cb(
                        "TEAM_ORDER",
                        f"TEAM ORDERS EXECUTED ({car.team_short}): #{car.number} {car.code} lets #{teammate.number} {teammate.code} through near Turn {turn}!",
                    )
                    event_cb(
                        "RADIO",
                        f"PIT WALL ({car.team_short}): 'Swap completed. Great teamwork #{car.code}. Now #{teammate.code}, push hard!'",
                    )
                else:
                    dist_tm = (car.s - teammate.s) % self.track.length_m
                    if 0.0 < dist_tm < 95.0:
                        # Move yielding car cleanly off the racing line to allow pass
                        side = 1.0 if teammate.d <= 0.0 else -1.0
                        car.target_d = max(-0.84, min(0.84, side * 0.78))
                        # Lift throttle so trailing teammate carries decisive passing momentum
                        target_v = min(target_v, max(36.0, teammate.v * 0.82))

        if in_yellow:
            target_v = min(target_v, 56.0)
        elif self.flag_state == "VSC":
            target_v = min(target_v, 52.0)
        elif self.flag_state == "SC":
            dist_to_sc = (self.sc_s - car.s) % self.track.length_m
            if car.pos == 1 and dist_to_sc < 120.0:
                target_v = min(target_v, 47.0 + (dist_to_sc - 26.0) * 0.25)
            elif car_ahead and gap_ahead_s < 1.1:
                target_v = min(target_v, car_ahead.v + (gap_ahead_s - 0.65) * 14.0)
            else:
                target_v = min(target_v, 66.0)
        elif self.flag_state == "GREEN" and car_ahead and not car_ahead.in_pits:
            half_u = self.track.width_px_at(car.s) * 0.39
            min_d_w = CAR_WID_PX / half_u
            lane_offset = abs(car.d - car_ahead.d)
            # Continuous lateral overlap factor tapering smoothly (zero discrete flicker)
            lateral_overlap = max(0.0, min(1.0, (min_d_w * 1.20 - lane_offset) / max(0.01, min_d_w * 0.45)))
            dist_ahead_m = (car_ahead.s - car.s) % self.track.length_m
            min_long_car = CAR_LEN_PX / self.track.px_per_m
            is_alongside = dist_ahead_m < min_long_car * 0.95 and lane_offset >= min_d_w * 0.75
            in_active_pass = (
                car.maneuver_pass_timer > 0.0
                or getattr(car_ahead, "maneuver_pass_timer", 0.0) > 0.0
                or car.battle_with == car_ahead.driver_id
                or is_alongside
                or (car.team_id == car_ahead.team_id and getattr(car_ahead, "team_order", "") == "YIELD")
            )
            if not in_active_pass and dist_ahead_m < 110.0 and lateral_overlap > 0.001:
                st_ahead = self.track.sample(car_ahead.s)["station"]
                is_ahead_braking = self.is_braking[st_ahead]
                brake_dist_req = max(0.0, car.v * car.v - car_ahead.v * car_ahead.v) / 85.0
                if is_ahead_braking and dist_ahead_m < brake_dist_req + 28.0:
                    margin = (brake_dist_req + 28.0) - dist_ahead_m
                    brake_blend = min(1.0, margin / 16.0) * lateral_overlap
                    approach_v = (1.0 - brake_blend) * target_v + brake_blend * car_ahead.v
                    target_v = min(target_v, approach_v)
                elif gap_ahead_s < 0.92:
                    gap_blend = max(0.0, min(1.0, (0.92 - gap_ahead_s) / 0.60))
                    blend = gap_blend * lateral_overlap
                    desired_gap = 0.35
                    follow_v = car_ahead.v + (gap_ahead_s - desired_gap) * 12.0
                    target_follow = max(4.0, follow_v)
                    target_v = min(target_v, (1.0 - blend) * target_v + blend * target_follow)

        # Blue Flag AI: lapped cars yield off-line and lift throttle
        car.blue_flag_timer = max(0.0, car.blue_flag_timer - dt)
        is_lapped = (leader is not None and leader.lap > car.lap and not car.in_pits)
        if is_lapped:
            closing_lead_car = None
            for lead_car in self.standings:
                if lead_car.lap > car.lap and not lead_car.in_pits and not lead_car.dnf:
                    dist_behind = (car.s - lead_car.s) % self.track.length_m
                    if 0.0 < dist_behind < 55.0:
                        closing_lead_car = lead_car
                        break
            if closing_lead_car is not None:
                car.blue_flag = True
                target_v *= 0.88
                if car.blue_flag_timer <= 0.0:
                    car.blue_flag_timer = 9.0
                    event_cb(
                        "BLUE_FLAG",
                        f"BLUE FLAGS: #{car.number} {car.code} ({car.team_short}) yields off-line to let #{closing_lead_car.number} {closing_lead_car.code} through!",
                    )
            else:
                car.blue_flag = False
        else:
            car.blue_flag = False

        # FIA Rule 33.4 Defense cooldown & reset (Car is permitted at most ONE defensive move)
        if car.defense_timer > 0.0:
            car.defense_timer = max(0.0, car.defense_timer - dt)
            if car.defense_timer <= 0.0 and car.battle_with is None:
                car.defense_moves = 0
                car.defending_side = 0.0

        if car.v < target_v:
            pu_acc = 13.8 * ice_power_mult * (1.0 + (u["power_unit"] - 5) * 0.022) * (1.0 - car.wing_damage * 0.08)
            if car.drs_active:
                pu_acc *= 1.28
            elif car.overtake_active:
                pu_acc *= 1.52
            elif car.boost_active:
                pu_acc *= 1.15
            elif car.v > DERATE_START_MS:
                derate_frac = min(1.0, (car.v - DERATE_START_MS) / (DERATE_END_MS - DERATE_START_MS))
                pu_acc *= max(0.28, 1.0 - 0.65 * derate_frac)

            drag_fade = max(0.18, 1.0 - (max(0.0, car.v) / 104.0) ** 1.85)
            v_deficit = target_v - car.v
            max_acc = pu_acc * drag_fade
            in_braking_or_apex = (smp["curv"] > 0.003 or self.is_braking[st])
            if in_braking_or_apex and v_deficit <= 1.5:
                # Progressive throttle roll-on in braking/corner zones: prevents full-power ping-pong
                car.accel = min(max_acc, max(2.0, v_deficit / max(dt, 0.001)))
            else:
                car.accel = max_acc
            car.v = min(target_v, car.v + car.accel * dt)
            car.braking = False
            if car.v > 84.0 and car.aero_mode == "STRAIGHT" and random.random() < 0.14:
                car.sparks = True
            elif car.wing_damage > 0.35 and car.v > 58.0 and random.random() < 0.30:
                car.sparks = True
        else:
            v_diff = car.v - target_v
            max_brake = 42.0 * (0.85 + 0.15 * grip_mult)
            if v_diff <= 1.5:
                # Smooth throttle lift & aerodynamic coasting (zero slamming!)
                brake_decel = min(10.0, v_diff / max(dt, 0.001))
            elif v_diff < 7.0:
                # Progressive brake pedal modulation ramping smoothly from coasting to heavy braking
                blend = (v_diff - 1.5) / 5.5
                brake_decel = 10.0 + blend * (max_brake - 10.0)
            else:
                # Full threshold braking in deep corner braking zones
                brake_decel = max_brake
            car.accel = -brake_decel
            car.braking = v_diff > 4.5
            car.v = max(target_v, car.v - brake_decel * dt)

        ds = car.v * dt
        new_s = prev_s + ds

        # Multi-DRS Zones Detection & Activation
        drs_zones = getattr(self.track, "drs_zones", None)
        ds_step = max(ds, 0.1)
        if drs_zones:
            for zone in drs_zones:
                det_s = zone["detection_s_m"]
                act_s = zone["activation_s_m"]
                end_s = zone["end_s_m"]
                z_id = zone["id"]

                # Detection Point Crossing
                if (det_s - prev_s) % self.track.length_m <= ds_step:
                    if (
                        self.flag_state == "GREEN"
                        and car.lap >= 2
                        and car.lap > self.restart_no_overtake_lap
                        and self.wetness < 0.20
                        and car_ahead is not None
                        and not car_ahead.in_pits
                    ):
                        dist_det = (car_ahead.s - det_s) % self.track.length_m
                        time_gap = dist_det / max(car.v, 28.0)
                        if 0.001 < time_gap <= 1.000:
                            car.overtake_eligible = True
                            car.drs_eligible = True
                            car.drs_eligible_zone = z_id
                        else:
                            if car.drs_eligible_zone == z_id:
                                car.drs_eligible = False
                                car.drs_eligible_zone = None
                            car.overtake_eligible = False
                    else:
                        if car.drs_eligible_zone == z_id:
                            car.drs_eligible = False
                            car.drs_eligible_zone = None
                        car.overtake_eligible = False

                # End of DRS Zone Crossing (braking point)
                if (end_s - prev_s) % self.track.length_m <= ds_step:
                    car.overtake_eligible = False
                    if car.drs_eligible_zone == z_id:
                        car.drs_eligible = False
                        car.drs_eligible_zone = None
                        car.drs_active = False

        else:
            det_s = self.track.detection_s_m
            if prev_s < det_s <= new_s:
                if (
                    self.flag_state == "GREEN"
                    and car.lap >= 2
                    and car.lap > self.restart_no_overtake_lap
                    and self.wetness < 0.20
                    and car_ahead is not None
                    and not car_ahead.in_pits
                ):
                    dist_det = (car_ahead.s - det_s) % self.track.length_m
                    time_gap = dist_det / max(car.v, 28.0)
                    if 0.001 < time_gap <= 1.000:
                        car.overtake_eligible = True
                        car.drs_eligible = True
                    else:
                        car.overtake_eligible = False
                        car.drs_eligible = False
                else:
                    car.overtake_eligible = False
                    car.drs_eligible = False

        if car.pit_blend_active:
            # Exiting car stays bounded inside pit exit blend lane past Turn 1/2
            car.target_d = 0.76 * self.track.pit_side
            if (car.s-self.track.pit_exit_s)%self.track.length_m >= 110:
                car.pit_blend_active = False
        elif car.blue_flag:
            car.target_d = 0.82 * self.track.pit_side
        elif car.defense_moves > 0 or car.defense_timer > 0.0:
            # Defending car: STRICT ONE-MOVE RULE (cars must NOT move more than once)
            car.target_d = car.defending_side
        elif car.battle_with is None and car.maneuver_timer <= 0.0 and car.maneuver_pass_timer <= 0.0:
            base_line_d = smp.get("racing_line_d", 0.0) + car.driver_line_bias
            # Front wing damage induces push/understeer: car washes wide in turns
            if car.wing_damage > 0.15 and smp["curv"] > 0.005:
                understeer_wash = car.wing_damage * 0.36 * (-smp["inside_sign"])
                if car.wing_damage_side == "BOTH" or (car.wing_damage_side == "RIGHT" and smp["inside_sign"] == -1) or (car.wing_damage_side == "LEFT" and smp["inside_sign"] == 1):
                    base_line_d += understeer_wash

            # Disciplined race start: hold starting grid lane down the main straight until approaching Turn 1
            t1_s = self.track.corners[0]["s_m"] if self.track.corners else 320.0
            if car.lap == 1 and car.total_dist < t1_s * 0.72:
                car.target_d = car.grid_start_d
            elif car.lap == 1 and car.total_dist < t1_s:
                blend = min(1.0, max(0.0, (car.total_dist - t1_s * 0.72) / max(t1_s * 0.28, 1.0)))
                car.target_d = (1.0 - blend) * car.grid_start_d + blend * max(-0.88, min(0.88, base_line_d))
            else:
                car.target_d = max(-0.88, min(0.88, base_line_d))

        steer_rate = 2.6 if (car.maneuver_pass_timer > 0.0 or car.maneuver_timer > 0.0) else 2.0
        max_d_step = 1.6 * dt
        step_d = (car.target_d - car.d) * min(1.0, dt * steer_rate)
        car.d += max(-max_d_step, min(max_d_step, step_d))

        # 2D Vehicle Dynamics: lateral G, front wheel steer angle with realistic hairpin steering lock
        a_lat = (car.v * car.v) * smp["curv"]
        car.g_lat = round((a_lat / GRAVITY) * smp["inside_sign"], 2)
        car.body_slip_angle = 0.0
        wheelbase_m = 3.6
        ackerman_steer = math.atan(wheelbase_m * 1.65 * smp["curv"] * smp["inside_sign"])
        lane_steer = (car.target_d - car.d) * 0.20
        car.steer_angle = round(max(-0.42, min(0.42, ackerman_steer + lane_steer)), 4)

        km_step = ds / 1000.0
        wear_rate = (
            comp_spec["wear_per_km"]
            * self.track.tire_abrasion
            * pace_wear_mod
            * (1.0 - (sk["tire_mgmt"] - 85) * 0.012)
            * (1.0 - (u["chassis"] - 5) * 0.018)
            * (1.28 if dirty_air_loss > 0.015 else 1.0)
            * (1.65 if (self.wetness < 0.08 and car.compound in ("INTER", "WET")) else 1.0)
        )
        car.tire_wear = min(0.99, car.tire_wear + km_step * max(0.002, wear_rate))
        target_temp = 96.0 + (12.0 if car.pace_mode in ("PUSH", "ATTACK") else (-6.0 if car.pace_mode == "CONSERVE" else 0.0))
        if dirty_air_loss > 0.01:
            target_temp += 6.0
        car.tire_temp += (target_temp - car.tire_temp) * min(1.0, dt * 0.35)
        car.fuel_kg = max(0.1, car.fuel_kg - km_step * 0.31)

        self._check_solo_incidents(car, smp, dt, event_cb)
        if car.dnf:
            return

        self._advance_car_progress(car, ds, leader_finished, event_cb)

    def _roll_pit_stop_duration(self, car: CarState, event_cb) -> tuple[float, str]:
        """Realistic F1 pit stop distribution: faster mean for top crews, right-tail slow/botched stops."""
        crew_lvl = car.upgrades["pit_crew"]
        tier_shift = (car.car_perf_index - 80.0) * 0.012
        mean_clean = 2.90 - crew_lvl * 0.098 - tier_shift

        roll = random.random()
        botch_prob = max(0.008, 0.036 - crew_lvl * 0.0028)
        slow_prob = max(0.035, 0.125 - crew_lvl * 0.0095)
        hesitation_prob = max(0.080, 0.190 - crew_lvl * 0.011)

        if roll < botch_prob:
            dur = round(mean_clean + random.uniform(4.8, 9.2), 2)
            issue = random.choice(["Cross-threaded wheel nut", "Front jack release failure", "Sticky rear-left wheel gun"])
            event_cb(
                "PIT",
                f"BOTCHED PIT STOP! {issue} holds #{car.number} {car.code} ({car.team_short}) stationary for {dur:.1f}s!",
            )
            return dur, "BOTCHED"
        if roll < botch_prob + slow_prob:
            dur = round(mean_clean + random.uniform(1.65, 3.85), 2)
            event_cb(
                "PIT",
                f"SLOW PIT STOP: Sticky wheel gun delays #{car.number} {car.code} ({car.team_short}) ({dur:.1f}s stop).",
            )
            return dur, "SLOW"
        if roll < botch_prob + slow_prob + hesitation_prob:
            dur = round(mean_clean + random.uniform(0.45, 1.25), 2)
            return dur, "HESITATION"

        dur = round(max(1.80, random.gauss(mean_clean, 0.14)), 2)
        if dur <= 2.02:
            event_cb(
                "PURPLE",
                f"LIGHTNING PIT STOP: {car.team_short} crew nails a {dur:.2f}s stop for #{car.number} {car.code}!",
            )
        return dur, "CLEAN"

    def _step_pit_lane(self, car: CarState, leader_finished: bool, dt: float, event_cb) -> None:
        pit_d = 2.0 * self.track.pit_side
        car.d += (pit_d - car.d) * min(1.0, dt * 5.5)
        car.braking = False
        car.aero_mode = "CORNER"
        car.overtake_active = False
        team_box_s = self._team_pit_box_s(car)
        min_pit_long_m = (CAR_LEN_PX * 1.10) / self.track.pit_px_per_m

        if car.pit_phase == "ENTRY":
            car.pit_apron = max(0.0, car.pit_apron - dt * 6.0)
            car.v = max(PIT_SPEED_LIMIT_MS, car.v - 35.0 * dt)
            prev_s = car.s
            ds = car.v * dt * self.track.pit_distance_scale
            L = self.track.length_m
            span = self.track.pit_span_m

            # Pit-lane local coordinate (0 at pit entry line, span at pit exit); robust across the S/F line
            rel = (prev_s - self.track.pit_entry_s) % L
            if rel > L - 150.0:
                rel -= L
            rel_box = (team_box_s - self.track.pit_entry_s) % L

            if not car.pit_speed_checked and rel >= 0.0:
                car.pit_speed_checked = True
                if random.random() < 0.038 * (1.20 - car.skills["consistency"] / 100.0):
                    car.time_penalty_s += 5
                    event_cb("PENALTY", f"FIA STEWARDS: +5s Penalty for #{car.number} {car.code} â€” Speeding in the Pit Lane (Pit Entry)!")

            # Double-stack check: if teammate is currently STOPPED in the team's garage box, hold right behind!
            teammate_stopped = any(
                o.driver_id != car.driver_id and o.team_id == car.team_id and o.in_pits and o.pit_phase == "STOPPED"
                for o in self.cars
            )
            wait_rel = rel_box - min_pit_long_m
            if teammate_stopped and rel + ds >= wait_rel and rel <= rel_box:
                clamp_ds = max(0.0, wait_rel - rel)
                if clamp_ds > 0.0:
                    self._advance_car_progress(car, clamp_ds, leader_finished, event_cb)
                car.v = 0.0
                return

            if rel + ds >= rel_box or rel > span:
                delta_to_box = rel_box - rel
                self._advance_car_progress(car, delta_to_box, leader_finished, event_cb)
                car.v = 0.0
                if car.drive_through_pending:
                    car.drive_through_pending = False
                    car.pit_phase = "EXIT"
                    event_cb("STEWARDS", f"PIT LANE: #{car.number} {car.code} serves Drive-Through Penalty.")
                else:
                    car.pit_phase = "STOPPED"
                    car.pit_apron = 1.0
                    base_stop, _stop_quality = self._roll_pit_stop_duration(car, event_cb)

                    penalty_wait = min(10.0, float(car.time_penalty_s))
                    if car.time_penalty_s > 0:
                        car.served_penalties_s += int(penalty_wait)
                        event_cb("STEWARDS", f"PIT BOX: #{car.number} {car.code} serving +{int(penalty_wait)}s penalty before tyre change.")
                        car.time_penalty_s = max(0, car.time_penalty_s - int(penalty_wait))

                    wing_wait = 7.4 if car.wing_damage >= 0.20 else 0.0
                    if wing_wait > 0:
                        old_side = car.wing_damage_side
                        car.wing_damage = 0.0
                        car.wing_damage_side = "NONE"
                        event_cb("PIT", f"PIT CREW: Replacing damaged front wing assembly ({old_side}) on #{car.number} {car.code} (+{wing_wait:.1f}s).")

                    car.pit_stop_timer = round(base_stop + penalty_wait + wing_wait, 2)
                    car.last_pit_duration = car.pit_stop_timer
            else:
                self._advance_car_progress(car, ds, leader_finished, event_cb)

        elif car.pit_phase == "STOPPED":
            car.v = 0.0
            car.pit_apron = 1.0
            car.pit_stop_timer -= dt
            if car.pit_stop_timer <= 0.0:
                # FIA Pit-Release Check: hold momentarily in garage box if a moving car is right alongside in the Fast Lane
                L = self.track.length_m
                fast_lane_busy = any(
                    o.driver_id != car.driver_id
                    and o.in_pits
                    and not o.dnf
                    and o.pit_phase != "STOPPED"
                    and o.v > 1.0
                    and min((o.s - car.s) % L, (car.s - o.s) % L) < min_pit_long_m * 1.12
                    for o in self.cars
                )
                if fast_lane_busy:
                    return

                car.compound = car.next_compound
                car.compounds_used.add(car.compound)
                car.tire_wear = 0.0
                car.tire_age_laps = 0
                car.tire_temp = 86.0
                car.pit_stops += 1
                car.pit_phase = "EXIT"
                car.v = PIT_SPEED_LIMIT_MS
                car.pit_apron = 0.0
                car.next_compound = "MEDIUM" if car.compound != "MEDIUM" else "HARD"
                event_cb(
                    "PIT",
                    f"PIT OUT: #{car.number} {car.code} ({car.team_short}) rejoins on {car.compound} ({car.last_pit_duration:.2f}s stationary).",
                )
                car.radio_box_announced = False
                car.cliff_radio_triggered = False
                car.inlap_push_announced = False
                self.radio_dispatcher.trigger_pit_exit(car, car.last_pit_duration, event_cb)
                other_in_pit = any(
                    o.in_pits and o.driver_id != car.driver_id and abs(o.s - car.s) < 38.0 for o in self.cars
                )
                if other_in_pit and random.random() < 0.14:
                    self.stewards_queue.append(
                        {
                            "timer": 6.5,
                            "stage": "NOTED",
                            "turn": 1,
                            "culprit_id": car.driver_id,
                            "summary": f"#{car.number} {car.code} close pit release",
                            "reason": "Unsafe Release in Pit Lane",
                            "verdict": random.choice(["NFA", "5S"]),
                        }
                    )

        elif car.pit_phase == "EXIT":
            car.pit_apron = max(0.0, car.pit_apron - dt * 6.0)
            car.v = PIT_SPEED_LIMIT_MS
            L_ex = self.track.length_m
            rel_ex = (car.s - self.track.pit_entry_s) % L_ex
            ds = car.v*dt*self.track.pit_distance_scale
            remaining=max(0,self.track.pit_span_m-rel_ex)
            travelled=min(ds,remaining)
            self._advance_car_progress(car,travelled,leader_finished,event_cb)
            if ds>=remaining:
                car.in_pits = False
                car.pit_phase = "NONE"
                car.pit_speed_checked = False
                car.pit_apron = 0.0
                car.pit_blend_active = True
                car.d = 0.76 * self.track.pit_side
                car.target_d = 0.76 * self.track.pit_side
                leftover=max(0,dt-travelled/(car.v*self.track.pit_distance_scale))
                if leftover:self._advance_car_progress(car,car.v*leftover,leader_finished,event_cb)

    def _check_solo_incidents(self, car: CarState, smp: dict, dt: float, event_cb) -> None:
        if self.flag_state != "GREEN":
            return

        sk = car.skills
        u = car.upgrades
        push_mult = {"CONSERVE": 0.45, "BALANCED": 1.0, "PUSH": 1.85, "ATTACK": 2.9}.get(car.pace_mode, 1.0)

        if smp["curv"] > 0.011:
            tl_prob = 0.0011 * push_mult * (1.22 - sk["consistency"] / 115.0) * dt
            if random.random() < tl_prob:
                car.track_limits_strikes += 1
                turn = self.track.nearest_corner(car.s)
                if car.track_limits_strikes == 3:
                    event_cb(
                        "STEWARDS",
                        f"BLACK & WHITE FLAG: #{car.number} {car.code} shown warning for Track Limits at Turn {turn} (3 strikes).",
                    )
                elif car.track_limits_strikes >= 4:
                    car.track_limits_strikes = 0
                    car.time_penalty_s += 5
                    event_cb(
                        "PENALTY",
                        f"PENALTY: +5s Time Penalty for #{car.number} {car.code} â€” Exceeding Track Limits (4 strikes).",
                    )

        slick_in_rain = self.wetness > 0.25 and car.compound in ("SOFT", "MEDIUM", "HARD")
        # Base crash risk tuned to authentic F1 low attrition (0.000045)
        risk = (
            0.000045
            * push_mult
            * (1.20 - sk["consistency"] / 115.0)
            * (2.8 if slick_in_rain else (1.30 if self.wetness > 0.35 else 1.0))
            * (1.7 if car.tire_wear > 0.76 else 1.0)
            * dt
        )
        if smp["curv"] > 0.012 and random.random() < risk:
            turn = self.track.nearest_corner(car.s)
            # Terminal barrier impact DNF rate: 2.5% permanent circuits, 5.0% street tracks
            if random.random() < (0.05 if self.track.id in ("monaco", "saudi", "azerbaijan", "singapore", "canada") else 0.025):
                car.dnf = True
                car.dnf_reason = f"Crashed at Turn {turn}"
                car.dnf_timer = 35.0
                car.v = 0.0
                car.d = -1.62 * self.track.pit_side
                car.smoke = 4.0
                car.repair_cost_m += round(random.uniform(0.65, 1.75), 2)
                self._update_xy(car)
                event_cb(
                    "CRASH",
                    f"CRASH! #{car.number} {car.name} ({car.team_short}) loses the rear and hits the barrier at Turn {turn}! OUT OF THE RACE!",
                )
                self.trigger_safety_car(
                    "SC" if random.random() < 0.58 else "VSC",
                    f"#{car.number} {car.code} barrier impact at Turn {turn}",
                    event_cb,
                )
                return
            else:
                car.spin_timer = random.uniform(3.2, 5.5)
                car.smoke = 2.8
                car.tire_wear = min(0.98, car.tire_wear + 0.06)
                self.radio_dispatcher.trigger_spin(car, turn, event_cb, self.race_clock)
                if random.random() < 0.20:
                    car.wing_damage = min(0.75, car.wing_damage + random.uniform(0.24, 0.48))
                    car.wing_damage_side = random.choice(["LEFT", "RIGHT"])
                    car.repair_cost_m += 0.28
                    event_cb(
                        "YELLOW",
                        f"YELLOW FLAG SECTOR {smp['sector']}: #{car.number} {car.code} clips barrier at Turn {turn} (Front Wing Damage) and spins!",
                    )
                else:
                    event_cb(
                        "YELLOW",
                        f"YELLOW FLAG SECTOR {smp['sector']}: #{car.number} {car.code} spins off at Turn {turn} and rejoins!",
                    )
                self.flag_state = "YELLOW"
                self.yellow_sector = smp["sector"]
                self.yellow_timer = 7.5
                return

        # Mechanical reliability failure (scaled to authentic modern F1 standards, ~80% reduction)
        rel_lvl = u.get("reliability", 5)
        pace_factor = 0.65 if car.pace_mode == "CONSERVE" else (1.20 if car.pace_mode == "ATTACK" else 1.0)
        # Grace period for early race (clock > 35.0s) and reduced coefficient from 0.00016 to 0.000032
        mech_prob = (
            (0.000018 * max(0.16, 1.30 - rel_lvl * 0.12) * pace_factor * dt)
            if self.race_clock > 45.0
            else 0.0
        )
        if random.random() < mech_prob:
            failure = random.choice(["MGU-K Electrical Failure", "Turbocharger Failure", "Hydraulics Leak", "Gearbox Issue"])
            turn = self.track.nearest_corner(car.s)
            car.dnf = True
            car.dnf_reason = failure
            car.dnf_timer = 30.0
            car.v = 0.0
            car.d = -1.62 * self.track.pit_side
            car.smoke = 3.5
            self._update_xy(car)
            event_cb(
                "RETIREMENT",
                f"MECHANICAL DNF: Smoke from #{car.number} {car.name} ({car.team_short}) near Turn {turn} â€” {failure}!",
            )
            if random.random() < 0.65:
                self.trigger_safety_car("VSC", f"#{car.number} {car.code} stopped trackside ({failure})", event_cb)

    def select_and_evaluate_maneuver(
        self,
        attacker: CarState,
        defender: CarState,
        smp: dict,
        is_braking_zone: bool,
    ) -> tuple[str, float, float]:
        """
        Choose an authentic F1 overtaking maneuver and compute its exact success rate
        scaling with Driver Skill delta AND Car Performance difference (+ tyres, ERS, track width).
        """
        ins = float(smp.get("inside_sign", 1))
        curv = smp["curv"]
        def_covers_inside = (defender.d * ins) > 0.22 or defender.skills["defense"] >= 87

        # Distance to nearest corner and corner characteristics
        dist_to_corner = 9999.0
        nearest_corner_obj = None
        if getattr(self.track, "corners", None):
            s_w = attacker.s % self.track.length_m
            for c in self.track.corners:
                d_c = abs(c["s_m"] - s_w)
                d_c = min(d_c, self.track.length_m - d_c)
                if d_c < dist_to_corner:
                    dist_to_corner = d_c
                    nearest_corner_obj = c

        corner_st = nearest_corner_obj["station"] if nearest_corner_obj else smp.get("station", 0)
        apex_curv = self.track.stations[corner_st]["curv"] if hasattr(self.track, "stations") else curv
        apex_v = self.v_env[corner_st]

        # Balance rule: Divebomb is ONLY permitted in hairpins and corners!
        # Hairpin: tight radius (apex_curv >= 0.012 or apex_v <= 38.0 m/s or curv >= 0.011) and within 70m of apex
        is_hairpin = (apex_curv >= 0.012 or apex_v <= 38.0 or curv >= 0.011) and (dist_to_corner <= 70.0 or curv >= 0.009)
        # Corner: genuine deceleration corner (apex_curv >= 0.0062 and apex_v <= 65.0 m/s) within 55m of apex
        is_corner = (apex_curv >= 0.0062 and apex_v <= 65.0) and (dist_to_corner <= 55.0 or curv >= 0.0065)

        # Lap 1 opening sector: pack is compressed 22-wide; drivers avoid reckless divebombs and hold clean racing line
        t2_s = self.track.corners[1]["s_m"] if len(self.track.corners) > 1 else 600.0
        if attacker.lap == 1 and attacker.total_dist < t2_s:
            maneuver = "SLIPSTREAM"
            target_d = -0.68 * ins if defender.d * ins > 0.0 else 0.68 * ins
            maneuver_base = -0.15
        elif not is_hairpin and not is_corner:
            # NOT in a hairpin or corner: Divebomb is STRICTLY PROHIBITED.
            # Straights, straight approach, kinks, or high-speed sweeps:
            if smp.get("straight_mode", False) or curv < 0.0055:
                maneuver = "SLIPSTREAM"
                target_d = -0.74 * ins
                maneuver_base = 0.06
            else:
                if random.random() < 0.65 or self.track.track_width_m >= 13.5:
                    maneuver = "OUTSIDE"
                    target_d = -0.80 * ins
                    maneuver_base = -0.10 + (self.track.track_width_m - 13.0) * 0.10
                else:
                    maneuver = "DUMMY"
                    target_d = -0.76 * ins if defender.d * ins > 0.05 else 0.76 * ins
                    maneuver_base = 0.06
        elif is_hairpin:
            # Hairpin: Premier territory for divebombing down the inside!
            if def_covers_inside:
                if attacker.skills["racecraft"] >= 88 and random.random() < 0.40:
                    maneuver = "DUMMY"
                    target_d = -0.78 * ins if defender.d * ins > 0.05 else 0.78 * ins
                    maneuver_base = 0.12
                elif attacker.pace_mode == "ATTACK" and random.random() < 0.35:
                    maneuver = "DIVEBOMB"
                    target_d = 0.82 * ins if defender.d * ins < 0.15 else -0.80 * ins
                    maneuver_base = -0.08
                else:
                    maneuver = "OUTSIDE"
                    target_d = -0.80 * ins
                    maneuver_base = -0.06 + (self.track.track_width_m - 13.0) * 0.10
            else:
                if random.random() < 0.75:
                    maneuver = "DIVEBOMB"
                    target_d = 0.80 * ins
                    maneuver_base = 0.20
                else:
                    maneuver = "SWITCHBACK"
                    target_d = -0.76 * ins if defender.d * ins > 0.05 else 0.76 * ins
                    maneuver_base = 0.08
        else:
            # Standard Corner: Divebomb only if inside door is left open; otherwise work outside/switchback
            if is_braking_zone:
                if def_covers_inside:
                    if attacker.skills["racecraft"] >= 88 and random.random() < 0.38:
                        maneuver = "DUMMY"
                        target_d = -0.78 * ins if defender.d * ins > 0.05 else 0.78 * ins
                        maneuver_base = 0.08
                    elif self.track.track_width_m >= 13.4 or random.random() < 0.65:
                        maneuver = "OUTSIDE"
                        target_d = -0.80 * ins
                        maneuver_base = -0.12 + (self.track.track_width_m - 13.0) * 0.10
                    else:
                        maneuver = "SWITCHBACK"
                        target_d = -0.76 * ins if defender.d * ins > 0.05 else 0.76 * ins
                        maneuver_base = 0.02
                else:
                    r = random.random()
                    if r < 0.52:
                        maneuver = "DIVEBOMB"
                        target_d = 0.78 * ins
                        maneuver_base = 0.15
                    elif r < 0.80:
                        maneuver = "SWITCHBACK"
                        target_d = -0.76 * ins if defender.d * ins > 0.05 else 0.76 * ins
                        maneuver_base = 0.06
                    else:
                        maneuver = "OUTSIDE"
                        target_d = -0.80 * ins
                        maneuver_base = -0.10 + (self.track.track_width_m - 13.0) * 0.10
            else:
                if random.random() < 0.58:
                    maneuver = "SWITCHBACK"
                    target_d = -0.76 * ins if defender.d * ins > 0.05 else 0.76 * ins
                    maneuver_base = 0.04
                else:
                    maneuver = "OUTSIDE"
                    target_d = -0.78 * ins
                    maneuver_base = -0.14 + (self.track.track_width_m - 13.0) * 0.10

        atk_skill = attacker.skills["racecraft"] * 0.65 + attacker.skills["pace"] * 0.35
        def_skill = defender.skills["defense"] * 0.68 + defender.skills["racecraft"] * 0.32
        skill_delta = atk_skill - def_skill
        if self.wetness > 0.15:
            skill_delta += (attacker.skills["wet_skill"] - defender.skills["wet_skill"]) * 0.35

        car_delta = attacker.car_perf_index - defender.car_perf_index
        grip_delta = (attacker.grip_snapshot - defender.grip_snapshot) * 18.0

        ers_mod = (
            (1.20 if attacker.overtake_active else (0.35 if attacker.boost_active else 0.0))
            - (0.30 if defender.boost_active else 0.0)
        )
        width_mod = (self.track.track_width_m - 13.2) * 0.10
        agg_mod = 0.30 if attacker.pace_mode == "ATTACK" else (0.12 if attacker.pace_mode == "PUSH" else -0.08)

        logit = (
            maneuver_base
            + skill_delta * 0.095
            + car_delta * 0.125
            + grip_delta * 0.105
            + ers_mod
            + width_mod
            + agg_mod
        )
        p_success = 1.0 / (1.0 + math.exp(-max(-4.2, min(4.2, logit))))
        return maneuver, p_success, target_d

    def _resolve_battles_and_incidents(self, dt: float, event_cb) -> None:
        """Evaluate wheel-to-wheel 2D lane shifts, smooth side-by-side overtaking maneuvers, defense & contact."""
        active = [c for c in self.standings if not c.dnf and not c.finished and not c.in_pits and c.spin_timer <= 0.0]
        for c in active:
            c.battle_with = None

        if self.flag_state in ("VSC", "SC", "LIGHTS"):
            return

        min_long_m = CAR_LEN_PX / self.track.px_per_m
        half_usable = self.track.track_width_px * 0.39
        min_d_sep = CAR_WID_PX / half_usable

        # Sustain active passing momentum smoothly through the adjacent lane (zero teleportation!)
        for c in active:
            if c.maneuver_pass_timer > 0.0 and c.maneuver_target_id:
                tgt = self.cars_by_id.get(c.maneuver_target_id)
                if tgt and not tgt.dnf and not tgt.in_pits:
                    # Require a full clear car length ahead (1.35x) before ending passing lane commitment
                    if c.total_dist > tgt.total_dist + min_long_m * 1.35:
                        c.maneuver_pass_timer = 0.0
                        c.maneuver_target_id = None
                        c.battle_with = None
                        c.attacking_side = 0.0
                        tgt.battle_with = None
                        tgt.attacking_side = 0.0
                        tgt.defense_moves = 0
                        tgt.defense_timer = 0.0
                    else:
                        lat_sep = abs(compute_lateral_screen_px(self.track, c.d,c.s) - compute_lateral_screen_px(self.track, tgt.d,tgt.s))
                        if lat_sep >= CAR_WID_PX * 0.86:
                            st_c = self.track.sample(c.s)["station"]
                            v_env_c = self.v_env[st_c]
                            if c.v < v_env_c and c.v < tgt.v + 1.2:
                                c.v = min(v_env_c, c.v + 3.2 * dt)
                            if c.total_dist > tgt.total_dist and tgt.v > c.v:
                                tgt.v = max(4.0, tgt.v - 2.4 * dt)
                            # Defending car leaves generous racing room on opposite flank
                            tgt_room_side = 1.0 if c.d < tgt.d else -1.0
                            tgt.target_d = max(-0.84, min(0.84, c.target_d + tgt_room_side * max(0.82, min_d_sep * 1.30)))

        for i in range(1, len(active)):
            defender = active[i - 1]
            attacker = active[i]
            if defender.lap != attacker.lap:
                continue

            actual_gap = defender.total_dist - attacker.total_dist
            if actual_gap < -4.0 or actual_gap > max(38.0, min_long_m * 1.55):
                continue

            if attacker.team_id == defender.team_id:
                if attacker.team_order == "HOLD":
                    if attacker.v > defender.v * 0.995:
                        attacker.v = max(defender.v * 0.995, attacker.v - 22.0 * dt)
                    continue
                elif defender.team_order == "YIELD":
                    # Defender cooperatively lets teammate through without defending or blocking!
                    attacker.maneuver_pass_timer = 2.8
                    attacker.maneuver_target_id = defender.driver_id
                    side = 1.0 if attacker.d <= 0.0 else -1.0
                    defender.target_d = max(-0.84, min(0.84, side * 0.78))
                    defender.defense_moves = 0
                    defender.defense_timer = 0.0
                    defender.maneuver = ""
                    attacker.target_d = max(-0.84, min(0.84, -side * 0.45))
                    continue

            smp = self.track.sample(attacker.s)
            st = smp["station"]
            ins = float(smp.get("inside_sign", 1))
            in_yellow = (self.flag_state == "YELLOW" and self.yellow_sector == smp["sector"])
            if in_yellow:
                if attacker.pace_mode == "ATTACK" and random.random() < 0.004 * dt:
                    attacker.time_penalty_s += 10
                    event_cb(
                        "PENALTY",
                        f"PENALTY: +10s Time Penalty for #{attacker.number} {attacker.code} â€” Overtaking under Yellow Flags!",
                    )
                else:
                    if attacker.v > defender.v:
                        attacker.v = max(defender.v, attacker.v - 24.0 * dt)
                    continue

            attacker.battle_with = defender.driver_id
            defender.battle_with = attacker.driver_id

            t1_s = self.track.corners[0]["s_m"] if self.track.corners else 320.0
            if defender.lap == 1 and defender.total_dist < t1_s * 0.75:
                def_line = defender.grid_start_d
            else:
                def_line = (0.36 if defender.skills["defense"] >= 86 else 0.18) * ins

            if defender.maneuver_pass_timer <= 0.0:
                if defender.defense_moves == 0:
                    # Exactly ONE defensive move: defender commits to defending line
                    defender.defense_moves = 1
                    defender.defending_side = def_line
                    defender.defense_timer = 4.5
                    defender.target_d = def_line
                    defender.maneuver = "DEFEND"
                    defender.maneuver_timer = 3.5
                else:
                    # STRICT ONE-MOVE RULE: Cars are coded to NOT move more than once!
                    # Defender stays firmly locked on its committed defending line throughout the battle.
                    defender.target_d = defender.defending_side

            # Ensure attacker's passing lane always clears defender laterally by >= min_d_sep * 1.30
            if attacker.maneuver_timer <= 0.0 and attacker.maneuver_pass_timer <= 0.0:
                if attacker.attacking_side == 0.0:
                    attacker.attacking_side = -1.0 if defender.target_d >= 0.0 else 1.0
                side = attacker.attacking_side
                if defender.target_d + side * min_d_sep * 1.30 > 0.86:
                    side = -1.0
                    attacker.attacking_side = -1.0
                elif defender.target_d + side * min_d_sep * 1.30 < -0.86:
                    side = 1.0
                    attacker.attacking_side = 1.0
                attacker.target_d = max(-0.86, min(0.86, defender.target_d + side * max(0.85, min_d_sep * 1.30)))

            # Aggressive slingshot attack launch window: up to 2.85x car lengths on straights / braking zones
            max_attempt_gap = min_long_m * (2.85 if (smp.get("straight_mode", False) or self.is_braking[st]) else 1.85)
            if (
                0.0 <= actual_gap <= max_attempt_gap
                and attacker.maneuver_attempt_cooldown <= 0.0
                and attacker.maneuver_pass_timer <= 0.0
                and attacker.v >= defender.v - 2.8
            ):
                maneuver, p_success, man_d = self.select_and_evaluate_maneuver(
                    attacker, defender, smp, self.is_braking[st]
                )
                # Guarantee chosen maneuver target_d clears defender's lane laterally
                if abs(man_d - defender.target_d) < min_d_sep * 1.30:
                    side = attacker.attacking_side if attacker.attacking_side != 0.0 else (-1.0 if defender.target_d >= 0.0 else 1.0)
                    man_d = max(-0.86, min(0.86, defender.target_d + side * min_d_sep * 1.30))

                attacker.maneuver = maneuver
                attacker.maneuver_timer = 2.8
                attacker.target_d = man_d
                # Shorter attempt cooldown: aggressive pursuit
                attacker.maneuver_attempt_cooldown = random.uniform(1.6, 3.2)

                turn = self.track.nearest_corner(attacker.s)
                target_pos = defender.pos

                if random.random() < p_success:
                    # Initiate clean side-by-side overtaking pass!
                    attacker.maneuver_pass_timer = 2.6
                    attacker.maneuver_target_id = defender.driver_id
                    if attacker.overtake_active:
                        # Slingshot punch: attacker surges past defender with smooth envelope-bounded velocity
                        st_atk = self.track.sample(attacker.s)["station"]
                        if attacker.v < self.v_env[st_atk]:
                            attacker.v = min(self.v_env[st_atk], attacker.v + 1.2)
                    # Defender respects the completed pass and leaves clear lateral room
                    side = 1.0 if attacker.target_d < defender.d else -1.0
                    defender.target_d = max(-0.86, min(0.86, attacker.target_d + side * min_d_sep * 1.30))
                    defender.defense_moves = 0
                    defender.defense_timer = 0.0
                    defender.battle_with = None
                    defender.attacking_side = 0.0
                    attacker.attacking_side = 0.0

                    if target_pos <= 12 and attacker.overtake_cooldown <= 0.0 and self.race_clock > 7.0:
                        attacker.overtake_cooldown = 6.5
                        ovt_tag = " [OVERTAKE MODE]" if attacker.overtake_active else ""
                        msg_by_maneuver = {
                            "DIVEBOMB": f"DIVEBOMB P{target_pos}: #{attacker.number} {attacker.code} lunges late on the brakes inside {defender.code} at Turn {turn}{ovt_tag}!",
                            "OUTSIDE": f"OUTSIDE SEND P{target_pos}: #{attacker.number} {attacker.code} sweeps around the outside of {defender.code} through Turn {turn}{ovt_tag}!",
                            "SWITCHBACK": f"SWITCHBACK P{target_pos}: #{attacker.number} {attacker.code} cuts back underneath {defender.code} exiting Turn {turn}!",
                            "DUMMY": f"DUMMY MOVE P{target_pos}: #{attacker.number} {attacker.code} sells the feint and slices past {defender.code} into Turn {turn}!",
                            "SLIPSTREAM": f"SLIPSTREAM PASS P{target_pos}: #{attacker.number} {attacker.code} drafts past {defender.code} on approach to Turn {turn}{ovt_tag}!",
                        }
                        event_cb("OVERTAKE", msg_by_maneuver.get(maneuver, f"OVERTAKE P{target_pos}: {attacker.code} passes {defender.code} at Turn {turn}!"))
                else:
                    defender.maneuver = "DEFEND"
                    defender.maneuver_timer = 2.0
                    if attacker.v > defender.v * 0.96:
                        attacker.v = max(defender.v * 0.96, attacker.v - 18.0 * dt)
                    attacker.maneuver_timer = 0.0
                    # On stout defense, attacker holds clean slipstream line behind defender
                    attacker.target_d = defender.d
                    attacker.attacking_side = 0.0

                    if maneuver in ("DIVEBOMB", "OUTSIDE") and smp["curv"] > 0.0085:
                        lockup_prob = 0.10 * (1.20 - attacker.skills["consistency"] / 110.0)
                        if random.random() < lockup_prob:
                            attacker.smoke = 1.9
                            attacker.tire_wear = min(0.99, attacker.tire_wear + 0.012)
                            inc_chance = 0.004 * max(0.2, 1.15 - attacker.skills["consistency"] / 100.0)
                            if attacker.contact_cooldown <= 0.0 and defender.contact_cooldown <= 0.0 and random.random() < inc_chance:
                                self._handle_collision(attacker, defender, smp["sector"], event_cb)
                                continue

                    if target_pos <= 6 and defender.overtake_cooldown <= 0.0 and random.random() < 0.25 and self.race_clock > 10.0:
                        defender.overtake_cooldown = 9.0
                        event_cb(
                            "RACE_CONTROL",
                            f"STOUT DEFENSE P{target_pos}: #{defender.number} {defender.code} shuts the door on {attacker.code}'s {maneuver} at Turn {turn}!",
                        )

    def _handle_collision(self, attacker: CarState, defender: CarState, sector: int, event_cb) -> None:
        attacker.contact_cooldown = 12.0
        defender.contact_cooldown = 12.0
        attacker.maneuver_pass_timer = 0.0
        turn = self.track.nearest_corner(attacker.s)

        culprit = attacker if random.random() < 0.65 else defender
        victim = defender if culprit is attacker else attacker
        roll = random.random()

        is_lap1 = attacker.lap == 1
        if roll < 0.62 or is_lap1:
            victim.v = max(8.0, victim.v - 2.2)
            deflect_dir = 1.0 if victim.d >= culprit.d else -1.0
            victim.target_d = max(-1.05, min(1.05, victim.d + deflect_dir * 0.22))
            culprit.target_d = max(-1.05, min(1.05, culprit.d - deflect_dir * 0.12))
            victim.smoke = 1.4
            attacker.sparks = True
            defender.sparks = True
            # Authentic damage on EVERY collision contact: both cars suffer physical damage
            culprit_dmg = random.uniform(0.14, 0.26)
            culprit.wing_damage = min(0.85, culprit.wing_damage + culprit_dmg)
            culprit.wing_damage_side = "RIGHT" if culprit.d < victim.d else "LEFT"
            culprit.repair_cost_m += round(culprit_dmg * 0.75, 2)
            culprit.tire_wear = min(0.99, culprit.tire_wear + 0.02)

            victim_dmg = random.uniform(0.10, 0.20)
            victim.wing_damage = min(0.85, victim.wing_damage + victim_dmg)
            victim.wing_damage_side = "LEFT" if victim.d > culprit.d else "RIGHT"
            victim.repair_cost_m += round(victim_dmg * 0.65, 2)
            victim.tire_wear = min(0.99, victim.tire_wear + 0.02)

            if culprit.wing_damage >= 0.35:
                culprit.box_this_lap = True
            if victim.wing_damage >= 0.35:
                victim.box_this_lap = True

            event_cb(
                "INCIDENT",
                f"WHEEL-TO-WHEEL! Contact between #{attacker.number} {attacker.code} and #{defender.number} {defender.code} at Turn {turn} (Wing Damage)!",
            )
            self.stewards_queue.append(
                {
                    "timer": 7.5,
                    "stage": "NOTED",
                    "turn": turn,
                    "culprit_id": culprit.driver_id,
                    "summary": f"{attacker.code} & {defender.code}",
                    "reason": "Forcing Another Driver Off the Track",
                    "verdict": random.choice(["NFA", "5S", "5S"]),
                }
            )
        elif roll < 0.985:
            attacker.wing_damage = min(0.85, attacker.wing_damage + random.uniform(0.24, 0.45))
            attacker.wing_damage_side = "RIGHT" if attacker.d > defender.d else "LEFT"
            attacker.repair_cost_m += 0.45
            if attacker.wing_damage >= 0.35 and not attacker.box_this_lap:
                attacker.box_this_lap = True
            victim.spin_timer = random.uniform(2.8, 4.5)
            victim.spin_omega = random.choice([-5.8, 5.8]) * random.uniform(0.85, 1.25)
            victim.spin_lateral_dir = 1.0 if victim.d >= 0.0 else -1.0
            victim.spin_rebound_done = False
            victim.smoke = 2.4
            self.radio_dispatcher.trigger_spin(victim, turn, event_cb, self.race_clock)
            victim.repair_cost_m += 0.32
            self.flag_state = "YELLOW"
            self.yellow_sector = sector
            self.yellow_timer = 8.0
            event_cb(
                "CRASH",
                f"COLLISION AT TURN {turn}! {attacker.code} and {defender.code} tangle — {victim.code} spins & carbon debris flies!",
            )
            self.stewards_queue.append(
                {
                    "timer": 8.5,
                    "stage": "NOTED",
                    "turn": turn,
                    "culprit_id": culprit.driver_id,
                    "summary": f"{attacker.code} & {defender.code} collision",
                    "reason": "Causing a Collision",
                    "verdict": random.choice(["5S", "10S", "NFA"]),
                }
            )
        else:
            # Rare terminal crash (top 4% of collisions only)
            victim.dnf = True
            victim.dnf_reason = f"Collision with {culprit.code} (T{turn})"
            victim.dnf_timer = 38.0
            victim.v = 0.0
            victim.target_d = 1.35 if victim.d >= 0.0 else -1.35
            victim.smoke = 4.5
            victim.repair_cost_m += round(random.uniform(0.95, 2.10), 2)
            victim.wing_damage = min(0.90, victim.wing_damage + random.uniform(0.40, 0.75))
            self._update_xy(victim)

            double_dnf = random.random() < 0.16
            if double_dnf:
                min_long_m = CAR_LEN_PX / self.track.px_per_m
                culprit.dnf = True
                culprit.dnf_reason = f"Collision with {victim.code} (T{turn})"
                culprit.dnf_timer = 38.0
                culprit.v = 0.0
                culprit.d = 1.42 if culprit.d >= 0.0 else -1.42
                culprit.total_dist = victim.total_dist - min_long_m * 1.15
                culprit.s = culprit.total_dist % self.track.length_m
                culprit.smoke = 4.5
                culprit.repair_cost_m += round(random.uniform(1.10, 2.25), 2)
                self._update_xy(culprit)
                event_cb(
                    "CRASH",
                    f"MASSIVE CRASH AT TURN {turn}! BOTH {attacker.code} ({attacker.team_short}) AND {defender.code} ({defender.team_short}) ARE OUT!",
                )
            else:
                culprit.wing_damage = min(0.90, culprit.wing_damage + 0.55)
                culprit.wing_damage_side = "BOTH" if random.random() < 0.45 else ("RIGHT" if culprit.d > victim.d else "LEFT")
                culprit.repair_cost_m += 0.65
                if culprit.wing_damage >= 0.35 and not culprit.box_this_lap:
                    culprit.box_this_lap = True
                event_cb(
                    "CRASH",
                    f"HEAVY COLLISION AT TURN {turn}! {victim.code} is OUT in the gravel; {culprit.code} limps on with heavy damage!",
                )
                self.stewards_queue.append(
                    {
                        "timer": 9.0,
                        "stage": "NOTED",
                        "turn": turn,
                        "culprit_id": culprit.driver_id,
                        "summary": f"{attacker.code} / {defender.code} crash",
                        "reason": "Causing a Serious Collision",
                        "verdict": random.choice(["10S", "10S", "DT"]),
                    }
                )

            self.trigger_safety_car("SC", f"Debris at Turn {turn} ({attacker.code}/{defender.code})", event_cb)

    def _on_physical_contact(self, c1: CarState, c2: CarState, sat: tuple[float, float, float, float], event_cb) -> None:
        """Physical contact physics: sparks, smoke, deceleration scrub, front wing/sidepod damage, stewards."""
        if c1.dnf or c2.dnf or c1.in_pits or c2.in_pits:
            return

        # Passing or battling cars are holding designated adjacent lanes; clean racing is never an incident
        if (
            c1.maneuver_pass_timer > 0.0
            or c2.maneuver_pass_timer > 0.0
            or c1.maneuver_timer > 0.0
            or c2.maneuver_timer > 0.0
            or c1.battle_with == c2.driver_id
            or c2.battle_with == c1.driver_id
        ):
            return

        # Lap 1 start discipline: pack is compressed 22-wide; SAT cushions without false contact alerts/damage
        if c1.lap == 1 or c2.lap == 1:
            return

        # Cooldown prevents spamming damage, repeated deceleration scrub, and alerts across consecutive frames
        if c1.contact_cooldown > 0.0 or c2.contact_cooldown > 0.0:
            return

        L = self.track.length_m
        arc_fwd = (c1.s - c2.s) % L
        arc_bwd = L - arc_fwd
        if arc_fwd < arc_bwd or (abs(arc_fwd - arc_bwd) < 0.05 and c1.total_dist >= c2.total_dist):
            ahead, behind = c1, c2
        else:
            ahead, behind = c2, c1

        turn = self.track.nearest_corner(behind.s)
        pen_l1, pen_w1, pen_l2, pen_w2 = sat
        min_pen_w = min(pen_w1, pen_w2)
        delta_v = behind.v - ahead.v
        speed_gap = abs(c1.v - c2.v)

        # Distinguish side-by-side vs nose-to-tail contact
        is_side_by_side = min_pen_w < 3.2 and abs(c1.d - c2.d) > 0.22

        if is_side_by_side:
            # Physical lateral separation impulse (smooth target guidance, zero snap!)
            d_diff = c1.d - c2.d
            side_norm = 1.0 if d_diff >= 0.0 else -1.0
            c1.target_d = max(-1.05, min(1.05, c1.d + side_norm * 0.18))
            c2.target_d = max(-1.05, min(1.05, c2.d - side_norm * 0.18))
            c1.sparks = True
            c2.sparks = True
            # Authentic sidepod/endplate abrasion damage whenever physical contact occurs
            contact_dmg = random.uniform(0.04, 0.09)
            c1.wing_damage = min(0.85, c1.wing_damage + contact_dmg)
            c2.wing_damage = min(0.85, c2.wing_damage + contact_dmg)
            c1.tire_wear = min(0.99, c1.tire_wear + 0.008)
            c2.tire_wear = min(0.99, c2.tire_wear + 0.008)

            if speed_gap > 5.5:
                c1.contact_cooldown = 6.0
                c2.contact_cooldown = 6.0
                c1.smoke = max(c1.smoke, 1.4)
                c2.smoke = max(c2.smoke, 1.4)
                c1.v = max(12.0, c1.v - 1.2)
                c2.v = max(12.0, c2.v - 1.2)
                c1.tire_wear = min(0.99, c1.tire_wear + 0.012)
                c2.tire_wear = min(0.99, c2.tire_wear + 0.012)

                side_car = c1 if c1.v > c2.v else c2
                other_car = c2 if side_car is c1 else c1
                side = "RIGHT" if side_car.d < other_car.d else "LEFT"
                side_car.wing_damage = min(0.35, side_car.wing_damage + random.uniform(0.06, 0.12))
                side_car.wing_damage_side = side
                side_car.repair_cost_m += round(random.uniform(0.08, 0.18), 2)
                if side_car.wing_damage >= 0.35 and not side_car.box_this_lap:
                    side_car.box_this_lap = True

                event_cb(
                    "INCIDENT",
                    f"WHEEL BANGING! Contact between #{c1.number} {c1.code} and #{c2.number} {c2.code} fighting through Turn {turn}!",
                )
                self.radio_dispatcher.trigger_contact(c1, c2, turn, event_cb, self.race_clock)
                self.stewards_queue.append(
                    {
                        "timer": 7.0,
                        "stage": "NOTED",
                        "turn": turn,
                        "culprit_id": c1.driver_id if c1.d < c2.d else c2.driver_id,
                        "summary": f"{c1.code} & {c2.code} side-by-side",
                        "reason": "Wheel-to-wheel contact",
                        "verdict": random.choice(["NFA", "NFA", "5S"]),
                    }
                )
        else:
            # Longitudinal contact: trailing car into rear of car ahead
            # Physical longitudinal impulse
            behind.v = max(8.0, ahead.v - 1.4)
            ahead.v = min(ahead.v + 0.8, 95.0)
            behind.sparks = True
            ahead.sparks = True

            # Authentic damage: trailing car front wing takes real damage on closing contact (> 2.2 m/s / 8 km/h)
            rear_dmg = min(0.35, max(0.08, delta_v * 0.038))
            behind.wing_damage = min(0.85, behind.wing_damage + rear_dmg)
            behind.wing_damage_side = "RIGHT" if behind.d > ahead.d else "LEFT"
            behind.repair_cost_m += round(rear_dmg * 0.65, 2)
            ahead.tire_wear = min(0.99, ahead.tire_wear + 0.012)
            if behind.wing_damage >= 0.35 and not behind.box_this_lap:
                behind.box_this_lap = True

            if delta_v > 6.0:
                c1.contact_cooldown = 6.0
                c2.contact_cooldown = 6.0
                behind.smoke = max(behind.smoke, 1.5)

                wing_add = random.uniform(0.18, 0.36)
                behind.wing_damage = min(0.85, behind.wing_damage + wing_add)
                if behind.wing_damage_side == "NONE":
                    behind.wing_damage_side = "RIGHT" if behind.d > ahead.d else ("LEFT" if behind.d < ahead.d else "BOTH")
                elif behind.wing_damage_side != "BOTH" and random.random() < 0.3:
                    behind.wing_damage_side = "BOTH"

                behind.repair_cost_m += round(random.uniform(0.20, 0.45), 2)
                behind.tire_wear = min(0.99, behind.tire_wear + 0.020)
                ahead.tire_wear = min(0.99, ahead.tire_wear + 0.015)
                if behind.wing_damage >= 0.35 and not behind.box_this_lap:
                    behind.box_this_lap = True

                if delta_v > 8.5 and random.random() < 0.40:
                    ahead.spin_timer = random.uniform(2.8, 4.2)
                    ahead.spin_omega = random.choice([-5.8, 5.8]) * random.uniform(0.85, 1.25)
                    ahead.spin_lateral_dir = 1.0 if ahead.d >= 0.0 else -1.0
                    ahead.spin_rebound_done = False
                    ahead.smoke = 2.8
                    self.radio_dispatcher.trigger_spin(ahead, turn, event_cb, self.race_clock)
                    event_cb(
                        "CRASH",
                        f"HEAVY CONTACT AT TURN {turn}! #{behind.number} {behind.code} tags #{ahead.number} {ahead.code} into a spin! Front wing damage for {behind.code}!",
                    )
                else:
                    event_cb(
                        "INCIDENT",
                        f"FRONT WING DAMAGE! #{behind.number} {behind.code} misjudges braking and hits the rear of #{ahead.number} {ahead.code} at Turn {turn}!",
                    )
                self.radio_dispatcher.trigger_contact(behind, ahead, turn, event_cb, self.race_clock)
                self.stewards_queue.append(
                    {
                        "timer": 8.0,
                        "stage": "NOTED",
                        "turn": turn,
                        "culprit_id": behind.driver_id,
                        "summary": f"{behind.code} on {ahead.code}",
                        "reason": "Causing a Collision",
                        "verdict": random.choice(["5S", "10S", "NFA"]),
                    }
                )

    def _update_standings(self, dt: float, event_cb) -> None:
        prev_pos = {c.driver_id: c.pos for c in self.standings}

        def sort_key(c: CarState):
            if c.dnf:
                return (2, -c.total_dist)
            if c.finished:
                return (0, c.finish_time)
            return (1, -c.total_dist)

        self.standings.sort(key=sort_key)

        leader = self.standings[0]
        for idx, c in enumerate(self.standings):
            new_p = idx + 1
            if c.team_order == "YIELD":
                tm = next((o for o in self.standings if o.team_id == c.team_id and o.driver_id != c.driver_id and not o.dnf), None)
                if tm and tm.total_dist > c.total_dist:
                    c.team_order = "FREE"
                    c.swap_target_id = None
                    tm.swap_pass_id = None
            old_p = prev_pos.get(c.driver_id, new_p)
            if (
                new_p < old_p
                and not c.in_pits
                and not c.dnf
                and c.overtake_cooldown <= 0.0
                and self.race_clock > 8.0
            ):
                passed = self.standings[idx + 1] if idx + 1 < len(self.standings) else None
                if passed and not passed.in_pits and not passed.dnf and passed.spin_timer <= 0.0:
                    c.overtake_cooldown = 6.0
                    ovt_tag = " [OVERTAKE MODE]" if c.overtake_active else ""
                    turn = self.track.nearest_corner(c.s)
                    man_lbl = f" ({c.maneuver})" if c.maneuver else ""
                    if new_p <= 12 or getattr(c, "team_id", "") == getattr(self, "player_team_id", "") or getattr(passed, "team_id", "") == getattr(self, "player_team_id", ""):
                        event_cb(
                            "OVERTAKE",
                            f"OVERTAKE P{new_p}: #{c.number} {c.code} passes {passed.code} near Turn {turn}{man_lbl}{ovt_tag}!",
                        )
                    # Trigger event-driven team radio for overtaken driver or overtaker
                    self.radio_dispatcher.trigger_overtake_event(
                        overtaker=c,
                        overtaken=passed,
                        new_p=new_p,
                        turn=turn,
                        event_cb=event_cb,
                        clock=self.race_clock,
                        maneuver=getattr(c, "maneuver", ""),
                    )
            c.pos = new_p

            if idx == 0 or c.dnf:
                c.gap_to_leader = 0.0
                c.interval_ahead = 0.0
            elif c.finished and leader.finished:
                c.gap_to_leader = round(c.finish_time - leader.finish_time, 3)
                prev_c = self.standings[idx - 1]
                c.interval_ahead = round(c.finish_time - prev_c.finish_time, 3) if prev_c.finished else 0.0
            else:
                ref_v = max(c.v, 48.0)
                c.gap_to_leader = round(max(0.0, (leader.total_dist - c.total_dist) / ref_v), 3)
                prev_c = self.standings[idx - 1]
                c.interval_ahead = round(max(0.0, (prev_c.total_dist - c.total_dist) / ref_v), 3)

        if leader.finished:
            if not getattr(self, "win_radio_triggered", False):
                self.win_radio_triggered = True
                self.radio_dispatcher.trigger_race_win(leader, event_cb, self.race_clock)
            self.post_finish_timer += dt
            all_done = all(c.finished or c.dnf for c in self.cars)
            if all_done or self.post_finish_timer > 18.0:
                for c in self.cars:
                    if not c.dnf and not c.finished:
                        c.finished = True
                        c.finish_time = round(self.race_clock + c.gap_to_leader + c.time_penalty_s, 3)
                self.standings.sort(key=sort_key)
                for idx, c in enumerate(self.standings):
                    c.pos = idx + 1
                self.finished = True


def _fmt_lap(seconds: float) -> str:
    mins = int(seconds // 60)
    rem = seconds - mins * 60
    return f"{mins}:{rem:06.3f}"
