with open('sim/physics.py', 'r', encoding='utf-8') as f:
    text = f.read()

t_lane = """        elif self.flag_state == "GREEN" and car_ahead and not car_ahead.in_pits:
            half_u = self.track.width_px_at(car.s) * 0.39
            min_d_w = CAR_WID_PX / half_u
            in_same_lane = abs(car.d - car_ahead.d) < min_d_w * 0.92
            dist_ahead_m = (car_ahead.s - car.s) % self.track.length_m
            min_long_car = CAR_LEN_PX / self.track.px_per_m
            is_alongside = dist_ahead_m < min_long_car * 0.95 and abs(car.d - car_ahead.d) >= min_d_w * 0.75
            in_active_pass = (
                car.maneuver_pass_timer > 0.0
                or getattr(car_ahead, "maneuver_pass_timer", 0.0) > 0.0
                or car.battle_with == car_ahead.driver_id
                or is_alongside
            )
            if not in_active_pass and dist_ahead_m < 110.0:
                st_ahead = self.track.sample(car_ahead.s)["station"]
                is_ahead_braking = self.is_braking[st_ahead]
                brake_dist_req = max(0.0, car.v * car.v - car_ahead.v * car_ahead.v) / 85.0
                if is_ahead_braking and dist_ahead_m < brake_dist_req + 28.0:
                    margin = (brake_dist_req + 28.0) - dist_ahead_m
                    brake_blend = min(1.0, margin / 16.0)
                    approach_v = (1.0 - brake_blend) * target_v + brake_blend * car_ahead.v
                    target_v = min(target_v, approach_v)
                elif in_same_lane and gap_ahead_s < 0.90:
                    blend = max(0.0, min(1.0, (0.90 - gap_ahead_s) / 0.60))
                    desired_gap = 0.35
                    follow_v = car_ahead.v + (gap_ahead_s - desired_gap) * 12.0
                    target_follow = max(4.0, follow_v)
                    target_v = min(target_v, (1.0 - blend) * target_v + blend * target_follow)"""

r_lane = """        elif self.flag_state == "GREEN" and car_ahead and not car_ahead.in_pits:
            half_u = self.track.width_px_at(car.s) * 0.39
            min_d_w = CAR_WID_PX / half_u
            lane_offset = abs(car.d - car_ahead.d)
            # Continuous lateral overlap factor tapering smoothly (zero discrete flicker)
            lateral_overlap = max(0.0, min(1.0, (min_d_w * 1.20 - lane_offset) / max(0.01, min_d_w * 0.45)))
            dist_ahead_m = (car_ahead.s - car.s) % self.track.length_m
            min_long_car = CAR_LEN_PX / self.track.px_per_m
            is_alongside = dist_ahead_m < min_long_car * 0.95 and lane_offset >= min_d_w * 0.75
            in_active_pass = (
                car.maneuver_pass_timer > 0.0
                or getattr(car_ahead, "maneuver_pass_timer", 0.0) > 0.0
                or car.battle_with == car_ahead.driver_id
                or is_alongside
            )
            if not in_active_pass and dist_ahead_m < 110.0 and lateral_overlap > 0.001:
                st_ahead = self.track.sample(car_ahead.s)["station"]
                is_ahead_braking = self.is_braking[st_ahead]
                brake_dist_req = max(0.0, car.v * car.v - car_ahead.v * car_ahead.v) / 85.0
                if is_ahead_braking and dist_ahead_m < brake_dist_req + 28.0:
                    margin = (brake_dist_req + 28.0) - dist_ahead_m
                    brake_blend = min(1.0, margin / 16.0) * lateral_overlap
                    approach_v = (1.0 - brake_blend) * target_v + brake_blend * car_ahead.v
                    target_v = min(target_v, approach_v)
                elif gap_ahead_s < 0.92:
                    gap_blend = max(0.0, min(1.0, (0.92 - gap_ahead_s) / 0.60))
                    blend = gap_blend * lateral_overlap
                    desired_gap = 0.35
                    follow_v = car_ahead.v + (gap_ahead_s - desired_gap) * 12.0
                    target_follow = max(4.0, follow_v)
                    target_v = min(target_v, (1.0 - blend) * target_v + blend * target_follow)"""

assert t_lane in text, 't_lane not found'
text = text.replace(t_lane, r_lane, 1)

with open('sim/physics.py', 'w', encoding='utf-8') as f:
    f.write(text)
print('Applied continuous lateral overlap following successfully!')

