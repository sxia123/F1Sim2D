with open("sim/championship.py", "r", encoding="utf-8") as f:
    text = f.read()

target = """                    elif car.pace_mode == "CONSERVE" and old_pace != car.pace_mode:
                        self.race_session.radio_dispatcher.trigger_conserve_mode(
                            car, event_cb=self._push_event, clock=clk, turn=turn
                        )"""

replacement = """                    elif car.pace_mode == "CONSERVE" and old_pace != car.pace_mode:
                        self.race_session.radio_dispatcher.trigger_conserve_mode(
                            car, event_cb=self._push_event, clock=clk, turn=turn, is_pit_wall=True
                        )"""

assert target in text, "Could not find target in championship.py"
text = text.replace(target, replacement, 1)

with open("sim/championship.py", "w", encoding="utf-8") as f:
    f.write(text)

print("sim/championship.py updated successfully!")

