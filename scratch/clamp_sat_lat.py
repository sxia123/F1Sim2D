"""Clamp maximum lateral shift in SAT to 0.11 per car per tick."""
import pathlib

ROOT = pathlib.Path(r"c:\Coding\F1Sim2D")
phys_file = ROOT / "sim" / "physics.py"
text = phys_file.read_text(encoding="utf-8")

old_sat_lat = """                if is_lateral and not ahead.in_pits and not behind.in_pits and not c1_off and not c2_off and allow_passing:
                    need_d = min(0.24, (max(pen_w1, pen_w2) + 0.15) / half_usable)
                    if behind.d >= ahead.d:
                        new_a = max(-0.93, ahead.d - need_d * 0.50)
                        used_a = ahead.d - new_a
                        new_b = min(0.93, behind.d + (need_d - used_a))
                        used_b = new_b - behind.d
                        if used_a + used_b < need_d:
                            new_a = max(-0.93, new_a - (need_d - used_a - used_b))
                    else:
                        new_a = min(0.93, ahead.d + need_d * 0.50)
                        used_a = new_a - ahead.d
                        new_b = max(-0.93, behind.d - (need_d - used_a))
                        used_b = behind.d - new_b
                        if used_a + used_b < need_d:
                            new_a = min(0.93, new_a + (need_d - used_a - used_b))
                    ahead.d = new_a
                    behind.d = new_b"""

new_sat_lat = """                if is_lateral and not ahead.in_pits and not behind.in_pits and not c1_off and not c2_off and allow_passing:
                    need_d = min(0.22, (max(pen_w1, pen_w2) + 0.15) / half_usable)
                    max_single_shift = 0.11
                    if behind.d >= ahead.d:
                        shift_a = min(max_single_shift, need_d * 0.50)
                        new_a = max(-0.93, ahead.d - shift_a)
                        shift_b = min(max_single_shift, need_d - (ahead.d - new_a))
                        new_b = min(0.93, behind.d + shift_b)
                    else:
                        shift_a = min(max_single_shift, need_d * 0.50)
                        new_a = min(0.93, ahead.d + shift_a)
                        shift_b = min(max_single_shift, need_d - (new_a - ahead.d))
                        new_b = max(-0.93, behind.d - shift_b)
                    ahead.d = new_a
                    behind.d = new_b"""

assert old_sat_lat in text, "old_sat_lat not found"
text = text.replace(old_sat_lat, new_sat_lat)
phys_file.write_text(text, encoding="utf-8")
print("Successfully clamped SAT lateral shift per car to 0.11")

