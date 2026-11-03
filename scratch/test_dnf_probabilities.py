def calc_race_dnfs(
    mech_coeff=0.00016,
    crash_risk_base=0.00028,
    crash_dnf_rate=0.20,
    collision_dnf_rate=0.12,
    double_dnf_rate=0.42,
    num_cars=20,
    race_time_s=1800,
):
    import random
    
    # Simulate 50 races
    total_mech = 0
    total_crash = 0
    total_coll = 0
    
    dt = 0.05
    steps = int(race_time_s / dt)
    
    # Analytical expected values:
    # 1. Mechanical: num_cars * race_time_s * mech_coeff * rel_factor(0.80)
    exp_mech = num_cars * race_time_s * mech_coeff * 0.80
    
    # 2. Crash: cars in high curv (~25% of lap) * crash_risk_base * crash_dnf_rate
    exp_crash = num_cars * (race_time_s * 0.25) * crash_risk_base * crash_dnf_rate
    
    # 3. Collision: assume ~1.5 contact incidents per race * collision_dnf_rate * (1 + double_dnf_rate)
    exp_coll = 1.5 * collision_dnf_rate * (1.0 + double_dnf_rate)
    
    total_exp = exp_mech + exp_crash + exp_coll
    return {
        "exp_mech": exp_mech,
        "exp_crash": exp_crash,
        "exp_coll": exp_coll,
        "total_exp_dnfs": total_exp
    }

old_stats = calc_race_dnfs(0.00016, 0.00028, 0.20, 0.12, 0.42)
new_stats = calc_race_dnfs(0.000035, 0.00014, 0.08, 0.04, 0.18)

print("--- OLD DNF PROFILE ---")
for k, v in old_stats.items():
    print(f"  {k}: {v:.2f}")

print("\n--- NEW DNF PROFILE ---")
for k, v in new_stats.items():
    print(f"  {k}: {v:.2f}")

