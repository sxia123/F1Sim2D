import sys
import os

def patch_physics():
    path = os.path.join("sim", "physics.py")
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Tow calculation: reduce peak speed bonus from 0.016 to 0.008 (max ~2.7 km/h, authentic subtle tow)
    # and narrow the wake window (<= 20m, <= 0.28s, lateral <= 0.16)
    old_tow = '''                # Tow Balance: Only occurs if RIGHT BEHIND the car ahead on a straight
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
                        slipstream_bonus = prox_factor * align_factor * 0.016'''

    new_tow = '''                # Tow Balance: Only occurs if RIGHT BEHIND the car ahead on a straight
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
                        slipstream_bonus = prox_factor * align_factor * 0.008'''

    assert old_tow in content, "old_tow target not found in sim/physics.py"
    content = content.replace(old_tow, new_tow, 1)

    # 2. Rebalance passing lane speed boost in battles (prevent unrealistic slingshot pull)
    old_pass_boost = '''                            st_c = self.track.sample(c.s)["station"]
                            v_env_c = self.v_env[st_c]
                            if c.v < v_env_c:
                                c.v = min(v_env_c, c.v + 12.0 * dt)
                            if tgt.v > c.v - 1.2:
                                tgt.v = max(4.0, tgt.v - 8.0 * dt)'''

    new_pass_boost = '''                            st_c = self.track.sample(c.s)["station"]
                            v_env_c = self.v_env[st_c]
                            if c.v < v_env_c and c.v < tgt.v + 1.2:
                                c.v = min(v_env_c, c.v + 3.2 * dt)
                            if c.total_dist > tgt.total_dist and tgt.v > c.v:
                                tgt.v = max(4.0, tgt.v - 2.4 * dt)'''

    assert old_pass_boost in content, "old_pass_boost target not found in sim/physics.py"
    content = content.replace(old_pass_boost, new_pass_boost, 1)

    # 3. Reduce SLIPSTREAM base logit advantage
    old_slip_logit = '''        elif not is_hairpin and not is_corner:
            # NOT in a hairpin or corner: Divebomb is STRICTLY PROHIBITED.
            # Straights, straight approach, kinks, or high-speed sweeps:
            if smp.get("straight_mode", False) or curv < 0.0055:
                maneuver = "SLIPSTREAM"
                target_d = -0.74 * ins
                maneuver_base = 0.22'''

    new_slip_logit = '''        elif not is_hairpin and not is_corner:
            # NOT in a hairpin or corner: Divebomb is STRICTLY PROHIBITED.
            # Straights, straight approach, kinks, or high-speed sweeps:
            if smp.get("straight_mode", False) or curv < 0.0055:
                maneuver = "SLIPSTREAM"
                target_d = -0.74 * ins
                maneuver_base = 0.06'''

    assert old_slip_logit in content, "old_slip_logit target not found in sim/physics.py"
    content = content.replace(old_slip_logit, new_slip_logit, 1)

    # 4. Crash rate reduction: reduce solo crash risk and terminal barrier DNF rate
    old_crash_risk = '''        # Reduced base crash risk from 0.00028 to 0.00011 (less arbitrary random retirements)
        risk = (
            0.00011
            * push_mult
            * (1.25 - sk["consistency"] / 110.0)
            * (3.2 if slick_in_rain else (1.35 if self.wetness > 0.35 else 1.0))
            * (1.9 if car.tire_wear > 0.76 else 1.0)
            * dt
        )
        if smp["curv"] > 0.012 and random.random() < risk:
            turn = self.track.nearest_corner(car.s)
            # Reduced terminal barrier impact DNF rate from 20%/34% to 6%/12% (most spins recover or clip wing)
            if random.random() < (0.12 if self.track.id in ("monaco", "saudi", "azerbaijan", "singapore", "canada") else 0.06):
                car.dnf = True'''

    new_crash_risk = '''        # Base crash risk tuned to authentic F1 low attrition (0.000045)
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
                car.dnf = True'''

    assert old_crash_risk in content, "old_crash_risk target not found in sim/physics.py"
    content = content.replace(old_crash_risk, new_crash_risk, 1)

    # 5. Non-terminal spin damage probability reduction: 45% -> 20%
    old_spin_dmg = '''                if random.random() < 0.45:
                    car.wing_damage = min(0.75, car.wing_damage + random.uniform(0.24, 0.48))'''

    new_spin_dmg = '''                if random.random() < 0.20:
                    car.wing_damage = min(0.75, car.wing_damage + random.uniform(0.24, 0.48))'''

    assert old_spin_dmg in content, "old_spin_dmg target not found in sim/physics.py"
    content = content.replace(old_spin_dmg, new_spin_dmg, 1)

    # 6. Mechanical failure rate tuned further: 0.000032 -> 0.000018
    old_mech = '''        mech_prob = (
            (0.000032 * max(0.18, 1.35 - rel_lvl * 0.12) * pace_factor * dt)
            if self.race_clock > 35.0
            else 0.0
        )'''

    new_mech = '''        mech_prob = (
            (0.000018 * max(0.16, 1.30 - rel_lvl * 0.12) * pace_factor * dt)
            if self.race_clock > 45.0
            else 0.0
        )'''

    assert old_mech in content, "old_mech target not found in sim/physics.py"
    content = content.replace(old_mech, new_mech, 1)

    # 7. Collision contact incident chance during battle: 0.015 -> 0.004
    old_inc = '''                            inc_chance = 0.015 * max(0.2, 1.15 - attacker.skills["consistency"] / 100.0)'''
    new_inc = '''                            inc_chance = 0.004 * max(0.2, 1.15 - attacker.skills["consistency"] / 100.0)'''

    assert old_inc in content, "old_inc target not found in sim/physics.py"
    content = content.replace(old_inc, new_inc, 1)

    # 8. Collision roll threshold: 0.96 -> 0.985 (only 1.5% of contact causes terminal DNF)
    old_coll_roll = '''        elif roll < 0.96:'''
    new_coll_roll = '''        elif roll < 0.985:'''

    assert old_coll_roll in content, "old_coll_roll target not found in sim/physics.py"
    content = content.replace(old_coll_roll, new_coll_roll, 1)

    # 9. In RaceSession.set_starting_compound, also synchronize next_compound
    old_set_start = '''    def set_starting_compound(self, driver_id: str, compound: str) -> bool:
        if compound in TIRE_COMPOUNDS and driver_id in self.cars_by_id:
            car = self.cars_by_id[driver_id]
            car.compound = compound
            car.compounds_used = {compound}
            car.tire_age_laps = 0
            car.tire_wear = 0.01
            self.starting_compounds[driver_id] = compound
            return True
        return False'''

    new_set_start = '''    def set_starting_compound(self, driver_id: str, compound: str) -> bool:
        if compound in TIRE_COMPOUNDS and driver_id in self.cars_by_id:
            car = self.cars_by_id[driver_id]
            car.compound = compound
            car.next_compound = compound
            car.compounds_used = {compound}
            car.tire_age_laps = 0
            car.tire_wear = 0.01
            self.starting_compounds[driver_id] = compound
            return True
        return False'''

    assert old_set_start in content, "old_set_start target not found in sim/physics.py"
    content = content.replace(old_set_start, new_set_start, 1)

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("Successfully patched sim/physics.py")

