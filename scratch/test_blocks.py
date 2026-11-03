import pathlib

ROOT = pathlib.Path(r"c:\Coding\F1Sim2D")
phys_file = ROOT / "sim" / "physics.py"
text = phys_file.read_text(encoding="utf-8")

old_steer = """        steer_rate = 5.8 if (car.maneuver_pass_timer > 0.0 or car.maneuver_timer > 0.0) else 2.8
        car.d += (car.target_d - car.d) * min(1.0, dt * steer_rate)"""

old_blue_yield = """                    deficit = min_long_m - ds_m
                    if deficit > 0:
                        if is_blue_yield:
                            c.v = max(c.v, o.v * 1.02)
                        else:
                            c.v = min(c.v, max(o.v * 0.988, 4.0))
                        soft_shift = min(deficit * 0.30 + 0.02, 0.25)
                        c.total_dist -= soft_shift
                        c.s = c.total_dist % L"""

old_sat_spread = """                if is_lateral and not ahead.in_pits and not behind.in_pits and not c1_off and not c2_off and allow_passing:
                    need_d = (max(pen_w1, pen_w2) + 0.45) / half_usable
                    if behind.d >= ahead.d:
                        new_a = max(-0.93, ahead.d - need_d * 0.40)
                        used_a = ahead.d - new_a
                        new_b = min(0.93, behind.d + (need_d - used_a))
                        used_b = new_b - behind.d
                        if used_a + used_b < need_d:
                            new_a = max(-0.93, new_a - (need_d - used_a - used_b))
                    else:
                        new_a = min(0.93, ahead.d + need_d * 0.40)
                        used_a = new_a - ahead.d
                        new_b = max(-0.93, behind.d - (need_d - used_a))
                        used_b = behind.d - new_b
                        if used_a + used_b < need_d:
                            new_a = min(0.93, new_a + (need_d - used_a - used_b))
                    ahead.d = new_a
                    behind.d = new_b"""

old_pit_q = """                behind.total_dist -= soft_shift
                behind.s = behind.total_dist % L
                behind.v = min(behind.v, ahead.v)"""

old_env1 = """                        if lat_sep >= CAR_WID_PX * 0.86:
                            c.v = max(c.v, tgt.v + 5.2)
                            tgt.v = max(4.0, min(tgt.v, c.v - 2.6))"""

old_env2 = """                    if attacker.overtake_active:
                        # Slingshot punch: attacker surges past defender with decisive velocity
                        attacker.v = max(attacker.v, defender.v + 4.2)"""

old_team_hold = """            if attacker.team_id == defender.team_id and attacker.team_order == "HOLD":
                attacker.v = min(attacker.v, defender.v * 0.995)
                continue"""

old_yellow = """                    attacker.v = min(attacker.v, defender.v)
                    continue"""

old_handle_col = """        is_lap1 = attacker.lap == 1
        if roll < 0.62 or is_lap1:
            victim.v *= 0.90
            deflect_dir = 1.0 if victim.d >= culprit.d else -1.0
            victim.d = max(-1.15, min(1.15, victim.d + deflect_dir * 0.28))
            culprit.d = max(-1.15, min(1.15, culprit.d - deflect_dir * 0.14))
            self._update_xy(victim)
            self._update_xy(culprit)
            victim.smoke = 1.4
            attacker.sparks = True
            defender.sparks = True
            culprit.repair_cost_m += 0.12
            if random.random() < 0.35:
                culprit.wing_damage = min(0.35, culprit.wing_damage + random.uniform(0.06, 0.12))
            event_cb(
                "INCIDENT",
                f"WHEEL-TO-WHEEL! Contact between #{attacker.number} {attacker.code} and #{defender.number} {defender.code} at Turn {turn}!",
            )"""

old_spin_teleport = """            victim.d = 1.42 if victim.d >= 0.0 else -1.42
            victim.smoke = 4.5
            victim.repair_cost_m += round(random.uniform(0.95, 2.10), 2)
            self._update_xy(victim)"""

old_contact_side = """        if is_side_by_side:
            # Physical lateral separation impulse
            d_diff = c1.d - c2.d
            side_norm = 1.0 if d_diff >= 0.0 else -1.0
            c1.d = max(-1.12, min(1.12, c1.d + side_norm * 0.14))
            c2.d = max(-1.12, min(1.12, c2.d - side_norm * 0.14))
            self._update_xy(c1)
            self._update_xy(c2)
            c1.sparks = True
            c2.sparks = True

            # Clean F1 wheel-to-wheel racing: zero wing damage and zero false alerts
            # Only trigger an incident on severe, violent speed mismatch (> 9.4 m/s / 34 km/h)
            if speed_gap > 9.4:"""

old_contact_rear = """            # High closing speed (> 7.4 m/s / 27 km/h) damages front wing
            if delta_v > 7.4:"""

blocks = [
    ('old_steer', old_steer),
    ('old_blue_yield', old_blue_yield),
    ('old_sat_spread', old_sat_spread),
    ('old_pit_q', old_pit_q),
    ('old_env1', old_env1),
    ('old_env2', old_env2),
    ('old_team_hold', old_team_hold),
    ('old_yellow', old_yellow),
    ('old_handle_col', old_handle_col),
    ('old_spin_teleport', old_spin_teleport),
    ('old_contact_side', old_contact_side),
    ('old_contact_rear', old_contact_rear),
]

all_ok = True
for name, b in blocks:
    found = b in text
    print(name, ":", found)
    if not found:
        all_ok = False

if all_ok:
    print("ALL BLOCKS FOUND SUCCESSFULLY!")
else:
    print("SOME BLOCKS FAILED")
