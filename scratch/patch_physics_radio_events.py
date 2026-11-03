with open("sim/physics.py", "r", encoding="utf-8") as f:
    text = f.read().replace("\r\n", "\n")

# 1. CarState initialization of radio event flags
target_car_init = """        # Team Radio & Tailing Dynamics
        self.tailing_timer: float = 0.0
        self.last_radio_time: float = -99.0
        self.radio_box_announced: bool = False"""

repl_car_init = """        # Team Radio & Tailing Dynamics
        self.tailing_timer: float = 0.0
        self.last_radio_time: float = -99.0
        self.radio_box_announced: bool = False
        self.cliff_radio_triggered: bool = False
        self.inlap_push_announced: bool = False"""

assert target_car_init in text, "target_car_init not found"
text = text.replace(target_car_init, repl_car_init, 1)

# 2. Reset flags on pit exit
target_pit_exit = """                car.radio_box_announced = False
                self.radio_dispatcher.trigger_pit_exit(car, car.last_pit_duration, event_cb)"""

repl_pit_exit = """                car.radio_box_announced = False
                car.cliff_radio_triggered = False
                car.inlap_push_announced = False
                self.radio_dispatcher.trigger_pit_exit(car, car.last_pit_duration, event_cb)"""

assert target_pit_exit in text, "target_pit_exit not found"
text = text.replace(target_pit_exit, repl_pit_exit, 1)

# 3. In-lap push mode activation on box call
target_box_call = """        if car.box_this_lap and not car.radio_box_announced and laps_left >= 1:
            car.radio_box_announced = True
            self.radio_dispatcher.trigger_box_call(car, event_cb)"""

repl_box_call = """        if car.box_this_lap and not car.radio_box_announced and laps_left >= 1:
            car.radio_box_announced = True
            self.radio_dispatcher.trigger_box_call(car, event_cb)
            if not getattr(car, "inlap_push_announced", False):
                car.inlap_push_announced = True
                car.pace_mode = "ATTACK"
                turn = self.track.nearest_corner(car.s) if hasattr(self.track, "nearest_corner") else 1
                self.radio_dispatcher.trigger_push_mode(
                    car, "IN-LAP ATTACK", is_pit_wall=True, event_cb=event_cb, clock=self.race_clock, turn=turn
                )"""

assert target_box_call in text, "target_box_call not found"
text = text.replace(target_box_call, repl_box_call, 1)

# 4. Tyre cliff trigger
target_cliff = """        wear = car.tire_wear
        cliff = comp_spec["cliff_wear"]
        if wear <= cliff:
            wear_factor = 1.0 - wear * 0.11
        else:
            wear_factor = (1.0 - cliff * 0.11) - (wear - cliff) * 0.85"""

repl_cliff = """        wear = car.tire_wear
        cliff = comp_spec["cliff_wear"]
        if wear >= cliff and not getattr(car, "cliff_radio_triggered", False) and laps_left >= 2:
            car.cliff_radio_triggered = True
            self.radio_dispatcher.trigger_tyre_cliff(car, event_cb, self.race_clock)

        if wear <= cliff:
            wear_factor = 1.0 - wear * 0.11
        else:
            wear_factor = (1.0 - cliff * 0.11) - (wear - cliff) * 0.85"""

assert target_cliff in text, "target_cliff not found"
text = text.replace(target_cliff, repl_cliff, 1)

# 5. AI dynamic push / conserve mode switching
target_ai_pace = """        fw_grip_factor = 1.0 - car.wing_damage * (0.28 if smp["curv"] > 0.005 else 0.12)"""

repl_ai_pace = """        # AI dynamic push / attack / conserve mode switching based on proximity and tyres
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

        fw_grip_factor = 1.0 - car.wing_damage * (0.28 if smp["curv"] > 0.005 else 0.12)"""

assert target_ai_pace in text, "target_ai_pace not found"
text = text.replace(target_ai_pace, repl_ai_pace, 1)

# 6. Overtake radio event
target_overtake = """            if (
                new_p < old_p
                and new_p <= 10
                and not c.in_pits
                and not c.dnf
                and c.overtake_cooldown <= 0.0
                and self.race_clock > 8.0
            ):
                passed = self.standings[idx + 1]
                if not passed.in_pits and not passed.dnf and passed.spin_timer <= 0.0:
                    c.overtake_cooldown = 7.0
                    ovt_tag = " [OVERTAKE MODE]" if c.overtake_active else ""
                    turn = self.track.nearest_corner(c.s)
                    man_lbl = f" ({c.maneuver})" if c.maneuver else ""
                    event_cb(
                        "OVERTAKE",
                        f"OVERTAKE P{new_p}: #{c.number} {c.code} passes {passed.code} near Turn {turn}{man_lbl}{ovt_tag}!",
                    )"""

repl_overtake = """            if (
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
                    )"""

assert target_overtake in text, "target_overtake not found"
text = text.replace(target_overtake, repl_overtake, 1)

# 7. Safety car triggers
target_sc = """        if mode == "VSC" and self.flag_state != "SC":
            self.flag_state = "VSC"
            self.vsc_timer = random.uniform(16.0, 25.0)
            self.yellow_sector = None
            event_cb("SC", f"VIRTUAL SAFETY CAR DEPLOYED: {reason}. Maintain VSC delta!")
        else:
            self.flag_state = "SC"
            self.sc_laps_remaining = 2
            self.sc_in_this_lap = False
            self.sc_s = (leader.s + 140.0) % self.track.length_m
            self._update_sc_xy()
            self.yellow_sector = None
            event_cb("SC", f"SAFETY CAR DEPLOYED: {reason}! Pack bunching up behind the Safety Car.")"""

