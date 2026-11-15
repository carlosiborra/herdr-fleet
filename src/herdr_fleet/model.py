"""Pure agent identity, observation clocks and stable tree construction."""
from dataclasses import dataclass
import json
import re
from .search import fuzzy_score


STATUSES = ('working', 'done', 'idle', 'blocked', 'unknown')


@dataclass(frozen=True)
class Agent:
    pane_id: str
    workspace_id: str
    tab_id: str
    kind: str
    status: str
    title: str
    cwd: str
    seq: int
    session: str
    focused: bool


def parse_agent(value):
    if not isinstance(value, dict):
        raise ValueError('Invalid agent record')
    for key in ('pane_id', 'workspace_id', 'tab_id'):
        if not isinstance(value.get(key), str) or not value[key]:
            raise ValueError('Invalid agent identity')
    status = value.get('agent_status')
    seq = value.get('state_change_seq', 0)
    if status not in STATUSES or type(seq) is not int or seq < 0:
        raise ValueError('Invalid agent state')
    for key in ('agent', 'terminal_title_stripped', 'cwd'):
        if value.get(key) is not None and not isinstance(value[key], str):
            raise ValueError('Invalid agent text')
    return Agent(value['pane_id'], value['workspace_id'], value['tab_id'],
                 value.get('agent') or 'agent', status,
                 value.get('terminal_title_stripped') or 'Untitled agent',
                 value.get('cwd') or '', seq,
                 json.dumps(value.get('agent_session'), sort_keys=True),
                 value.get('focused') is True)


@dataclass(frozen=True)
class Observed:
    agent: Agent
    since: float
    highlight_until: float
    rank: int
    code: str
    transition_seen: bool = False


