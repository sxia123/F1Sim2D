import re

with open('sim/championship.py', encoding='utf-8') as f:
    text = f.read()

radio_matches = re.findall(r'_push_event\([\'"]RADIO[\'"].*?\)', text, re.DOTALL)
print('Total RADIO in championship.py:', len(radio_matches))
for r in radio_matches[:10]:
    print(' -', repr(r[:90]))

other_events = re.findall(r'_push_event\([\'"]([A-Z_]+)[\'"]', text)
from collections import Counter
print('Event kinds in championship.py:', Counter(other_events))

