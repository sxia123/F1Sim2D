from pathlib import Path

# 1. Patch sim/physics.py
p_phys = Path("sim/physics.py")
text_phys = p_phys.read_text(encoding="utf-8")

# Add import
import_target = "from sim.car_geometry import (CAR_LEN_PX,CAR_WID_PX,CAR_HALF_LENGTH,CAR_HALF_WIDTH,"
import_repl = "from sim.radio import RadioDispatcher\nfrom sim.car_geometry import (CAR_LEN_PX,CAR_WID_PX,CAR_HALF_LENGTH,CAR_HALF_WIDTH,"
assert import_target in text_phys, "import_target not found in physics.py"
text_phys = text_phys.replace(import_target, import_repl, 1)

# Add tailing_timer, last_radio_time, radio_box_announced to CarState
car_attr_target = """        self.defense_timer: float = 0.0

        self.planned_pit_lap: int = max(5, int(total_laps * random.uniform(0.38, 0.56)))"""
car_attr_repl = """        self.defense_timer: float = 0.0

        # Team Radio & Tailing Dynamics
        self.tailing_timer: float = 0.0
        self.last_radio_time: float = -99.0
        self.radio_box_announced: bool = False

        self.planned_pit_lap: int = max(5, int(total_laps * random.uniform(0.38, 0.56)))"""
assert car_attr_target in text_phys, "car_attr_target not found in physics.py"
text_phys = text_phys.replace(car_attr_target, car_attr_repl, 1)

# Initialize radio_dispatcher in RaceSession.__init__
rs_init_target = """        self.stewards_queue: list[dict[str, Any]] = []

        self.cars: list[CarState] = []"""
rs_init_repl = """        self.stewards_queue: list[dict[str, Any]] = []
        self.radio_dispatcher = RadioDispatcher()

        self.cars: list[CarState] = []"""
assert rs_init_target in text_phys, "rs_init_target not found in physics.py"
text_phys = text_phys.replace(rs_init_target, rs_init_repl, 1)

# Step radio_dispatcher in RaceSession.step
rs_step_target = """        self._step_weather(dt, event_cb)
        self._step_race_control(dt, event_cb)
        self._step_stewards(dt, event_cb)

        leader = self.standings[0] if self.standings else None"""
rs_step_repl = """        self._step_weather(dt, event_cb)
        self._step_race_control(dt, event_cb)
        self._step_stewards(dt, event_cb)
        self.radio_dispatcher.step(dt, self.race_clock, self.cars, self.track, self.wetness, self.flag_state, event_cb)

        leader = self.standings[0] if self.standings else None"""
assert rs_step_target in text_phys, "rs_step_target not found in physics.py"
text_phys = text_phys.replace(rs_step_target, rs_step_repl, 1)

# Tailing timer in _step_car
tailing_target = """        slipstream_bonus = 0.0
        dirty_air_loss = 0.0
        gap_ahead_s = 99.0
        if car_ahead and not car_ahead.in_pits:
            dist_ahead = (car_ahead.s - car.s) % self.track.length_m
            if 2.0 < dist_ahead < 95.0:
                gap_ahead_s = dist_ahead / max(car.v, 25.0)
                if gap_ahead_s < 0.95:
                    slipstream_bonus = (1.0 - gap_ahead_s / 0.95) * 0.048
                    if smp["curv"] > 0.007:
                        dirty_air_loss = (1.0 - gap_ahead_s / 0.95) * 0.036"""
tailing_repl = """        slipstream_bonus = 0.0
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
            car.tailing_timer = max(0.0, car.tailing_timer - dt * 0.4)"""
assert tailing_target in text_phys, "tailing_target not found in physics.py"
text_phys = text_phys.replace(tailing_target, tailing_repl, 1)

# Box call announcement in _step_car
box_ann_target = """        entry_gap=(self.track.pit_entry_s-prev_s)%self.track.length_m
        if car.box_this_lap and entry_gap <= car.v*dt:"""
box_ann_repl = """        if car.box_this_lap and not car.radio_box_announced and laps_left >= 1:
            car.radio_box_announced = True
            self.radio_dispatcher.trigger_box_call(car, event_cb)

        entry_gap=(self.track.pit_entry_s-prev_s)%self.track.length_m
        if car.box_this_lap and entry_gap <= car.v*dt:"""
