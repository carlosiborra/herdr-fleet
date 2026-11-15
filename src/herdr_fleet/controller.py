"""Selection and keyboard behavior, independent of terminal and subprocesses."""
from .model import Fleet, build_rows, row_sections
from .prefs import poll_seconds


class Controller:
    def __init__(self, prefs, username='', search_mode='tree'):
        self.fleet = Fleet()
        self.collapsed = set(prefs.collapsed)
        self.poll_interval = poll_seconds(prefs.poll_interval)
        self.workspace_labels, self.tab_labels = {}, {}
        self.selected = ''
        self.offset = 0
        self.query = ''
        self.filtering = False
        self.search_mode = search_mode
        self.jump = ''
        self.peek = None
        self.peek_target = None
        self.peek_identity = None
        self.peek_generation = 0
        self.error = ''
        self.username = username

    def rows(self):
        return build_rows(self.fleet, self.collapsed, self.query,
                          self.workspace_labels, self.tab_labels, username=self.username,
                          match_mode='fuzzy' if self.search_mode == 'fuzzy' else 'substring')

    def selectable(self):
        return tuple(r for r in self.rows() if r.kind != 'separator')

    def reconcile(self):
        rows = self.selectable()
        if self.selected not in {r.key for r in rows}:
            preferred = next((r for r in rows if r.agent), None) if self.search_mode == 'search' and self.filtering else None
            self.selected = preferred.key if preferred else rows[0].key if rows else ''
            self.discard_peek()

    def update(self, payload, now):
        self.fleet.update(payload, now)
        if self.peek_target:
            current = self.fleet.agents.get(self.peek_target)
            if not current or (current.agent.session, current.agent.kind) != self.peek_identity:
                self.discard_peek()
        self.reconcile()

    def discard_peek(self):
        self.peek = None
        self.peek_target = self.peek_identity = None
        self.peek_generation += 1

    def receive_peek(self, target, lines):
        if target == self.peek_target:
            self.peek = lines

    def selected_row(self):
        return next((r for r in self.selectable() if r.key == self.selected), None)

    def handle(self, key):
        if key == 'interrupt':
            return ('quit', '')
        if self.filtering:
            if key in ('up', 'down', '\x0e', '\x10'):
                self.move('down' if key == '\x0e' else 'up' if key == '\x10' else key)
                return None
            if key == 'enter':
                self.filtering = False
            elif key == 'escape':
                self.filtering, self.query = False, ''
            elif key == 'backspace':
                self.query = self.query[:-1]
                self.selected = ''
            elif len(key) == 1 and key.isprintable():
                self.query += key
                self.selected = ''
            self.discard_peek()
            self.reconcile()
            return None
        if key in ('q', 'escape'):
            if key == 'q':
                return ('quit', '')
            if self.jump:
                self.jump = ''
                return None
            if self.query:
                self.query = ''
                self.reconcile()
                return None
            return ('quit', '')
        if len(key) == 1 and 'A' <= key <= 'Z':
            self.jump += key
            if len(self.jump) == 2:
                code, self.jump = self.jump, ''
                target = next((o.agent.pane_id for o in self.fleet.agents.values()
                               if o.code == code), None)
                if target:
                    return ('focus', target)
                self.error = 'No agent has that jump code'
            return None
        self.jump = ''
        if key == '/':
            self.filtering = True
            return None
        rows = self.selectable()
        row = self.selected_row()
        if key in ('j', 'k', 'up', 'down') and rows:
            self.move(key)
        elif row and key in ('h', 'left', 'l', 'right', 'enter'):
            if row.agent and key == 'enter':
                return ('focus', row.agent.pane_id)
            if row.kind in ('workspace', 'tab'):
                if key in ('l', 'right') or (key == 'enter' and not row.expanded):
                    self.collapsed.discard(row.key)
                elif key in ('h', 'left', 'enter'):
                    self.collapsed.add(row.key)
            elif row.agent and key in ('h', 'left'):
                self.selected = 'tab:' + row.agent.tab_id
                self.collapsed.add(self.selected)
            self.discard_peek()
            self.reconcile()
        elif row and row.agent and key == 'p':
            if self.peek_target == row.agent.pane_id:
                self.discard_peek()
            else:
                self.discard_peek()
                self.peek_target = row.agent.pane_id
                self.peek_identity = (row.agent.session, row.agent.kind)
                self.peek = ('Loading preview...',)
                return ('peek', row.agent.pane_id)
        return None

    def move(self, key):
        rows = self.selectable()
        if not rows:
            return
        index = next((i for i, r in enumerate(rows) if r.key == self.selected), 0)
        index = max(0, min(len(rows) - 1, index + (1 if key in ('j', 'down') else -1)))
        if self.selected != rows[index].key:
            self.discard_peek()
        self.selected = rows[index].key

    def ensure_visible(self, height):
        pinned, rows = row_sections(self.rows(), height)
        height = max(1, height - len(pinned))
        if self.selected in {r.key for r in pinned}:
            self.offset = min(self.offset, max(0, len(rows) - height))
            return
        index = next((i for i, r in enumerate(rows) if r.key == self.selected), 0)
        if index < self.offset:
            self.offset = index
        elif index >= self.offset + max(1, height):
            self.offset = max(0, index - max(1, height) + 1)
        self.offset = min(self.offset, max(0, len(rows) - max(1, height)))
