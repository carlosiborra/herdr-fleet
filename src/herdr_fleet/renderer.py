"""Pure, cell-bounded frames. Terminal writes belong to the app."""
from dataclasses import dataclass

from .model import elapsed, row_sections
from .text import fit, cell_width
from .theme import Palette


@dataclass(frozen=True)
class View:
    fleet: object
    rows: tuple
    selected: str = ''
    offset: int = 0
    now: float = 0
    error: str = ''
    query: str = ''
    filtering: bool = False
    jump: str = ''
    peek: object = None
    peek_title: str = ''
    poll_interval: float = 1
    search_mode: str = 'tree'


def body_geometry(view, width, height):
    top = 4 + bool(view.error)
    bottom = 3 if height >= 10 else 1
    available = max(0, height - top - bottom)
    peek_height = min(16, available // 2) if view.peek is not None and 60 <= width < 120 else 0
    return top, max(0, available - peek_height), peek_height


def agent_parts(row, width, now):
    a = row.agent
    glyph = {'done': '✓', 'idle': '○', 'blocked': '!', 'unknown': '?',
             'working': '◴◷◶◵'[int(now * 4) % 4]}[a.status]
    badge = {'claude': 'CL', 'codex': 'CX'}.get(a.kind, 'AG')
    prefix = row.prefix + row.observed.code + ' ' + glyph + ' [' + badge + '] '
    state = a.status if width >= 60 else {'working': 'work', 'blocked': 'block', 'unknown': '?'}.get(a.status, a.status)
    duration = elapsed(now - row.observed.since) if row.observed.transition_seen else '?'
    right = ' ' + state + ' age ' + duration if width >= 60 else ' ' + duration
    title_width = max(0, width - cell_width(prefix) - cell_width(right))
    prefix = fit(prefix, width)
    title = fit(row.label or a.title, title_width, pad=True)
    right = fit(right, max(0, width - cell_width(prefix) - cell_width(title)), pad=True)
    return prefix, title, right


def render(view, width, height, palette=None):
    palette = palette or Palette()
    width, height = max(1, width), max(1, height)
    totals = view.fleet.totals()
    counts = '  '.join('%d %s' % (totals[s], s) for s in totals if totals[s]) or '0 agents'
    title = 'AGENT FLEET  |  ' + counts
    if view.search_mode == 'fuzzy':
        title = 'AGENT SEARCH  |  ' + counts
    if width < 75:
        short = {'working': 'work', 'done': 'done', 'idle': 'idle', 'blocked': 'block', 'unknown': '?'}
        title = ('FUZZY  ' if view.search_mode == 'fuzzy' else 'FLEET  ') + ' '.join(
            '%d%s' % (totals[s], short[s]) for s in totals if totals[s])
    lines = [palette.paint(fit(title, width, True), 'accent', bold=True),
             palette.paint(fit('Live session  |  age ? = start time unknown  |  AA..ZZ jump',
                               width, True), 'subtext0'),
             palette.paint(fit('/ ' + view.query + ('▏' if view.filtering else '') +
                               ('  jump ' + view.jump + '_' if view.jump else ''), width, True), 'blue'),
             palette.paint('─' * width, 'subtext0')]
    if view.error:
        lines.append(palette.paint(fit('! ' + view.error, width, True), 'red'))
    _, body_height, peek_height = body_geometry(view, width, height)
    side = view.peek is not None and width >= 120
    tree_width = width - min(60, width // 3) - 3 if side else width
    pinned, tree = row_sections(view.rows, body_height)
    tree_height = max(0, body_height - len(pinned))
    visible = pinned + tree[view.offset:view.offset + tree_height]
    body = []
    for row in visible:
        selected = row.key == view.selected
        if row.agent:
            color = {'working': 'yellow', 'done': 'green', 'idle': 'subtext0',
                     'blocked': 'red', 'unknown': 'subtext0'}[row.agent.status]
            highlight = row.observed.highlight_until > view.now
            parts = agent_parts(row, max(0, tree_width - 2), view.now)
            marker = fit('› ' if selected else '  ', tree_width)
            body.append(palette.paint(marker, color, selected) +
                        palette.paint(parts[0], color, selected, highlight) +
                        palette.paint(parts[1], 'text', selected, selected) +
                        palette.paint(parts[2], 'subtext0', selected))
            continue
        else:
            text = fit(row.prefix + ('▾ ' if row.expanded else '▸ ') + row.label
                       if row.kind in ('workspace', 'tab') else row.label,
                       max(0, tree_width - 2), True)
            color = 'accent' if row.kind == 'workspace' else 'subtext0'
            highlight = False
        body.append(palette.paint(fit(('› ' if selected else '  ') + text, tree_width, True),
                                  color, selected, row.kind == 'workspace'))
    if not body and body_height:
        body.append(palette.paint(fit('No matching agents' if view.query else 'No coding agents running',
                                      tree_width, True), 'subtext0'))
    body.extend(' ' * tree_width for _ in range(max(0, body_height - len(body))))
    if side:
        panel_width = width - tree_width - 3
        preview = ['PEEK  ' + view.peek_title] + list(view.peek or ())
        body = [line + palette.paint(' │ ', 'subtext0') +
                palette.paint(fit(preview[i] if i < len(preview) else '', panel_width, True),
                              'blue' if i == 0 else 'text') for i, line in enumerate(body)]
    lines.extend(body)
    if peek_height:
        preview = ['PEEK  ' + view.peek_title] + list(view.peek or ())[-max(0, peek_height - 1):]
        lines.extend(palette.paint(fit(preview[i] if i < len(preview) else '', width, True),
                                   'blue' if i == 0 else 'text') for i in range(peek_height))
    if height >= 10:
        selected = next((r for r in view.rows if r.key == view.selected), None)
        if selected and selected.agent:
            a = selected.agent
            detail = '%s / %s / %s | %s | %s age %s | %s' % (
                a.workspace_id, a.tab_id, a.pane_id, a.kind, a.status,
                elapsed(view.now - selected.observed.since) if selected.observed.transition_seen else 'unknown', a.cwd)
            lines.append(palette.paint(fit('TITLE  ' + a.title, width, True), 'text'))
            lines.append(palette.paint(fit(detail, width, True), 'subtext0'))
        else:
            lines.extend([' ' * width, ' ' * width])
    footer = ('j/k move  h/l fold  Enter focus  p peek  / filter  q/Esc close'
              if width >= 75 else 'j/k ↑↓  Enter go  h/l fold  p / q')
    if view.filtering and view.search_mode in ('search', 'fuzzy'):
        footer = 'Type query  Ctrl-N/P or ↑↓ select  Enter select  Esc navigate'
    lines.append(palette.paint(fit(footer, width, True), 'subtext0'))
    return tuple(lines[:height] + [' ' * width] * max(0, height - len(lines)))


def changed_rows(previous, current):
    return tuple((i, line) for i, line in enumerate(current)
                 if i >= len(previous) or previous[i] != line)
