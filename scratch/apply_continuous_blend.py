with open('sim/physics.py', 'r', encoding='utf-8') as f:
    text = f.read()

t_bang = """            if not in_active_pass and dist_ahead_m < 110.0:
                st_ahead = self.track.sample(car_ahead.s)["station"]
                is_ahead_braking = self.is_braking[st_ahead]
                brake_dist_req = max(0.0, car.v * car.v - car_ahead.v * car_ahead.v) / 85.0
                if is_ahead_braking and dist_ahead_m < brake_dist_req + 18.0:
                    target_v = min(target_v, max(car_ahead.v, car.v - 28.0 * dt))
                elif in_same_lane and gap_ahead_s < 0.85:
                    blend = max(0.0, min(1.0, (0.85 - gap_ahead_s) / 0.55))
                    desired_gap = 0.32
                    follow_v = car_ahead.v + (gap_ahead_s - desired_gap) * 14.0
                    target_follow = max(4.0, follow_v)
                    target_v = min(target_v, (1.0 - blend) * target_v + blend * target_follow)"""

r_bang = """            if not in_active_pass and dist_ahead_m < 110.0:
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

assert t_bang in text, 't_bang not found'
text = text.replace(t_bang, r_bang, 1)

with open('sim/physics.py', 'w', encoding='utf-8') as f:
    f.write(text)
print('Applied continuous blend following successfully!')

