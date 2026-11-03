with open('sim/physics.py', 'r', encoding='utf-8') as f:
    text = f.read()

t_follow = """            if not in_active_pass and dist_ahead_m < 135.0:
                st_ahead = self.track.sample(car_ahead.s)["station"]
                is_ahead_braking = self.is_braking[st_ahead] or car_ahead.braking
                brake_dist_req = max(0.0, car.v * car.v - car_ahead.v * car_ahead.v) / 85.0
                if is_ahead_braking and dist_ahead_m < brake_dist_req + 18.0:
                    target_v = min(target_v, car_ahead.v)
                elif in_same_lane and gap_ahead_s < 0.65:
                    desired_gap = 0.28
                    follow_v = car_ahead.v + (gap_ahead_s - desired_gap) * 16.0
                    target_v = min(target_v, max(follow_v, 4.0))"""

r_follow = """            if not in_active_pass and dist_ahead_m < 110.0:
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

assert t_follow in text, 't_follow not found'
text = text.replace(t_follow, r_follow, 1)

with open('sim/physics.py', 'w', encoding='utf-8') as f:
    f.write(text)
print('Applied smooth following overhaul successfully!')

