import sys
import os

def patch_physics():
    path = os.path.join("sim", "physics.py")
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Tow calculation patch in step()
    old_tow = '''        slipstream_bonus = 0.0
        dirty_air_loss = 0.0
        gap_ahead_s = 99.0
        if car_ahead and not car_ahead.in_pits:
            dist_ahead = (car_ahead.s - car.s) % self.track.length_m
            if 2.0 < dist_ahead < 95.0:
                gap_ahead_s = dist_ahead / max(car.v, 25.0)
                if gap_ahead_s < 0.75:
                    car.tailing_timer = min(15.0, car.tailing_timer + dt)
                else:
                    car.tailing_timer = max(0.0, car.tailing_timer - dt * 0.4)
                if gap_ahead_s < 0.95:
                    slipstream_bonus = (1.0 - gap_ahead_s / 0.95) * 0.048
                    if smp["curv"] > 0.007:
                        dirty_air_loss = (1.0 - gap_ahead_s / 0.95) * 0.036
        else:
            car.tailing_timer = max(0.0, car.tailing_timer - dt * 0.4)'''

    new_tow = '''        slipstream_bonus = 0.0
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
                # - Proximity: <= 28m and <= 0.36s gap
                # - Lateral wake alignment: lateral offset <= 0.22 (drops to zero if pulled out)
                # - Track condition: straight line / flat-out only (curv < 0.0042 and not in braking zone)
                # - Realistic speed bonus: max 1.6% (~1.3-1.5 m/s or ~5 km/h)
                if (
                    3.0 <= dist_ahead <= 28.0
                    and gap_ahead_s <= 0.36
                    and smp["curv"] < 0.0042
                    and not self.is_braking[st]
                ):
                    lat_offset = abs(car.d - car_ahead.d)
                    if lat_offset <= 0.22:
                        align_factor = 1.0 - (lat_offset / 0.22) ** 1.5
                        prox_factor = 1.0 - (gap_ahead_s / 0.36)
                        slipstream_bonus = prox_factor * align_factor * 0.016

                # Dirty air downforce deficit in cornering wake
                if gap_ahead_s < 0.85 and smp["curv"] > 0.0065:
                    dirty_air_loss = (1.0 - gap_ahead_s / 0.85) * 0.032
        else:
            car.tailing_timer = max(0.0, car.tailing_timer - dt * 0.4)'''

    assert old_tow in content, "old_tow target not found in sim/physics.py"
    content = content.replace(old_tow, new_tow, 1)

    # 2. Top speed multipliers patch (prevent excessive speed boost)
    old_top = '''        if has_active_aero and car.aero_mode == "STRAIGHT":
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
            target_v = min(max(target_v, 82.0), top_cap)'''

    new_top = '''        if has_active_aero and car.aero_mode == "STRAIGHT":
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
            target_v = min(max(target_v, 82.0), top_cap)'''

    assert old_top in content, "old_top target not found in sim/physics.py"
    content = content.replace(old_top, new_top, 1)

    # 3. Maneuver selection patch: Divebomb only in hairpins and corners!
    old_man = '''        # Lap 1 opening sector: pack is compressed 22-wide; drivers avoid reckless divebombs and hold clean racing line
        t2_s = self.track.corners[1]["s_m"] if len(self.track.corners) > 1 else 600.0
        if attacker.lap == 1 and attacker.total_dist < t2_s:
            maneuver = "SLIPSTREAM"
            target_d = -0.68 * ins if defender.d * ins > 0.0 else 0.68 * ins
            maneuver_base = -0.15
        elif smp["straight_mode"] or curv < 0.0052:
            maneuver = "SLIPSTREAM"
            target_d = -0.74 * ins
            maneuver_base = 0.22
        elif is_braking_zone:
            if def_covers_inside:
                if attacker.skills["racecraft"] >= 88 and random.random() < 0.42:
                    maneuver = "DUMMY"
                    target_d = -0.78 * ins if defender.d * ins > 0.05 else 0.78 * ins
                    maneuver_base = 0.08
                elif self.track.track_width_m >= 13.4 or random.random() < 0.58:
                    maneuver = "OUTSIDE"
                    target_d = -0.80 * ins
                    maneuver_base = -0.12 + (self.track.track_width_m - 13.0) * 0.10
                else:
                    maneuver = "DIVEBOMB"
                    target_d = 0.82 * ins if defender.d * ins < 0.15 else -0.80 * ins
                    maneuver_base = -0.06
            else:
                maneuver = "DIVEBOMB"
                target_d = 0.78 * ins
                maneuver_base = 0.16
        else:
            if random.random() < 0.54:
                maneuver = "SWITCHBACK"
                target_d = -0.76 * ins if defender.d * ins > 0.05 else 0.76 * ins
                maneuver_base = 0.04
            else:
                maneuver = "OUTSIDE"
                target_d = -0.78 * ins
                maneuver_base = -0.14 + (self.track.track_width_m - 13.0) * 0.10'''

    new_man = '''        # Distance to nearest corner and corner characteristics
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
                maneuver_base = 0.22
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
                    maneuver_base = -0.14 + (self.track.track_width_m - 13.0) * 0.10'''

    assert old_man in content, "old_man target not found in sim/physics.py"
    content = content.replace(old_man, new_man, 1)

    # 4. Radio dispatch pass maneuver
    old_radio_call = '''                    # Trigger event-driven team radio for overtaken driver or overtaker
                    self.radio_dispatcher.trigger_overtake_event(
                        overtaker=c,
                        overtaken=passed,
                        new_p=new_p,
                        turn=turn,
                        event_cb=event_cb,
                        clock=self.race_clock,
                    )'''

    new_radio_call = '''                    # Trigger event-driven team radio for overtaken driver or overtaker
                    self.radio_dispatcher.trigger_overtake_event(
                        overtaker=c,
                        overtaken=passed,
                        new_p=new_p,
                        turn=turn,
                        event_cb=event_cb,
                        clock=self.race_clock,
                        maneuver=getattr(c, "maneuver", ""),
                    )'''

    assert old_radio_call in content, "old_radio_call target not found in sim/physics.py"
    content = content.replace(old_radio_call, new_radio_call, 1)

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("Successfully patched sim/physics.py")

