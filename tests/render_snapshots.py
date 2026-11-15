"""Print synthetic snapshots only. Never captures real session content."""
from fixtures import fleet
from herdr_fleet.model import Fleet, build_rows
from herdr_fleet.renderer import View, render
from herdr_fleet.theme import Palette


model = Fleet()
payload = fleet()
payload[0]['terminal_title_stripped'] = 'Implementation \u00b7 Implement API | example.user \u00b7 1'
model.update(payload, 0)
rows = build_rows(model, workspace_labels={'w1': 'Engineering', 'w2': 'Docs', 'w3': 'Personal'},
                  tab_labels={'w1:t1': 'Implementation', 'w1:t2': 'Review', 'w2:t1': 'Site'},
                  username='example.user')
for width in (40, 80, 160):
    print('\nWIDTH %d (synthetic fixture)' % width)
    view = View(model, rows, selected='attention:w1:p2', now=252,
                peek=('Synthetic preview only', 'Tests pass; waiting for review'), peek_title='Review Unicode')
    print('\n'.join(render(view, width, 28, Palette(mode='none'))))