repl_sc = """        if mode == "VSC" and self.flag_state != "SC":
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
            self.radio_dispatcher.trigger_safety_car("SC", reason, event_cb, self.race_clock, self.standings)"""

assert target_sc in text, "target_sc not found"
text = text.replace(target_sc, repl_sc, 1)

# 8. SC in this lap
target_sc_in = """                if self.sc_laps_remaining == 1 and not self.sc_in_this_lap:
                    self.sc_in_this_lap = True
                    event_cb("RACE_CONTROL", "SAFETY CAR IN THIS LAP! Leader controls the pace to the Line.")"""

repl_sc_in = """                if self.sc_laps_remaining == 1 and not self.sc_in_this_lap:
                    self.sc_in_this_lap = True
                    event_cb("RACE_CONTROL", "SAFETY CAR IN THIS LAP! Leader controls the pace to the Line.")
                    self.radio_dispatcher.trigger_safety_car_in(event_cb, self.race_clock, self.standings)"""

assert target_sc_in in text, "target_sc_in not found"
text = text.replace(target_sc_in, repl_sc_in, 1)

# 9. Weather shift
target_weather = """                if prev_rain < 0.10 and self.rain_intensity >= 0.18:
                    event_cb("WEATHER", "WEATHER RADAR: Rain front arriving over the circuit! Surface grip dropping.")"""

repl_weather = """                if prev_rain < 0.10 and self.rain_intensity >= 0.18:
                    event_cb("WEATHER", "WEATHER RADAR: Rain front arriving over the circuit! Surface grip dropping.")
                    self.radio_dispatcher.trigger_weather_transition(
                        self.rain_intensity, self.wetness, event_cb, self.race_clock, self.standings, self.track
                    )"""

assert target_weather in text, "target_weather not found"
text = text.replace(target_weather, repl_weather, 1)

# 10. Spin triggers
target_spin1 = """                car.spin_timer = random.uniform(3.2, 5.5)
                car.smoke = 2.8
                car.tire_wear = min(0.98, car.tire_wear + 0.06)"""

repl_spin1 = """                car.spin_timer = random.uniform(3.2, 5.5)
                car.smoke = 2.8
                car.tire_wear = min(0.98, car.tire_wear + 0.06)
                self.radio_dispatcher.trigger_spin(car, turn, event_cb, self.race_clock)"""

assert target_spin1 in text, "target_spin1 not found"
text = text.replace(target_spin1, repl_spin1, 1)

target_spin2 = """            victim.spin_timer = random.uniform(2.8, 4.5)
            victim.spin_omega = random.choice([-5.8, 5.8]) * random.uniform(0.85, 1.25)
            victim.spin_lateral_dir = 1.0 if victim.d >= 0.0 else -1.0
            victim.spin_rebound_done = False
            victim.smoke = 2.4"""

repl_spin2 = """            victim.spin_timer = random.uniform(2.8, 4.5)
            victim.spin_omega = random.choice([-5.8, 5.8]) * random.uniform(0.85, 1.25)
            victim.spin_lateral_dir = 1.0 if victim.d >= 0.0 else -1.0
            victim.spin_rebound_done = False
            victim.smoke = 2.4
            self.radio_dispatcher.trigger_spin(victim, turn, event_cb, self.race_clock)"""

assert target_spin2 in text, "target_spin2 not found"
text = text.replace(target_spin2, repl_spin2, 1)

target_spin3 = """                if delta_v > 8.5 and random.random() < 0.40:
                    ahead.spin_timer = random.uniform(2.8, 4.2)
                    ahead.spin_omega = random.choice([-5.8, 5.8]) * random.uniform(0.85, 1.25)
                    ahead.spin_lateral_dir = 1.0 if ahead.d >= 0.0 else -1.0
                    ahead.spin_rebound_done = False
                    ahead.smoke = 2.8"""

repl_spin3 = """                if delta_v > 8.5 and random.random() < 0.40:
                    ahead.spin_timer = random.uniform(2.8, 4.2)
                    ahead.spin_omega = random.choice([-5.8, 5.8]) * random.uniform(0.85, 1.25)
                    ahead.spin_lateral_dir = 1.0 if ahead.d >= 0.0 else -1.0
                    ahead.spin_rebound_done = False
                    ahead.smoke = 2.8
                    self.radio_dispatcher.trigger_spin(ahead, turn, event_cb, self.race_clock)"""

assert target_spin3 in text, "target_spin3 not found"
text = text.replace(target_spin3, repl_spin3, 1)

# 11. Race win radio
target_win = """        if leader.finished:
            self.post_finish_timer += dt"""

repl_win = """        if leader.finished:
            if not getattr(self, "win_radio_triggered", False):
                self.win_radio_triggered = True
                self.radio_dispatcher.trigger_race_win(leader, event_cb, self.race_clock)
            self.post_finish_timer += dt"""

assert target_win in text, "target_win not found"
text = text.replace(target_win, repl_win, 1)

with open("sim/physics.py", "w", encoding="utf-8") as f:
    f.write(text)

print("sim/physics.py patched successfully with all event-driven radio triggers!")

