with open("sim/hall_of_fame.py", "r", encoding="utf-8") as f:
    text = f.read()

target = """    # Pick P2 and P3 from complementary top drivers
    p_pool = [d for d in DEFAULT_PODIUM_CANDIDATES if d != winner_id]
    p2_id = p_pool[(round_num * 3) % len(p_pool)]
    p3_id = p_pool[(round_num * 7 + 1) % len(p_pool)]
    if p2_id == p3_id:
        p3_id = p_pool[(round_num * 7 + 2) % len(p_pool)]"""

replacement = """    # Pick P2 and P3 with natural champion podium weighting
    champ_id = preset["wdc_id"]
    p_pool = [d for d in DEFAULT_PODIUM_CANDIDATES if d != winner_id]

    if champ_id != winner_id and round_num % 2 == 0:
        p2_id = champ_id
        rem = [d for d in p_pool if d != champ_id]
        p3_id = rem[(round_num * 5 + 1) % len(rem)]
    elif champ_id != winner_id and round_num % 3 == 0:
        rem = [d for d in p_pool if d != champ_id]
        p2_id = rem[(round_num * 3) % len(rem)]
        p3_id = champ_id
    else:
        p2_id = p_pool[(round_num * 3) % len(p_pool)]
        p3_id = p_pool[(round_num * 7 + 1) % len(p_pool)]
        if p2_id == p3_id:
            p3_id = p_pool[(round_num * 7 + 2) % len(p_pool)]"""

assert target in text, "Could not find target in hall_of_fame.py"
text = text.replace(target, replacement, 1)

with open("sim/hall_of_fame.py", "w", encoding="utf-8") as f:
    f.write(text)

print("sim/hall_of_fame.py updated successfully!")