def patch_championship():
    path = os.path.join("sim", "championship.py")
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Increase GRID_WALK duration to 18 seconds and pause speed to 1x during grid formation
    old_grid_walk = '''        self.phase = "GRID_WALK"
        self.phase_timer = 8.0'''

    new_grid_walk = '''        self.phase = "GRID_WALK"
        self.phase_timer = 18.0
        self.sim_speed = 1.0'''

    assert old_grid_walk in content, "old_grid_walk target not found in sim/championship.py"
    content = content.replace(old_grid_walk, new_grid_walk, 1)

    # 2. In set_starting_compound, ensure car.next_compound is also set and grid cars update
    old_champ_comp = '''            if self.race_session:
                self.race_session.set_starting_compound(driver_id, compound)
            self._push_event("RADIO", f"GRID STRATEGY: #{drv_num} {drv_code} confirmed starting on {compound} tyres!")
            self._save_state()
            return {"ok": True, "driver_id": driver_id, "compound": compound}'''

    new_champ_comp = '''            if self.race_session:
                self.race_session.set_starting_compound(driver_id, compound)
                car = self.race_session.cars_by_id.get(driver_id)
                if car:
                    car.next_compound = compound
            self._push_event("RADIO", f"GRID STRATEGY: #{drv_num} {drv_code} confirmed starting on {compound} tyres!")
            self._save_state()
            return {"ok": True, "driver_id": driver_id, "compound": compound}'''

    assert old_champ_comp in content, "old_champ_comp target not found in sim/championship.py"
    content = content.replace(old_champ_comp, new_champ_comp, 1)

    # 3. In pit_wall_command, allow updating start_compound during grid walk or race start
    old_pw_comp = '''            if "start_compound" in cmd and cmd["start_compound"] in TIRE_COMPOUNDS:
                comp = cmd["start_compound"]
                self.starting_compounds[driver_id] = comp
                if self.phase in ("GRID_WALK", "PRE_WEEKEND") or (self.race_session and self.race_session.lights_countdown > 0):
                    car.compound = comp
                    car.compounds_used = {comp}
                    car.tire_age_laps = 0
                    car.tire_wear = 0.01
                    self._push_event("RADIO", f"GRID CALL: #{car.number} {car.code} fitted with {comp} tyres for race start!")'''

    new_pw_comp = '''            if "start_compound" in cmd and cmd["start_compound"] in TIRE_COMPOUNDS:
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
                    self._push_event("RADIO", f"GRID STRATEGY: #{car.number} {car.code} starting tyres switched to {comp}!")'''

    assert old_pw_comp in content, "old_pw_comp target not found in sim/championship.py"
    # Also remove the adjacent separate "next_compound" check if replacing
    target_pw_block = old_pw_comp + '\n            if "next_compound" in cmd and cmd["next_compound"] in TIRE_COMPOUNDS:\n                car.next_compound = cmd["next_compound"]'
    assert target_pw_block in content, "target_pw_block target not found in sim/championship.py"
    content = content.replace(target_pw_block, new_pw_comp, 1)

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("Successfully patched sim/championship.py")

