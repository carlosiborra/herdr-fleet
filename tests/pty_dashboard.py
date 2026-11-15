"""Synthetic PTY fixture. Does not invoke HerdR or read real agents."""
import sys

from herdr_fleet.app import main
from herdr_fleet.client import HerdrError
from fixtures import fleet


class FakeClient:
    def __init__(self):
        self.calls = 0

    def agents(self):
        self.calls += 1
        if '--fail-once' in sys.argv and self.calls == 1:
            raise HerdrError('Synthetic outage')
        return fleet()

    def labels(self):
        return {'w1': 'Engineering', 'w2': 'Docs', 'w3': 'Personal'}, {}

    def peek(self, target):
        return ('Synthetic preview', 'No real agent output')

    def focus(self, target):
        return {'agent': {'pane_id': target}}


if '--crash' in sys.argv:
    import herdr_fleet.app as app
    original_render = app.render
    def failing_render(view, *args):
        if view.fleet.agents:
            raise RuntimeError('Synthetic render failure')
        return original_render(view, *args)
    app.render = failing_render

raise SystemExit(main([], environ={'HERDR_ENV': '1', 'NO_COLOR': ''}, client=FakeClient()))
