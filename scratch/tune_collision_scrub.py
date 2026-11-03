with open('sim/physics.py', 'r', encoding='utf-8') as f:
    text = f.read()

t_scrub = "victim.v = max(8.0, victim.v - 8.0)"
r_scrub = "victim.v = max(8.0, victim.v - 2.2)"
assert t_scrub in text, "t_scrub not found"
text = text.replace(t_scrub, r_scrub, 1)

with open('sim/physics.py', 'w', encoding='utf-8') as f:
    f.write(text)
print("Updated victim scrub deceleration successfully!")

