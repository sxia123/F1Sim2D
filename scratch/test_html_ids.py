with open('public/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

required_ids = [
    'tab-hall-of-fame', 'hof-era-badge', 'hof-engine-badge', 'hof-status-badge',
    'hof-champions-banner', 'hof-narrative-card', 'hof-races-grid',
    'hof-wdc-table', 'hof-wcc-table', 'hof-sub-races', 'hof-sub-standings',
    'hof-races-view', 'hof-standings-view'
]

for rid in required_ids:
    assert f'id="{rid}"' in html, f'Missing ID: {rid}'

assert 'data-tab="hall-of-fame"' in html, 'Missing hall of fame tab button'
assert 'hof-season-btn' in html, 'Missing hof-season-btn class'

print('All required IDs and elements found in public/index.html!')
