"""Apply smoothness and anti-bumping overhaul to sim/physics.py."""
import pathlib

PHYSICS_PATH = pathlib.Path(r"c:\Coding\F1Sim2D\sim\physics.py")

def main():
    text = PHYSICS_PATH.read_text(encoding="utf-8")

    # 1. Update QualifyingSession._update_xy (lines ~643-653)
    target_q_xy = """        # Dynamic course and apex yaw attitude
        tx, ty = smp["tx"], smp["ty"]
        nx, ny = smp["nx"], smp["ny"]
        half_usable = self.track.track_width_px * 0.39
        v_forward_px = max(6.0, car.v * self.track.px_per_m)
        v_lateral_px = (car.target_d - car.d) * 2.8 * half_usable * 0.18
        vx_c = v_forward_px * tx + v_lateral_px * nx
        vy_c = v_forward_px * ty + v_lateral_px * ny
        theta_course = math.atan2(vy_c, vx_c)
        yaw_attitude = getattr(car, "steer_angle", 0.0) * 0.24
        car.heading = round(theta_course + yaw_attitude, 4)"""

    repl_q_xy = """        # Dynamic course and apex yaw attitude (rate-limited, no snap)
        tx, ty = smp["tx"], smp["ty"]
        nx, ny = smp["nx"], smp["ny"]
        half_usable = self.track.track_width_px * 0.39
        v_forward_px = max(6.0, car.v * self.track.px_per_m)
        v_lateral_px = (car.target_d - car.d) * 2.8 * half_usable * 0.18
        drift_angle = max(-0.065, min(0.065, math.atan2(v_lateral_px, v_forward_px)))
        track_heading = math.atan2(ty, tx)
        yaw_attitude = getattr(car, "steer_angle", 0.0) * 0.20
        target_heading = (track_heading + drift_angle + yaw_attitude + math.pi) % (2.0 * math.pi) - math.pi

        prev_h = getattr(car, "heading", None)
        if prev_h is not None and getattr(car, "_has_initial_heading", False):
            dh = (target_heading - prev_h + math.pi) % (2.0 * math.pi) - math.pi
            max_dh = 8.5 * 0.05
            dh_clamped = max(-max_dh, min(max_dh, dh))
            car.heading = round((prev_h + dh_clamped + math.pi) % (2.0 * math.pi) - math.pi, 4)
        else:
            car.heading = round(target_heading, 4)
            car._has_initial_heading = True"""

    assert target_q_xy in text, "target_q_xy not found"
    text = text.replace(target_q_xy, repl_q_xy, 1)

    # 2. Update RaceSession._update_xy (lines ~984-998)
    target_race_xy = """        # 1. Course trajectory angle combining longitudinal speed and lateral maneuver velocity
        tx, ty = smp["tx"], smp["ty"]
        nx, ny = smp["nx"], smp["ny"]
        half_usable = self.track.track_width_px * 0.39
        v_forward_px = max(6.0, car.v * self.track.px_per_m)
        steer_rate = 5.8 if (car.maneuver_pass_timer > 0.0 or car.maneuver_timer > 0.0) else 2.8
        v_lateral_px = (car.target_d - car.d) * steer_rate * half_usable * 0.18

        vx_course = v_forward_px * tx + v_lateral_px * nx
        vy_course = v_forward_px * ty + v_lateral_px * ny
        theta_course = math.atan2(vy_course, vx_course)

        # 2. Dynamic chassis yaw in corners (especially hairpins): car nose turns naturally into the apex
        yaw_attitude = getattr(car, "steer_angle", 0.0) * 0.24
        car.heading = round(theta_course + yaw_attitude, 4)"""

    repl_race_xy = """        # 1. Course trajectory angle combining longitudinal speed and lateral maneuver velocity
        tx, ty = smp["tx"], smp["ty"]
        nx, ny = smp["nx"], smp["ny"]
        half_usable = self.track.track_width_px * 0.39
        v_forward_px = max(6.0, car.v * self.track.px_per_m)
        steer_rate = 5.8 if (car.maneuver_pass_timer > 0.0 or car.maneuver_timer > 0.0) else 2.8
        v_lateral_px = (car.target_d - car.d) * steer_rate * half_usable * 0.18

        drift_angle = max(-0.065, min(0.065, math.atan2(v_lateral_px, v_forward_px)))
        track_heading = math.atan2(ty, tx)

        # 2. Dynamic chassis yaw in corners (especially hairpins): car nose turns naturally into the apex
        yaw_attitude = getattr(car, "steer_angle", 0.0) * 0.20
        target_heading = (track_heading + drift_angle + yaw_attitude + math.pi) % (2.0 * math.pi) - math.pi

        prev_h = getattr(car, "heading", None)
        if prev_h is not None and getattr(car, "_has_initial_heading", False):
            dh = (target_heading - prev_h + math.pi) % (2.0 * math.pi) - math.pi
            max_dh = 8.5 * 0.05
            dh_clamped = max(-max_dh, min(max_dh, dh))
            car.heading = round((prev_h + dh_clamped + math.pi) % (2.0 * math.pi) - math.pi, 4)
        else:
            car.heading = round(target_heading, 4)
            car._has_initial_heading = True"""

    assert target_race_xy in text, "target_race_xy not found"
    text = text.replace(target_race_xy, repl_race_xy, 1)

    # 3. In _step_car: fix in_active_pass following distance bypass (lines ~1621-1626)
    target_active_pass = """            in_active_pass = (
                car.maneuver_pass_timer > 0.0
                or getattr(car_ahead, "maneuver_pass_timer", 0.0) > 0.0
                or car.battle_with == car_ahead.driver_id
                or is_alongside
            )"""

    repl_active_pass = """            in_active_pass = (
                (car.maneuver_pass_timer > 0.0 and abs(car.d - car_ahead.d) >= min_d_w * 0.75)
                or (getattr(car_ahead, "maneuver_pass_timer", 0.0) > 0.0 and abs(car.d - car_ahead.d) >= min_d_w * 0.75)
                or is_alongside
            )"""

    assert target_active_pass in text, "target_active_pass not found"
    text = text.replace(target_active_pass, repl_active_pass, 1)

    # 4. In _resolve_battles_and_incidents: smooth active pass acceleration & room leaving (lines ~2202-2208)
    target_active_pass_speed = """                        lat_sep = abs(compute_lateral_screen_px(self.track, c.d) - compute_lateral_screen_px(self.track, tgt.d))
                        if lat_sep >= CAR_WID_PX * 0.86:
                            c.v = max(c.v, tgt.v + 5.2)
                            tgt.v = max(4.0, min(tgt.v, c.v - 2.6))
                            # Defending car leaves generous racing room on opposite flank
                            tgt_room_side = 1.0 if c.d < tgt.d else -1.0
                            tgt.target_d = max(-0.84, min(0.84, c.target_d + tgt_room_side * max(0.82, min_d_sep * 1.30)))"""

    repl_active_pass_speed = """                        lat_sep = abs(compute_lateral_screen_px(self.track, c.d) - compute_lateral_screen_px(self.track, tgt.d))
                        if lat_sep >= CAR_WID_PX * 0.86:
                            st_c = self.track.sample(c.s)["station"]
                            v_env_c = self.v_env[st_c]
                            c.v = min(v_env_c, c.v + 16.0 * dt)
                            if tgt.v > c.v - 1.2:
                                tgt.v = max(4.0, tgt.v - 8.0 * dt)
                            # Defending car leaves generous racing room on opposite flank
                            tgt_room_side = 1.0 if c.d < tgt.d else -1.0
                            tgt.target_d = max(-0.84, min(0.84, c.target_d + tgt_room_side * max(0.82, min_d_sep * 1.20)))"""

    assert target_active_pass_speed in text, "target_active_pass_speed not found"
    text = text.replace(target_active_pass_speed, repl_active_pass_speed, 1)

    # 5. In _resolve_battles_and_incidents: attacker lane selection without oscillation (lines ~2263-2273)
    target_atk_lane = """            # Ensure attacker's passing lane always clears defender laterally by >= min_d_sep * 1.30
            if attacker.maneuver_timer <= 0.0 and attacker.maneuver_pass_timer <= 0.0:
                if attacker.attacking_side == 0.0:
                    attacker.attacking_side = -1.0 if defender.target_d >= 0.0 else 1.0
                side = attacker.attacking_side
                if defender.target_d + side * min_d_sep * 1.30 > 0.86:
                    side = -1.0
                    attacker.attacking_side = -1.0
                elif defender.target_d + side * min_d_sep * 1.30 < -0.86:
                    side = 1.0
                    attacker.attacking_side = 1.0
                attacker.target_d = max(-0.86, min(0.86, defender.target_d + side * max(0.85, min_d_sep * 1.30)))"""

    repl_atk_lane = """            # Ensure attacker's passing lane locks into chosen flank without oscillating
            if attacker.maneuver_timer <= 0.0 and attacker.maneuver_pass_timer <= 0.0:
                if getattr(attacker, "attacking_side", 0.0) == 0.0:
                    attacker.attacking_side = -1.0 if defender.target_d >= 0.0 else 1.0
                side = attacker.attacking_side
                if side > 0.0:
                    attacker.target_d = min(0.84, max(defender.target_d + min_d_sep * 1.05, 0.38))
                else:
                    attacker.target_d = max(-0.84, min(defender.target_d - min_d_sep * 1.05, -0.38))"""

    assert target_atk_lane in text, "target_atk_lane not found"
    text = text.replace(target_atk_lane, repl_atk_lane, 1)

    # 6. In _resolve_battles_and_incidents: maneuver launch speed & stout defense handling (lines ~2304-2334)
    target_man_trigger = """                    if attacker.overtake_active:
                        # Slingshot punch: attacker surges past defender with decisive velocity
                        attacker.v = max(attacker.v, defender.v + 4.2)
                    # Defender respects the completed pass and leaves clear lateral room
                    side = 1.0 if attacker.target_d < defender.d else -1.0
                    defender.target_d = max(-0.86, min(0.86, attacker.target_d + side * min_d_sep * 1.30))
                    defender.defense_moves = 0
                    defender.defense_timer = 0.0
                    defender.battle_with = None
                    defender.attacking_side = 0.0
                    attacker.attacking_side = 0.0"""

    repl_man_trigger = """                    if attacker.overtake_active:
                        # Slingshot punch: attacker surges past defender with smooth envelope-bounded velocity
                        attacker.v = min(self.v_env[st], attacker.v + 1.2)
                    # Defender respects the completed pass and leaves clear lateral room
                    side = 1.0 if attacker.target_d < defender.d else -1.0
                    defender.target_d = max(-0.84, min(0.84, attacker.target_d + side * min_d_sep * 1.15))
                    defender.defense_moves = 0
                    defender.defense_timer = 0.0
                    defender.battle_with = None
                    defender.attacking_side = 0.0
                    attacker.attacking_side = 0.0"""

    assert target_man_trigger in text, "target_man_trigger not found"
    text = text.replace(target_man_trigger, repl_man_trigger, 1)

    target_stout_defense = """                else:
                    defender.maneuver = "DEFEND"
                    defender.maneuver_timer = 2.0
                    attacker.v = min(attacker.v, defender.v * 0.96)
                    attacker.maneuver_timer = 0.0
                    # On stout defense, attacker holds clean slipstream line behind defender
                    attacker.target_d = defender.d
                    attacker.attacking_side = 0.0"""

    repl_stout_defense = """                else:
                    defender.maneuver = "DEFEND"
                    defender.maneuver_timer = 2.0
                    # Attacker eases throttle smoothly without instant deceleration crash
                    attacker.v = max(4.0, max(defender.v * 0.96, attacker.v - 14.0 * dt))
                    attacker.maneuver_timer = 0.0
                    # On stout defense, attacker maintains safe flank line rather than swerving into defender
                    side_atk = attacker.attacking_side if getattr(attacker, "attacking_side", 0.0) != 0.0 else 1.0
                    attacker.target_d = max(-0.84, min(0.84, defender.target_d + side_atk * min_d_sep * 1.15))"""

    assert target_stout_defense in text, "target_stout_defense not found"
    text = text.replace(target_stout_defense, repl_stout_defense, 1)

    # 7. In enforce_2d_car_separation: Section 2 soften nudge and smooth following decel (lines ~218-238)
    target_sec2 = """                    if (lat_sep >= req_lat or is_passing) and allow_passing:
                        if lat_sep < CAR_WID_PX:
                            need_d = (CAR_WID_PX - lat_sep) / half_usable + 0.04
                            if c.d >= o.d:
                                c.d = min(0.92, c.d + need_d * 0.50)
                                o.d = max(-0.92, o.d - need_d * 0.30)
                            else:
                                c.d = max(-0.92, c.d - need_d * 0.50)
                                o.d = min(0.92, o.d + need_d * 0.30)
                            c.target_d = c.d
                            o.target_d = o.d
                        new_sep = abs(compute_lateral_screen_px(track, o.d) - compute_lateral_screen_px(track, c.d))
                        if new_sep >= CAR_WID_PX - 0.05 or is_passing:
                            continue

                    deficit = min_long_m - ds_m
                    if deficit > 0:
                        if is_blue_yield:
                            c.v = max(c.v, o.v * 1.02)
                        else:
                            c.v = min(c.v, max(o.v * 0.988, 4.0))"""

    repl_sec2 = """                    if (lat_sep >= req_lat or is_passing) and allow_passing:
                        if lat_sep < CAR_WID_PX:
                            need_d = min(0.08, (CAR_WID_PX - lat_sep) / half_usable * 0.35 + 0.01)
                            if c.d >= o.d:
                                c.d = min(0.92, c.d + need_d * 0.60)
                                o.d = max(-0.92, o.d - need_d * 0.40)
                            else:
                                c.d = max(-0.92, c.d - need_d * 0.60)
                                o.d = min(0.92, o.d + need_d * 0.40)
                            c.target_d = c.d
                            o.target_d = o.d
                        new_sep = abs(compute_lateral_screen_px(track, o.d) - compute_lateral_screen_px(track, c.d))
                        if new_sep >= CAR_WID_PX - 0.05 or is_passing:
                            continue

                    deficit = min_long_m - ds_m
                    if deficit > 0:
                        if is_blue_yield:
                            c.v = max(c.v, o.v * 1.02)
                        else:
                            c.v = max(4.0, max(o.v * 0.98, c.v - 22.0 * 0.05))"""

    assert target_sec2 in text, "target_sec2 not found"
    text = text.replace(target_sec2, repl_sec2, 1)

    # 8. In enforce_2d_car_separation: Section 3 Case B & Case C (lines ~318-368)
    target_case_b = """                    need_d = (max(pen_w1, pen_w2) + 0.45) / half_usable
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
                            new_a = min(0.93, new_a + (need_d - used_a - used_b))"""

    repl_case_b = """                    need_d = (max(pen_w1, pen_w2) + 0.15) / half_usable
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
                            new_a = min(0.93, new_a + (need_d - used_a - used_b))"""

    assert target_case_b in text, "target_case_b not found"
    text = text.replace(target_case_b, repl_case_b, 1)

    target_case_c = """                    if sign_dir < 0.0 and not mover.dnf and mover.pit_phase != "STOPPED":
                        mover.v = min(mover.v, max(ahead.v * 0.98, 4.0))"""

    repl_case_c = """                    if sign_dir < 0.0 and not mover.dnf and mover.pit_phase != "STOPPED":
                        mover.v = max(4.0, max(ahead.v * 0.98, mover.v - 22.0 * 0.05))"""

    assert target_case_c in text, "target_case_c not found"
    text = text.replace(target_case_c, repl_case_c, 1)

    # 9. In _on_physical_contact: impulse deceleration (lines ~2564-2565)
    target_col_impulse = """            # Longitudinal contact: trailing car into rear of car ahead
            # Physical longitudinal impulse
            behind.v = max(8.0, ahead.v - 1.4)
            ahead.v = min(ahead.v + 0.8, 95.0)"""

    repl_col_impulse = """            # Longitudinal contact: trailing car into rear of car ahead
            # Physical longitudinal impulse: smooth damped scrub without instant 30 m/s crash drop
            behind.v = max(8.0, max(ahead.v * 0.96, behind.v - 2.8))
            ahead.v = min(ahead.v + 0.8, 95.0)"""

    assert target_col_impulse in text, "target_col_impulse not found"
    text = text.replace(target_col_impulse, repl_col_impulse, 1)

    PHYSICS_PATH.write_text(text, encoding="utf-8")
    print("sim/physics.py updated cleanly and verified!")

if __name__ == "__main__":
    main()

