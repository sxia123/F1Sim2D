with open('sim/physics.py', 'r', encoding='utf-8') as f:
    text = f.read()

t_acc = """            drag_fade = max(0.18, 1.0 - (max(0.0, car.v) / 104.0) ** 1.85)
            car.accel = pu_acc * drag_fade
            car.v = min(target_v, car.v + car.accel * dt)"""

r_acc = """            drag_fade = max(0.18, 1.0 - (max(0.0, car.v) / 104.0) ** 1.85)
            v_deficit = target_v - car.v
            max_acc = pu_acc * drag_fade
            in_braking_or_apex = (smp["curv"] > 0.003 or self.is_braking[st])
            if in_braking_or_apex and v_deficit <= 1.5:
                # Progressive throttle roll-on in braking/corner zones: prevents full-power ping-pong
                car.accel = min(max_acc, max(2.0, v_deficit / max(dt, 0.001)))
            else:
                car.accel = max_acc
            car.v = min(target_v, car.v + car.accel * dt)"""

assert t_acc in text, "t_acc not found"
text = text.replace(t_acc, r_acc, 1)

with open('sim/physics.py', 'w', encoding='utf-8') as f:
    f.write(text)
print("Applied progressive throttle roll-on successfully!")

