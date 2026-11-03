with open("sim/championship.py", "r", encoding="utf-8") as f:
    champ_code = f.read().replace("\r\n", "\n")

target_champ = """            if "pace_mode" in cmd and cmd["pace_mode"] in ("CONSERVE", "BALANCED", "PUSH", "ATTACK"):
                car.pace_mode = cmd["pace_mode"]
            if "ers_mode" in cmd and cmd["ers_mode"] in ("HARVEST", "AUTO", "BOOST", "OVERTAKE"):
                car.ers_mode = cmd["ers_mode"]"""

repl_champ = """            if "pace_mode" in cmd and cmd["pace_mode"] in ("CONSERVE", "BALANCED", "PUSH", "ATTACK"):
                old_pace = getattr(car, "pace_mode", "BALANCED")
                car.pace_mode = cmd["pace_mode"]
                if self.race_session and hasattr(self.race_session, "radio_dispatcher"):
                    clk = getattr(self.race_session, "race_clock", 0.0)
                    trk = getattr(self.race_session, "track", None)
                    turn = trk.nearest_corner(car.s) if trk and hasattr(trk, "nearest_corner") else 1
                    if car.pace_mode in ("PUSH", "ATTACK") and old_pace != car.pace_mode:
                        self.race_session.radio_dispatcher.trigger_push_mode(
                            car, car.pace_mode, is_pit_wall=True, event_cb=self._push_event, clock=clk, turn=turn
                        )
                    elif car.pace_mode == "CONSERVE" and old_pace != car.pace_mode:
                        self.race_session.radio_dispatcher.trigger_conserve_mode(
                            car, event_cb=self._push_event, clock=clk, turn=turn
                        )
            if "ers_mode" in cmd and cmd["ers_mode"] in ("HARVEST", "AUTO", "BOOST", "OVERTAKE"):
                old_ers = getattr(car, "ers_mode", "AUTO")
                car.ers_mode = cmd["ers_mode"]
                if self.race_session and hasattr(self.race_session, "radio_dispatcher"):
                    clk = getattr(self.race_session, "race_clock", 0.0)
                    trk = getattr(self.race_session, "track", None)
                    turn = trk.nearest_corner(car.s) if trk and hasattr(trk, "nearest_corner") else 1
                    if car.ers_mode in ("BOOST", "OVERTAKE") and old_ers != car.ers_mode:
                        self.race_session.radio_dispatcher.trigger_push_mode(
                            car, car.ers_mode, is_pit_wall=True, event_cb=self._push_event, clock=clk, turn=turn
                        )
                    elif car.ers_mode == "HARVEST" and old_ers != car.ers_mode:
                        self.race_session.radio_dispatcher.trigger_conserve_mode(
                            car, event_cb=self._push_event, clock=clk, turn=turn
                        )"""

assert target_champ in champ_code, "target_champ not found in sim/championship.py"
champ_code = champ_code.replace(target_champ, repl_champ, 1)

with open("sim/championship.py", "w", encoding="utf-8") as f:
    f.write(champ_code)

print("sim/championship.py patched successfully!")

