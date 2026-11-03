from pathlib import Path

p = Path("sim/physics.py")
text = p.read_text(encoding="utf-8")

old_aero = """        # Aero mode determination
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
            car.aero_mode = "CORNER\""""

new_aero = """        # Check DRS active for classic DRS era
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
            car.aero_mode = "CORNER\""""

assert old_aero in text, "old_aero not found"
text = text.replace(old_aero, new_aero, 1)

old_drs_dup = """            # Active DRS Zone Check for Classic DRS Era
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
        else:"""

new_drs_dup = """        else:"""

assert old_drs_dup in text, "old_drs_dup not found"
text = text.replace(old_drs_dup, new_drs_dup, 1)

p.write_text(text, encoding="utf-8")
print("Successfully synced DRS evaluation timing in sim/physics.py!")

