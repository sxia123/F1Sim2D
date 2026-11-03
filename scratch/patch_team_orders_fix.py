with open("sim/championship.py", "r", encoding="utf-8") as f:
    champ_code = f.read().replace("\r\n", "\n")

target_champ_order = """            if "team_order" in cmd and cmd["team_order"] in ("FREE", "HOLD", "YIELD"):
                car.team_order = cmd["team_order"]
                if car.team_order == "YIELD":
                    self._push_event("RADIO", f"TEAM ORDERS RADIO ({car.team_short}): #{car.number} {car.code} instructed to let teammate pass.")"""

repl_champ_order = """            if "team_order" in cmd and cmd["team_order"] in ("FREE", "HOLD", "YIELD", "SWAP"):
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
                    self._push_event("RADIO", f"TEAM ORDERS RADIO ({car.team_short}): #{car.number} {car.code} instructed free to race.")"""

assert target_champ_order in champ_code, "target_champ_order not found in sim/championship.py"
champ_code = champ_code.replace(target_champ_order, repl_champ_order, 1)

with open("sim/championship.py", "w", encoding="utf-8") as f:
    f.write(champ_code)

print("sim/championship.py patched successfully!")

with open("sim/physics.py", "r", encoding="utf-8") as f:
    phys_code = f.read().replace("\r\n", "\n")

# 1. CarState initialization
target_carstate = """        self.team_order: str = "FREE\""""
repl_carstate = """        self.team_order: str = "FREE"
        self.swap_target_id: str | None = None
        self.swap_pass_id: str | None = None"""
assert target_carstate in phys_code, "target_carstate not found"
phys_code = phys_code.replace(target_carstate, repl_carstate, 1)

# 2. _lane_selection: wants_pass
target_wants_pass = """            wants_pass = (
                allow_passing
                and not (c.team_id == nearest_ahead.team_id and c.team_order == "HOLD")
                and (c.v > nearest_ahead.v + 0.35 or c.maneuver_pass_timer > 0.0 or c.battle_with == nearest_ahead.driver_id)
            )"""

repl_wants_pass = """            is_team_yield = (c.team_id == nearest_ahead.team_id and getattr(nearest_ahead, "team_order", "") == "YIELD")
            wants_pass = (
                allow_passing
                and not (c.team_id == nearest_ahead.team_id and c.team_order == "HOLD")
                and (
                    c.v > nearest_ahead.v + 0.35
                    or c.maneuver_pass_timer > 0.0
                    or c.battle_with == nearest_ahead.driver_id
                    or is_team_yield
                )
            )"""
assert target_wants_pass in phys_code, "target_wants_pass not found"
phys_code = phys_code.replace(target_wants_pass, repl_wants_pass, 1)

# 3. _lane_selection: is_blue_yield and is_passing
target_blue_yield = """                    is_blue_yield = (c.lap > o.lap or getattr(o, "blue_flag", False))
                    req_lat = CAR_WID_PX * 0.70 if is_blue_yield else CAR_WID_PX * 0.84
                    is_passing = (
                        c.maneuver_pass_timer > 0.0
                        or getattr(o, "maneuver_pass_timer", 0.0) > 0.0
                        or c.maneuver_timer > 0.0
                    )"""

repl_blue_yield = """                    is_team_swap = (c.team_id == o.team_id and getattr(o, "team_order", "") == "YIELD")
                    is_blue_yield = (c.lap > o.lap or getattr(o, "blue_flag", False) or is_team_swap)
                    req_lat = CAR_WID_PX * 0.62 if is_blue_yield else CAR_WID_PX * 0.84
                    is_passing = (
                        c.maneuver_pass_timer > 0.0
                        or getattr(o, "maneuver_pass_timer", 0.0) > 0.0
                        or c.maneuver_timer > 0.0
                        or is_team_swap
                    )"""
assert target_blue_yield in phys_code, "target_blue_yield not found"
phys_code = phys_code.replace(target_blue_yield, repl_blue_yield, 1)

# 4. _step_car: YIELD throttle lift & swap completion
target_phys_yield = """        if car.team_order == "YIELD":
            teammate = next(
                (c for c in self.standings if c.team_id == car.team_id and c.driver_id != car.driver_id and not c.dnf),
                None,
            )
            if teammate and teammate.pos == car.pos + 1:
                dist_tm = (car.s - teammate.s) % self.track.length_m
                if dist_tm < 65.0 and smp["curv"] < 0.008:
                    target_v = min(target_v, 68.0)
                    car.target_d = 0.72
                if teammate.pos < car.pos:
                    car.team_order = "FREE\""""

repl_phys_yield = """        # Team Order: YIELD / SWAP Position to Teammate
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
                        target_v = min(target_v, max(36.0, teammate.v * 0.82))"""
assert target_phys_yield in phys_code, "target_phys_yield not found"
phys_code = phys_code.replace(target_phys_yield, repl_phys_yield, 1)

# 5. _step_car: collision avoidance in_active_pass
target_active_pass = """            in_active_pass = (
                car.maneuver_pass_timer > 0.0
                or getattr(car_ahead, "maneuver_pass_timer", 0.0) > 0.0
                or car.battle_with == car_ahead.driver_id
                or is_alongside
            )"""

repl_active_pass = """            in_active_pass = (
                car.maneuver_pass_timer > 0.0
                or getattr(car_ahead, "maneuver_pass_timer", 0.0) > 0.0
                or car.battle_with == car_ahead.driver_id
                or is_alongside
                or (car.team_id == car_ahead.team_id and getattr(car_ahead, "team_order", "") == "YIELD")
            )"""
assert target_active_pass in phys_code, "target_active_pass not found"
phys_code = phys_code.replace(target_active_pass, repl_active_pass, 1)

# 6. _resolve_multi_lane_battles: defender YIELD handling
target_battle_hold = """            if attacker.team_id == defender.team_id and attacker.team_order == "HOLD":
                if attacker.v > defender.v * 0.995:
                    attacker.v = max(defender.v * 0.995, attacker.v - 22.0 * dt)
                continue"""

repl_battle_hold = """            if attacker.team_id == defender.team_id:
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
                    continue"""
assert target_battle_hold in phys_code, "target_battle_hold not found"
phys_code = phys_code.replace(target_battle_hold, repl_battle_hold, 1)

with open("sim/physics.py", "w", encoding="utf-8") as f:
    f.write(phys_code)

print("sim/physics.py patched successfully with cooperative team order swap mechanics!")

