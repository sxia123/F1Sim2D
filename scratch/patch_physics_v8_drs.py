from pathlib import Path

path = Path("sim/physics.py")
content = path.read_text(encoding="utf-8")

# 1. CarState attributes
carstate_target = """        # 2026 Active Aero & Hybrid ERS / Overtake Mode
        self.aero_mode: str = "CORNER"
        self.battery_mj: float = 3.8
        self.max_battery_mj: float = 4.0
        self.overtake_eligible: bool = False
        self.overtake_active: bool = False
        self.boost_active: bool = False
        self.recharging: bool = False"""

carstate_repl = """        # 2026 Active Aero & Hybrid ERS / Overtake Mode & Classic DRS
        self.aero_mode: str = "CORNER"
        self.battery_mj: float = 3.8
        self.max_battery_mj: float = 4.0
        self.overtake_eligible: bool = False
        self.overtake_active: bool = False
        self.drs_eligible: bool = False
        self.drs_eligible_zone: int | None = None
        self.drs_active: bool = False
        self.boost_active: bool = False
        self.recharging: bool = False"""

assert carstate_target in content, "carstate_target not found"
content = content.replace(carstate_target, carstate_repl, 1)

# 2. QualifyingSession.__init__ accepts regulations
qs_init_target = """    def __init__(
        self,
        track: CompiledTrack,
        teams_by_id: dict[str, dict],
        active_drivers: list[dict],
        wetness: float,
        is_sprint_quali: bool = False,
    ):
        self.track = track
        self.is_sprint_quali = is_sprint_quali
        self.v_env, self.is_braking = build_speed_envelope(track)
        self.wetness: float = wetness
        self.finished: bool = False"""

qs_init_repl = """    def __init__(
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
        self.wetness: float = wetness
        self.finished: bool = False"""

assert qs_init_target in content, "qs_init_target not found"
content = content.replace(qs_init_target, qs_init_repl, 1)

# Battery in QualifyingSession.__init__
qs_car_target = """            car = CarState(drv, team, idx + 1, start_comp, 3)"""
qs_car_repl = """            car = CarState(drv, team, idx + 1, start_comp, 3)
            car.max_battery_mj = float(self.regulations.get("max_battery_mj", 4.0))
            car.battery_mj = car.max_battery_mj"""

assert qs_car_target in content, "qs_car_target not found"
content = content.replace(qs_car_target, qs_car_repl, 1)

# QualifyingSession.step target_v and acc
qs_step_target = """            target_v = self.v_env[st] * math.sqrt(max(0.65, car_grip))
            if smp["straight_mode"] and self.wetness < 0.30 and not self.is_braking[st]:
                car.aero_mode = "STRAIGHT"
                pu_bonus = 1.0 + (u["power_unit"] - 5) * 0.009
                target_v = min(96.5 * pu_bonus, target_v * 1.05)
            else:
                car.aero_mode = "CORNER"

            if car.v < target_v:
                acc = 13.5 * (1.0 + (u["power_unit"] - 5) * 0.018) * max(0.28, 1.0 - (max(0.0, car.v) / 104.0) ** 1.8)
                car.v = min(target_v, car.v + acc * dt)
                car.braking = False
            else:
                car.v = max(target_v, car.v - 42.0 * dt)
                car.braking = car.v - target_v > 3.5"""

qs_step_repl = """            ice_mult = float(self.regulations.get("ice_power_mult", 1.0))
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
                car.braking = car.v - target_v > 3.5"""

assert qs_step_target in content, "qs_step_target not found"
content = content.replace(qs_step_target, qs_step_repl, 1)

# 3. RaceSession.__init__ accepts regulations and starting_compounds
rs_init_target = """    def __init__(
        self,
        track: CompiledTrack,
        teams_by_id: dict[str, dict],
        grid_drivers: list[dict],
        wetness: float,
        rain_forecast: float,
        player_team_id: str,
        is_sprint: bool = False,
    ):
        self.track = track
        self.is_sprint = is_sprint"""

rs_init_repl = """    def __init__(
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
        self.starting_compounds = dict(starting_compounds or {})"""

