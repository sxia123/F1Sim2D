with open("sim/radio.py", "r", encoding="utf-8") as f:
    text = f.read()

target = """    def trigger_push_mode(
        self,
        car: Any,
        mode_name: str,
        is_pit_wall: bool,
        event_cb,
        clock: float = 0.0,
        turn: int = 1,
    ) -> None:
        \"\"\"Triggered when driver or pit wall activates Push / Attack / Max / Boost mode.\"\"\"
        if not self._can_broadcast(car, clock, min_global_cd=1.8, min_driver_cd=10.0):
            return"""

replacement = """    def trigger_push_mode(
        self,
        car: Any,
        mode_name: str,
        is_pit_wall: bool,
        event_cb,
        clock: float = 0.0,
        turn: int = 1,
    ) -> None:
        \"\"\"Triggered when driver or pit wall activates Push / Attack / Max / Boost mode.\"\"\"
        if not is_pit_wall and not self._can_broadcast(car, clock, min_global_cd=1.8, min_driver_cd=10.0):
            return"""

assert target in text, "Could not find target in radio.py"
text = text.replace(target, replacement, 1)

target2 = """    def trigger_conserve_mode(
        self,
        car: Any,
        event_cb,
        clock: float = 0.0,
        turn: int = 1,
    ) -> None:
        \"\"\"Triggered when driver or pit wall activates Conserve / Harvest mode.\"\"\"
        if not self._can_broadcast(car, clock, min_global_cd=2.5, min_driver_cd=16.0):
            return"""

replacement2 = """    def trigger_conserve_mode(
        self,
        car: Any,
        event_cb,
        clock: float = 0.0,
        turn: int = 1,
        is_pit_wall: bool = False,
    ) -> None:
        \"\"\"Triggered when driver or pit wall activates Conserve / Harvest mode.\"\"\"
        if not is_pit_wall and not self._can_broadcast(car, clock, min_global_cd=2.5, min_driver_cd=16.0):
            return"""

assert target2 in text, "Could not find target2 in radio.py"
text = text.replace(target2, replacement2, 1)

with open("sim/radio.py", "w", encoding="utf-8") as f:
    f.write(text)

print("sim/radio.py updated successfully!")

