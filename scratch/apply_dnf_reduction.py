import sys
import os

def patch_dnf():
    path = os.path.join("sim", "physics.py")
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Single car spin/crash risk & terminal DNF reduction
    old_crash = '''        slick_in_rain = self.wetness > 0.25 and car.compound in ("SOFT", "MEDIUM", "HARD")
        risk = (
            0.00028
            * push_mult
            * (1.35 - sk["consistency"] / 100.0)
            * (3.8 if slick_in_rain else (1.45 if self.wetness > 0.35 else 1.0))
            * (2.2 if car.tire_wear > 0.76 else 1.0)
            * dt
        )
        if smp["curv"] > 0.012 and random.random() < risk:
            turn = self.track.nearest_corner(car.s)
            if random.random() < (0.34 if self.track.id in ("monaco", "saudi", "azerbaijan", "singapore", "canada") else 0.20):
                car.dnf = True'''

    new_crash = '''        slick_in_rain = self.wetness > 0.25 and car.compound in ("SOFT", "MEDIUM", "HARD")
        # Reduced base crash risk from 0.00028 to 0.00011 (less arbitrary random retirements)
        risk = (
            0.00011
            * push_mult
            * (1.25 - sk["consistency"] / 110.0)
            * (3.2 if slick_in_rain else (1.35 if self.wetness > 0.35 else 1.0))
            * (1.9 if car.tire_wear > 0.76 else 1.0)
            * dt
        )
        if smp["curv"] > 0.012 and random.random() < risk:
            turn = self.track.nearest_corner(car.s)
            # Reduced terminal barrier impact DNF rate from 20%/34% to 6%/12% (most spins recover or clip wing)
            if random.random() < (0.12 if self.track.id in ("monaco", "saudi", "azerbaijan", "singapore", "canada") else 0.06):
                car.dnf = True'''

    assert old_crash in content, "old_crash target not found in sim/physics.py"
    content = content.replace(old_crash, new_crash, 1)

    # 2. Mechanical failure reduction
    old_mech = '''        rel_lvl = u["reliability"]
        mech_prob = 0.00016 * max(0.22, 1.38 - rel_lvl * 0.115) * (1.25 if car.pace_mode == "ATTACK" else 1.0) * dt
        if random.random() < mech_prob:
            failure = random.choice(["MGU-K Electrical Failure", "Turbocharger Failure", "Hydraulics Leak", "Gearbox Issue"])'''

    new_mech = '''        # Mechanical reliability failure (scaled to authentic modern F1 standards, ~80% reduction)
        rel_lvl = u.get("reliability", 5)
        pace_factor = 0.65 if car.pace_mode == "CONSERVE" else (1.20 if car.pace_mode == "ATTACK" else 1.0)
        # Grace period for early race (clock > 35.0s) and reduced coefficient from 0.00016 to 0.000032
        mech_prob = (
            (0.000032 * max(0.18, 1.35 - rel_lvl * 0.12) * pace_factor * dt)
            if self.race_clock > 35.0
            else 0.0
        )
        if random.random() < mech_prob:
            failure = random.choice(["MGU-K Electrical Failure", "Turbocharger Failure", "Hydraulics Leak", "Gearbox Issue"])'''

    assert old_mech in content, "old_mech target not found in sim/physics.py"
    content = content.replace(old_mech, new_mech, 1)

    # 3. Collision terminal DNF threshold & double DNF reduction
    old_coll = '''        elif roll < 0.88:
            attacker.wing_damage = min(0.85, attacker.wing_damage + random.uniform(0.24, 0.45))
            attacker.wing_damage_side = "RIGHT" if attacker.d > defender.d else "LEFT"
            attacker.repair_cost_m += 0.45
            if attacker.wing_damage >= 0.35 and not attacker.box_this_lap:
                attacker.box_this_lap = True
            victim.spin_timer = random.uniform(2.8, 4.5)
            victim.spin_omega = random.choice([-5.8, 5.8]) * random.uniform(0.85, 1.25)
            victim.spin_lateral_dir = 1.0 if victim.d >= 0.0 else -1.0
            victim.spin_rebound_done = False
            victim.smoke = 2.4
            self.radio_dispatcher.trigger_spin(victim, turn, event_cb, self.race_clock)
            victim.repair_cost_m += 0.32
            self.flag_state = "YELLOW"
            self.yellow_sector = sector
            self.yellow_timer = 8.0
            event_cb(
                "CRASH",
                f"COLLISION AT TURN {turn}! {attacker.code} and {defender.code} tangle â€” {victim.code} spins & carbon debris flies!",
            )
            self.stewards_queue.append(
                {
                    "timer": 8.5,
                    "stage": "NOTED",
                    "turn": turn,
                    "culprit_id": culprit.driver_id,
                    "summary": f"{attacker.code} & {defender.code} collision",
                    "reason": "Causing a Collision",
                    "verdict": random.choice(["5S", "10S", "NFA"]),
                }
            )
        else:
            victim.dnf = True
            victim.dnf_reason = f"Collision with {culprit.code} (T{turn})"
            victim.dnf_timer = 38.0
            victim.v = 0.0
            victim.target_d = 1.35 if victim.d >= 0.0 else -1.35
            victim.smoke = 4.5
            victim.repair_cost_m += round(random.uniform(0.95, 2.10), 2)
            victim.wing_damage = min(0.90, victim.wing_damage + random.uniform(0.40, 0.75))
            self._update_xy(victim)

            double_dnf = random.random() < 0.42'''

    new_coll = '''        elif roll < 0.96:
            attacker.wing_damage = min(0.85, attacker.wing_damage + random.uniform(0.24, 0.45))
            attacker.wing_damage_side = "RIGHT" if attacker.d > defender.d else "LEFT"
            attacker.repair_cost_m += 0.45
            if attacker.wing_damage >= 0.35 and not attacker.box_this_lap:
                attacker.box_this_lap = True
            victim.spin_timer = random.uniform(2.8, 4.5)
            victim.spin_omega = random.choice([-5.8, 5.8]) * random.uniform(0.85, 1.25)
            victim.spin_lateral_dir = 1.0 if victim.d >= 0.0 else -1.0
            victim.spin_rebound_done = False
            victim.smoke = 2.4
            self.radio_dispatcher.trigger_spin(victim, turn, event_cb, self.race_clock)
            victim.repair_cost_m += 0.32
            self.flag_state = "YELLOW"
            self.yellow_sector = sector
            self.yellow_timer = 8.0
            event_cb(
                "CRASH",
                f"COLLISION AT TURN {turn}! {attacker.code} and {defender.code} tangle — {victim.code} spins & carbon debris flies!",
            )
            self.stewards_queue.append(
                {
                    "timer": 8.5,
                    "stage": "NOTED",
                    "turn": turn,
                    "culprit_id": culprit.driver_id,
                    "summary": f"{attacker.code} & {defender.code} collision",
                    "reason": "Causing a Collision",
                    "verdict": random.choice(["5S", "10S", "NFA"]),
                }
            )
        else:
            # Rare terminal crash (top 4% of collisions only)
            victim.dnf = True
            victim.dnf_reason = f"Collision with {culprit.code} (T{turn})"
            victim.dnf_timer = 38.0
            victim.v = 0.0
            victim.target_d = 1.35 if victim.d >= 0.0 else -1.35
            victim.smoke = 4.5
            victim.repair_cost_m += round(random.uniform(0.95, 2.10), 2)
            victim.wing_damage = min(0.90, victim.wing_damage + random.uniform(0.40, 0.75))
            self._update_xy(victim)

            double_dnf = random.random() < 0.16'''

    if old_coll in content:
        content = content.replace(old_coll, new_coll, 1)
    else:
        alt_old = old_coll.replace("â€”", "—")
        assert alt_old in content, "old_coll not found"
        content = content.replace(alt_old, new_coll, 1)

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("Successfully patched sim/physics.py for DNF reduction")

if __name__ == "__main__":
    patch_dnf()