assert box_ann_target in text_phys, "box_ann_target not found in physics.py"
text_phys = text_phys.replace(box_ann_target, box_ann_repl, 1)

# Pit exit radio in _step_pit_lane
exit_radio_target = """                event_cb(
                    "PIT",
                    f"PIT OUT: #{car.number} {car.code} ({car.team_short}) rejoins on {car.compound} ({car.last_pit_duration:.2f}s stationary).",
                )"""
exit_radio_repl = """                event_cb(
                    "PIT",
                    f"PIT OUT: #{car.number} {car.code} ({car.team_short}) rejoins on {car.compound} ({car.last_pit_duration:.2f}s stationary).",
                )
                car.radio_box_announced = False
                self.radio_dispatcher.trigger_pit_exit(car, car.last_pit_duration, event_cb)"""
assert exit_radio_target in text_phys, "exit_radio_target not found in physics.py"
text_phys = text_phys.replace(exit_radio_target, exit_radio_repl, 1)

# Fastest lap radio in _advance_car_progress
purple_radio_target = """                    if car.laps_completed >= 2:
                        event_cb("PURPLE", f"FASTEST LAP: {car.code} ({car.team_short}) clocks {_fmt_lap(lap_time)}!")"""
purple_radio_repl = """                    if car.laps_completed >= 2:
                        event_cb("PURPLE", f"FASTEST LAP: {car.code} ({car.team_short}) clocks {_fmt_lap(lap_time)}!")
                        self.radio_dispatcher.trigger_fastest_lap(car, _fmt_lap(lap_time), event_cb)"""
assert purple_radio_target in text_phys, "purple_radio_target not found in physics.py"
text_phys = text_phys.replace(purple_radio_target, purple_radio_repl, 1)

# Contact radio in _on_physical_contact
contact_side_target = """                event_cb(
                    "INCIDENT",
                    f"WHEEL BANGING! Contact between #{c1.number} {c1.code} and #{c2.number} {c2.code} fighting through Turn {turn}!",
                )"""
contact_side_repl = """                event_cb(
                    "INCIDENT",
                    f"WHEEL BANGING! Contact between #{c1.number} {c1.code} and #{c2.number} {c2.code} fighting through Turn {turn}!",
                )
                self.radio_dispatcher.trigger_contact(c1, c2, turn, event_cb, self.race_clock)"""
assert contact_side_target in text_phys, "contact_side_target not found in physics.py"
text_phys = text_phys.replace(contact_side_target, contact_side_repl, 1)

contact_rear_target = """                else:
                    event_cb(
                        "INCIDENT",
                        f"FRONT WING DAMAGE! #{behind.number} {behind.code} misjudges braking and hits the rear of #{ahead.number} {ahead.code} at Turn {turn}!",
                    )"""
contact_rear_repl = """                else:
                    event_cb(
                        "INCIDENT",
                        f"FRONT WING DAMAGE! #{behind.number} {behind.code} misjudges braking and hits the rear of #{ahead.number} {ahead.code} at Turn {turn}!",
                    )
                self.radio_dispatcher.trigger_contact(behind, ahead, turn, event_cb, self.race_clock)"""
assert contact_rear_target in text_phys, "contact_rear_target not found in physics.py"
text_phys = text_phys.replace(contact_rear_target, contact_rear_repl, 1)

p_phys.write_text(text_phys, encoding="utf-8")
print("Successfully patched sim/physics.py with radio system!")

# 2. Patch sim/championship.py event buffer size
p_champ = Path("sim/championship.py")
text_champ = p_champ.read_text(encoding="utf-8")

feed_len_target = "if len(self.event_feed) > 90:\n            self.event_feed = self.event_feed[-90:]"
feed_len_repl = "if len(self.event_feed) > 160:\n            self.event_feed = self.event_feed[-160:]"
assert feed_len_target in text_champ, "feed_len_target not found in championship.py"
text_champ = text_champ.replace(feed_len_target, feed_len_repl, 1)

payload_feed_target = '"events": self.event_feed[-28:],'
payload_feed_repl = '"events": self.event_feed[-60:],'
assert payload_feed_target in text_champ, "payload_feed_target not found in championship.py"
text_champ = text_champ.replace(payload_feed_target, payload_feed_repl, 1)

p_champ.write_text(text_champ, encoding="utf-8")
print("Successfully patched sim/championship.py event buffer!")