assert rs_init_target in content, "rs_init_target not found"
content = content.replace(rs_init_target, rs_init_repl, 1)

# Tyre selection in RaceSession.__init__
rs_tyre_target = """        for idx, drv in enumerate(grid_drivers):
            team = teams_by_id[drv["team_id"]]
            grid_pos = idx + 1
            if wetness > 0.55:
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

            car = CarState(drv, team, grid_pos, comp, self.total_laps)"""

rs_tyre_repl = """        for idx, drv in enumerate(grid_drivers):
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

            car = CarState(drv, team, grid_pos, comp, self.total_laps)
            car.max_battery_mj = float(self.regulations.get("max_battery_mj", 4.0))
            car.battery_mj = car.max_battery_mj"""

assert rs_tyre_target in content, "rs_tyre_target not found"
content = content.replace(rs_tyre_target, rs_tyre_repl, 1)

# Add set_starting_compound method to RaceSession
rs_method_target = """    def _team_pit_box_s(self, car: CarState) -> float:"""
rs_method_repl = """    def set_starting_compound(self, driver_id: str, compound: str) -> bool:
        if compound in TIRE_COMPOUNDS and driver_id in self.cars_by_id:
            car = self.cars_by_id[driver_id]
            car.compound = compound
            car.compounds_used = {compound}
            car.tire_age_laps = 0
            car.tire_wear = 0.01
            self.starting_compounds[driver_id] = compound
            return True
        return False

    def _team_pit_box_s(self, car: CarState) -> float:"""

assert rs_method_target in content, "rs_method_target not found"
content = content.replace(rs_method_target, rs_method_repl, 1)

# 4. In RaceSession._step_car, aero_mode and battery drain/harvest
rs_aero_target = """        in_yellow = (self.flag_state == "YELLOW" and self.yellow_sector == sector)
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

        car.overtake_active = False
        car.boost_active = False
        car.recharging = False

        if self.flag_state == "GREEN" and not in_yellow:
            if self.is_braking[st]:
                harvest = 0.42 * dt * (1.0 + (u["power_unit"] - 5) * 0.03)
                car.battery_mj = min(car.max_battery_mj, car.battery_mj + harvest)
                car.recharging = True
            elif car.aero_mode == "STRAIGHT" or smp["curv"] < 0.0065:
                want_overtake = (
                    car.overtake_eligible
                    and car.battery_mj > 0.25
                    and car.ers_mode != "HARVEST"
                    and (gap_ahead_s < 1.35 or car.ers_mode in ("OVERTAKE", "BOOST"))
                )
                want_boost = (
                    not want_overtake
                    and car.battery_mj > 0.55
                    and (
                        car.ers_mode == "BOOST"
                        or (car.ers_mode == "AUTO" and (gap_ahead_s < 0.85 or car.pace_mode in ("PUSH", "ATTACK")))
                    )
                )
                if want_overtake:
                    car.overtake_active = True
                    drain = 0.28 * dt * (1.0 - (u["power_unit"] - 5) * 0.025)
                    car.battery_mj = max(0.0, car.battery_mj - drain)
                elif want_boost:
                    car.boost_active = True
                    drain = 0.22 * dt
                    car.battery_mj = max(0.0, car.battery_mj - drain)
                elif car.ers_mode != "HARVEST" and car.battery_mj > 1.20:
                    # Realistic baseline corner exit and straight-line MGU-K electrical deployment
                    drain = 0.12 * dt
                    car.battery_mj = max(0.0, car.battery_mj - drain)
                elif car.ers_mode == "HARVEST" or car.battery_mj < 0.45:
                    car.recharging = True
                    car.battery_mj = min(car.max_battery_mj, car.battery_mj + 0.16 * dt)

        target_v = self.v_env[st] * math.sqrt(grip_mult)
        if car.aero_mode == "STRAIGHT":
            pu_top = 1.0 + (u["power_unit"] - 5) * 0.0024 + (u["active_aero"] - 5) * 0.0018
            if car.overtake_active:
                top_cap = min(OVERTAKE_MAX_MS, 98.6 * pu_top * (1.0 + slipstream_bonus * 1.15))
                target_v = max(target_v, top_cap)
            else:
                boost_add = 2.1 if car.boost_active else (0.0 if not car.recharging else -2.6)
                top_cap = (91.2 * pu_top + boost_add) * (1.0 + slipstream_bonus * 0.85)
                target_v = min(max(target_v, 82.0), top_cap)
        else:
            if car.overtake_active:
                target_v *= 1.052
            elif car.boost_active:
                target_v *= 1.020"""