def patch_app_js():
    path = os.path.join("public", "app.js")
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Update isPreRace definition to cover GRID_WALK, PRE_WEEKEND, SPRINT_RACE start, and lights sequence
    old_is_pre = '''        const isPreRace = tick.phase === "GRID_WALK" || (tick.phase === "RACE" && tick.lights > 0);
        const isRace = (tick.phase === "RACE" || tick.phase === "SPRINT_RACE") && !c.dnf;
        const dis = (isRace || isPreRace) ? "" : "disabled";'''

    new_is_pre = '''        const isPreRace = tick.phase === "GRID_WALK"
          || tick.phase === "PRE_WEEKEND"
          || tick.flag === "GRID"
          || tick.flag === "LIGHTS"
          || ((tick.phase === "RACE" || tick.phase === "SPRINT_RACE") && (tick.lights > 0 || (c.lap <= 1 && c.kph < 25)));
        const isRace = (tick.phase === "RACE" || tick.phase === "SPRINT_RACE") && !c.dnf;
        const dis = (isRace || isPreRace) ? "" : "disabled";'''

    assert old_is_pre in content, "old_is_pre target not found in public/app.js"
    content = content.replace(old_is_pre, new_is_pre, 1)

    # 2. In pointerdown handler for start_comp, give immediate local feedback and toast
    old_ptr = '''      else if (cmd === "start_comp") {
        await this.apiPost("/api/set_starting_compound", { driver_id: driverId, compound: val });
        this.lastDomSyncMs = 0;
        return;
      }'''

    new_ptr = '''      else if (cmd === "start_comp") {
        const res = await this.apiPost("/api/set_starting_compound", { driver_id: driverId, compound: val });
        if (res.ok) {
          this.showToast(`START TYRE CONFIRMED: #${driverId.toUpperCase()} on ${val} tyres!`);
          if (this.liveTick && this.liveTick.cars) {
            const myCar = this.liveTick.cars.find(c => c.id === driverId);
            if (myCar) {
              myCar.comp = val;
              myCar.ncomp = val;
              this.renderPitWallCards(this.liveTick);
            }
          }
        }
        this.lastDomSyncMs = 0;
        return;
      }'''

    assert old_ptr in content, "old_ptr target not found in public/app.js"
    content = content.replace(old_ptr, new_ptr, 1)

    # 3. Update GRID_WALK banner overlay to instruct player on tyre selection
    old_banner = '''            <strong style="color:#ffffff;font-style:italic;letter-spacing:0.6px">${tick.phase === "GRID_WALK" ? "STARTING GRID LOCKED — FORMATION PROCEDURE" : `${tick.circuit_name.toUpperCase()}`}</strong>'''

    new_banner = '''            <strong style="color:#ffffff;font-style:italic;letter-spacing:0.6px">${tick.phase === "GRID_WALK" ? "STARTING GRID — CHOOSE TYRE COMPOUND ON PIT WALL" : `${tick.circuit_name.toUpperCase()}`}</strong>'''

    if old_banner in content:
        content = content.replace(old_banner, new_banner, 1)
    else:
        alt_b = old_banner.replace("—", "â€”")
        assert alt_b in content, "banner target not found in public/app.js"
        content = content.replace(alt_b, new_banner, 1)

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("Successfully patched public/app.js")

if __name__ == "__main__":
    patch_physics()
    patch_championship()
    patch_app_js()