class Fleet:
    def __init__(self):
        self.agents = {}
        self._rank = 0

    def update(self, payload, now):
        if not isinstance(payload, list):
            raise ValueError('Agent list is not an array')
        parsed = [parse_agent(a) for a in payload]
        if len({a.pane_id for a in parsed}) != len(parsed):
            raise ValueError('Duplicate agent pane identity')
        retained = {a.pane_id for a in parsed}
        used = {o.code for p, o in self.agents.items() if p in retained}
        available = (chr(65 + i // 26) + chr(65 + i % 26)
                     for i in range(26 * 26))
        codes = (code for code in available if code not in used)
        updated = {}
        for a in parsed:
            old = self.agents.get(a.pane_id)
            if old:
                changed = (a.seq, a.status, a.kind, a.session) != (
                    old.agent.seq, old.agent.status, old.agent.kind, old.agent.session)
                updated[a.pane_id] = Observed(a, now if changed else old.since,
                                             now + 2 if changed else old.highlight_until,
                                             old.rank, old.code,
                                             (old.transition_seen or changed) if a.session == old.agent.session else False)
            else:
                updated[a.pane_id] = Observed(a, now, 0, self._rank, next(codes, ''))
                self._rank += 1
        self.agents = updated

    def ordered(self):
        return tuple(sorted(self.agents.values(), key=lambda o: o.rank))

    def totals(self):
        return {s: sum(o.agent.status == s for o in self.agents.values()) for s in STATUSES}


@dataclass(frozen=True)
class Row:
    key: str
    kind: str
    label: str = ''
    prefix: str = ''
    observed: object = None
    expanded: bool = True

    @property
    def agent(self):
        return self.observed.agent if self.observed else None


def count_badge(agents):
    return ', '.join('%d %s' % (sum(o.agent.status == s for o in agents), s)
                     for s in STATUSES if any(o.agent.status == s for o in agents))


def clean_title(title, tab_label='', username=''):
    """Remove only recognized display metadata; retain the source title."""
    value = title.strip()
    decorated = False
    if tab_label:
        prefix = re.match(r'^' + re.escape(tab_label) + r'\s*(?:\u00b7|\|)\s*', value)
        if prefix and value[prefix.end():].strip():
            value = value[prefix.end():].strip()
            decorated = True
    without_number = re.sub(r'\s*(?:\u00b7|\|)\s*\d+$', '', value).strip()
    if username:
        owner = re.search(r'\s*\|\s*' + re.escape(username) + r'$', without_number)
        if owner and without_number[:owner.start()].strip():
            return without_number[:owner.start()].strip()
    return (without_number if decorated else value) or title


def row_sections(rows, height):
    """Pin attention only when enough rows remain for tree navigation."""
    count = next((i for i, row in enumerate(rows) if row.kind == 'workspace'), len(rows))
    if height >= 8 and count and count < len(rows):
        return rows[:count], rows[count:]
    return (), rows


def build_rows(fleet, collapsed=frozenset(), query='', workspace_labels=None,
               tab_labels=None, attention_limit=4, username='', match_mode='substring'):
    workspace_labels = workspace_labels or {}
    tab_labels = tab_labels or {}
    query = query.casefold()
    if match_mode == 'fuzzy':
        results = []
        for o in fleet.ordered():
            tab = tab_labels.get(o.agent.tab_id, '')
            title = clean_title(o.agent.title, tab, username)
            fields = (title, o.agent.title, tab, o.agent.kind, o.agent.cwd,
                      o.agent.workspace_id, workspace_labels.get(o.agent.workspace_id, ''))
            scores = [score for score in (fuzzy_score(query, text) for text in fields + (' '.join(fields),))
                      if score is not None]
            if scores:
                results.append((min(scores), o.rank, Row('agent:' + o.agent.pane_id, 'agent',
                                                        (tab + ': ' if tab else '') + title, observed=o)))
        return tuple(item[2] for item in sorted(results, key=lambda item: item[:2]))
    matching = [o for o in fleet.ordered() if not query or query in ' '.join((
        o.agent.title, o.agent.kind, o.agent.workspace_id,
        workspace_labels.get(o.agent.workspace_id, ''),
        tab_labels.get(o.agent.tab_id, ''))).casefold()]
    if not matching:
        return ()
    attention = sorted((o for o in matching if o.agent.status in ('done', 'blocked', 'working')),
                       key=lambda o: (('blocked', 'done', 'working').index(o.agent.status), o.rank))
    rows = []
    if attention:
        rows.append(Row('attention-summary', 'separator',
                        'NEEDS ATTENTION %d%s' % (len(attention),
                         ' | +%d in tree' % (len(attention) - attention_limit)
                         if len(attention) > attention_limit else '')))
        for o in attention[:attention_limit]:
            tab = tab_labels.get(o.agent.tab_id, '')
            title = clean_title(o.agent.title, tab, username)
            label = (tab + ': ' if tab else '') + title
            rows.append(Row('attention:' + o.agent.pane_id, 'attention', label, observed=o))
    workspaces = {}
    for o in matching:
        workspaces.setdefault(o.agent.workspace_id, {}).setdefault(o.agent.tab_id, []).append(o)
    for w, tabs in workspaces.items():
        key = 'workspace:' + w
        expanded = bool(query) or key not in collapsed
        agents = [o for group in tabs.values() for o in group]
        rows.append(Row(key, 'workspace', workspace_labels.get(w, w) + '  [' + count_badge(agents) + ']',
                        expanded=expanded))
        if not expanded:
            continue
        for ti, (tab, agents) in enumerate(tabs.items()):
            last_tab = ti == len(tabs) - 1
            key = 'tab:' + tab
            expanded = bool(query) or key not in collapsed
            label = '%s  [%d %s]' % (tab_labels.get(tab, tab), len(agents),
                                     'agent' if len(agents) == 1 else 'agents')
            rows.append(Row(key, 'tab', label,
                            '└─ ' if last_tab else '├─ ', expanded=expanded))
            if expanded:
                for i, o in enumerate(agents):
                    prefix = ('   ' if last_tab else '│  ') + ('└─ ' if i == len(agents) - 1 else '├─ ')
                    rows.append(Row('agent:' + o.agent.pane_id, 'agent',
                                    clean_title(o.agent.title, tab_labels.get(tab, ''), username),
                                    prefix=prefix, observed=o))
    return tuple(rows)


def elapsed(seconds):
    seconds = max(0, int(seconds))
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return '%dh%02dm' % (hours, minutes) if hours else (
        '%dm%02ds' % (minutes, seconds) if minutes else '%ds' % seconds)