rs_aero_repl = """        in_yellow = (self.flag_state == "YELLOW" and self.yellow_sector == sector)
        has_active_aero = self.regulations.get("has_active_aero", True)
        has_classic_drs = self.regulations.get("has_classic_drs", False)
        ice_power_mult = float(self.regulations.get("ice_power_mult", 1.0))
        is_v8_era = (self.regulations.get("era_id") == "V8_DRS")

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

        car.overtake_active = False
        car.boost_active = False
        car.recharging = False

        if self.flag_state == "GREEN" and not in_yellow:
            if self.is_braking[st]:
                base_harvest = 0.22 if is_v8_era else 0.35
                harvest = base_harvest * dt * (1.0 + (u["power_unit"] - 5) * 0.03)
                car.battery_mj = min(car.max_battery_mj, car.battery_mj + harvest)
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
                    car.battery_mj = min(car.max_battery_mj, car.battery_mj + (0.08 if is_v8_era else 0.12) * dt)
            else:
                if car.v < target_v and car.ers_mode != "HARVEST" and car.battery_mj > 0.25:
                    corner_drain = (0.12 if is_v8_era else 0.22) * dt
                    car.battery_mj = max(0.0, car.battery_mj - corner_drain)

        target_v = self.v_env[st] * math.sqrt(grip_mult)
        if has_active_aero and car.aero_mode == "STRAIGHT":
            pu_top = 1.0 + (u["power_unit"] - 5) * 0.0024 + (u["active_aero"] - 5) * 0.0018
            if car.overtake_active:
                top_cap = min(OVERTAKE_MAX_MS, 98.6 * pu_top * (1.0 + slipstream_bonus * 1.15))
                target_v = max(target_v, top_cap)
            else:
                boost_add = 2.1 if car.boost_active else (0.0 if not car.recharging else -2.6)
                top_cap = (91.2 * pu_top + boost_add) * (1.0 + slipstream_bonus * 0.85)
                target_v = min(max(target_v, 82.0), top_cap)
        elif has_classic_drs and car.drs_active:
            # Classic DRS open: +22 km/h drag reduction boost!
            pu_top = 1.0 + (u["power_unit"] - 5) * 0.0024
            drs_bonus_ms = 22.0 / 3.6  # +22 km/h (~6.11 m/s)
            top_cap = (93.5 * pu_top * ice_power_mult + drs_bonus_ms) * (1.0 + slipstream_bonus * 1.15)
            target_v = max(target_v, min(OVERTAKE_MAX_MS + 2.5, top_cap))
        elif has_classic_drs and smp["curv"] < 0.0065 and not self.is_braking[st]:
            # V8 NA Straight Top Speed without DRS
            pu_top = 1.0 + (u["power_unit"] - 5) * 0.0024
            boost_add = 1.6 if car.boost_active else 0.0
            top_cap = (90.2 * pu_top * ice_power_mult + boost_add) * (1.0 + slipstream_bonus * 0.85)
            target_v = min(max(target_v, 82.0), top_cap)
        else:
            if car.overtake_active:
                target_v *= 1.052
            elif car.boost_active:
                target_v *= 1.020"""

assert rs_aero_target in content, "rs_aero_target not found"
content = content.replace(rs_aero_target, rs_aero_repl, 1)

# 5. In RaceSession._step_car, acceleration update
accel_target = """        if car.v < target_v:
            pu_acc = 13.8 * (1.0 + (u["power_unit"] - 5) * 0.022) * (1.0 - car.wing_damage * 0.08)
            if car.overtake_active:
                pu_acc *= 1.52
            elif car.boost_active:
                pu_acc *= 1.15
            elif car.v > DERATE_START_MS:
                derate_frac = min(1.0, (car.v - DERATE_START_MS) / (DERATE_END_MS - DERATE_START_MS))
                pu_acc *= max(0.28, 1.0 - 0.65 * derate_frac)"""

