import re

with open('sim/physics.py', encoding='utf-8') as f:
    text = f.read()

radio_matches = re.findall(r'event_cb\([\'"]RADIO[\'"].*?\)', text, re.DOTALL)
print('Total RADIO in physics.py:', len(radio_matches))
for r in radio_matches[:10]:
    print(' -', repr(r[:90]))

other_events = re.findall(r'event_cb\([\'"]([A-Z_]+)[\'"]', text)
from collections import Counter
print('Event kinds in physics.py:', Counter(other_events))