def patch_radio():
    path = os.path.join("sim", "radio.py")
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Update trigger_overtaken signature and available radios filter
    old_overtaken = '''    def trigger_overtaken(
        self,
        overtaken_car: Any,
        overtaker_car: Any,
        turn: int,
        event_cb,
        clock: float = 0.0,
    ) -> None:
        """Triggered when a driver is passed by an opponent."""
        if not self._can_broadcast(overtaken_car, clock, min_global_cd=2.0, min_driver_cd=12.0):
            return
        self._mark_broadcast(overtaken_car, clock)

        drv_id = getattr(overtaken_car, "driver_id", "").lower()
        iconic_quotes = DRIVER_OVERTAKEN_RADIOS.get(drv_id, [])

        if iconic_quotes and random.random() < 0.75:
            quote = random.choice(iconic_quotes)
            quote_formatted = quote.format(turn=turn) if "{turn}" in quote else quote
            msg = f"TEAM RADIO (#{overtaken_car.number} {overtaken_car.code}): '{quote_formatted}'"
        else:
            tpl = random.choice(OVERTAKEN_RADIOS)'''

    new_overtaken = '''    def trigger_overtaken(
        self,
        overtaken_car: Any,
        overtaker_car: Any,
        turn: int,
        event_cb,
        clock: float = 0.0,
        maneuver: str = "",
    ) -> None:
        """Triggered when a driver is passed by an opponent."""
        if not self._can_broadcast(overtaken_car, clock, min_global_cd=2.0, min_driver_cd=12.0):
            return
        self._mark_broadcast(overtaken_car, clock)

        drv_id = getattr(overtaken_car, "driver_id", "").lower()
        iconic_quotes = DRIVER_OVERTAKEN_RADIOS.get(drv_id, [])

        if iconic_quotes and random.random() < 0.75:
            quote = random.choice(iconic_quotes)
            quote_formatted = quote.format(turn=turn) if "{turn}" in quote else quote
            msg = f"TEAM RADIO (#{overtaken_car.number} {overtaken_car.code}): '{quote_formatted}'"
        else:
            # Divebomb complaints only trigger if the maneuver was an authentic divebomb
            available_radios = [
                tpl for tpl in OVERTAKEN_RADIOS
                if "divebomb" not in tpl.lower() or maneuver == "DIVEBOMB"
            ]
            tpl = random.choice(available_radios)'''

    assert old_overtaken in content, "old_overtaken target not found in sim/radio.py"
    content = content.replace(old_overtaken, new_overtaken, 1)

    # 2. Update trigger_overtake_event signature and calls
    old_event = '''    def trigger_overtake_event(
        self,
        overtaker: Any,
        overtaken: Any,
        new_p: int,
        turn: int,
        event_cb,
        clock: float = 0.0,
    ) -> None:
        """Dispatches an authentic radio response from either the overtaken driver or overtaker."""
        # Favor the overtaken driver expressing frustration or pit wall reassurance ~55% of the time
        if random.random() < 0.55:
            if self._can_broadcast(overtaken, clock, min_global_cd=2.0, min_driver_cd=12.0):
                self.trigger_overtaken(overtaken, overtaker, turn, event_cb, clock)
                return
            if self._can_broadcast(overtaker, clock, min_global_cd=2.0, min_driver_cd=12.0):
                self.trigger_overtake_success(overtaker, overtaken, new_p, turn, event_cb, clock)
                return
        else:
            if self._can_broadcast(overtaker, clock, min_global_cd=2.0, min_driver_cd=12.0):
                self.trigger_overtake_success(overtaker, overtaken, new_p, turn, event_cb, clock)
                return
            if self._can_broadcast(overtaken, clock, min_global_cd=2.0, min_driver_cd=12.0):
                self.trigger_overtaken(overtaken, overtaker, turn, event_cb, clock)
                return'''

    new_event = '''    def trigger_overtake_event(
        self,
        overtaker: Any,
        overtaken: Any,
        new_p: int,
        turn: int,
        event_cb,
        clock: float = 0.0,
        maneuver: str = "",
    ) -> None:
        """Dispatches an authentic radio response from either the overtaken driver or overtaker."""
        # Favor the overtaken driver expressing frustration or pit wall reassurance ~55% of the time
        if random.random() < 0.55:
            if self._can_broadcast(overtaken, clock, min_global_cd=2.0, min_driver_cd=12.0):
                self.trigger_overtaken(overtaken, overtaker, turn, event_cb, clock, maneuver=maneuver)
                return
            if self._can_broadcast(overtaker, clock, min_global_cd=2.0, min_driver_cd=12.0):
                self.trigger_overtake_success(overtaker, overtaken, new_p, turn, event_cb, clock)
                return
        else:
            if self._can_broadcast(overtaker, clock, min_global_cd=2.0, min_driver_cd=12.0):
                self.trigger_overtake_success(overtaker, overtaken, new_p, turn, event_cb, clock)
                return
            if self._can_broadcast(overtaken, clock, min_global_cd=2.0, min_driver_cd=12.0):
                self.trigger_overtaken(overtaken, overtaker, turn, event_cb, clock, maneuver=maneuver)
                return'''

    assert old_event in content, "old_event target not found in sim/radio.py"
    content = content.replace(old_event, new_event, 1)

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("Successfully patched sim/radio.py")

if __name__ == "__main__":
    patch_physics()
    patch_radio()