accel_repl = """        if car.v < target_v:
            pu_acc = 13.8 * ice_power_mult * (1.0 + (u["power_unit"] - 5) * 0.022) * (1.0 - car.wing_damage * 0.08)
            if car.drs_active:
                pu_acc *= 1.28
            elif car.overtake_active:
                pu_acc *= 1.52
            elif car.boost_active:
                pu_acc *= 1.15
            elif car.v > DERATE_START_MS:
                derate_frac = min(1.0, (car.v - DERATE_START_MS) / (DERATE_END_MS - DERATE_START_MS))
                pu_acc *= max(0.28, 1.0 - 0.65 * derate_frac)"""

assert accel_target in content, "accel_target not found"
content = content.replace(accel_target, accel_repl, 1)

# 6. In RaceSession._step_car, DRS zone detection & activation logic
drs_detect_target = """        # Multi-DRS Zones Detection & Activation
        drs_zones = getattr(self.track, "drs_zones", None)
        ds_step = max(ds, 0.1)
        if drs_zones:
            for zone in drs_zones:
                det_s = zone["detection_s_m"]
                end_s = zone["end_s_m"]
                if (det_s - prev_s) % self.track.length_m <= ds_step:
                    if (
                        self.flag_state == "GREEN"
                        and car.lap >= 2
                        and car.lap > self.restart_no_overtake_lap
                        and car_ahead is not None
                        and not car_ahead.in_pits
                    ):
                        dist_det = (car_ahead.s - det_s) % self.track.length_m
                        time_gap = dist_det / max(car.v, 28.0)
                        if 0.02 < time_gap <= 1.000:
                            car.overtake_eligible = True
                            car.max_battery_mj = 4.5
                            car.battery_mj = min(4.5, car.battery_mj + 0.35)
                        else:
                            car.overtake_eligible = False
                            car.max_battery_mj = 4.0
                    else:
                        car.overtake_eligible = False
                        car.max_battery_mj = 4.0
                if (end_s - prev_s) % self.track.length_m <= ds_step:
                    car.overtake_eligible = False
                    car.max_battery_mj = 4.0
        else:
            det_s = self.track.detection_s_m
            if prev_s < det_s <= new_s:
                if (
                    self.flag_state == "GREEN"
                    and car.lap >= 2
                    and car.lap > self.restart_no_overtake_lap
                    and car_ahead is not None
                    and not car_ahead.in_pits
                ):
                    dist_det = (car_ahead.s - det_s) % self.track.length_m
                    time_gap = dist_det / max(car.v, 28.0)
                    if 0.02 < time_gap <= 1.000:
                        car.overtake_eligible = True
                        car.max_battery_mj = 4.5
                        car.battery_mj = min(4.5, car.battery_mj + 0.35)
                    else:
                        car.overtake_eligible = False"""

drs_detect_repl = """        # Multi-DRS Zones Detection & Activation
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

            # Active DRS Zone Check for Classic DRS Era
            car.drs_active = False
            if has_classic_drs and car.drs_eligible and car.drs_eligible_zone is not None:
                active_z = next((z for z in drs_zones if z["id"] == car.drs_eligible_zone), None)
                if active_z:
                    act_s = active_z["activation_s_m"]
                    end_s = active_z["end_s_m"]
                    z_len = (end_s - act_s) % self.track.length_m
                    cur_off = (car.s - act_s) % self.track.length_m
                    if cur_off <= z_len and not car.braking and not self.is_braking[st] and self.flag_state == "GREEN" and not in_yellow and self.wetness < 0.20:
                        car.drs_active = True
                        car.aero_mode = "DRS"
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
                    car.drs_eligible = False"""

assert drs_detect_target in content, "drs_detect_target not found"
content = content.replace(drs_detect_target, drs_detect_repl, 1)

path.write_text(content, encoding="utf-8")
print("Successfully patched sim/physics.py with V8, DRS and starting tyre logic!")

