with open('sim/physics.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if '"INCIDENT"' in l or '"CRASH"' in l:
        print(f"Line {i+1}: {l.strip()}")
