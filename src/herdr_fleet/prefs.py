"""Persist only UI preferences, never data obtained from agents."""
from dataclasses import dataclass
import json
import math
import os
import re
import tempfile


def poll_seconds(value):
    if isinstance(value, bool):
        return 1.0
    try:
        number = float(value)
        return max(0.5, number) if math.isfinite(number) else 1.0
    except (TypeError, ValueError, OverflowError):
        return 1.0


def safe_groups(groups):
    if not isinstance(groups, (list, tuple, set, frozenset)):
        return frozenset()
    return frozenset(g for g in groups if isinstance(g, str) and
                     re.fullmatch(r'(?:workspace:w[0-9]+|tab:w[0-9]+:t[0-9]+)', g))


@dataclass(frozen=True)
class Preferences:
    poll_interval: float = 1.0
    collapsed: frozenset = frozenset()


def load(root):
    if root is None:
        return Preferences()
    try:
        value = json.loads((root / 'preferences.json').read_text(encoding='utf-8'))
        if isinstance(value, dict):
            return Preferences(poll_seconds(value.get('poll_interval', 1)),
                               safe_groups(value.get('collapsed', [])))
    except (OSError, ValueError, UnicodeError):
        pass
    return Preferences()


def save(root, prefs):
    if root is None:
        return
    root.mkdir(parents=True, exist_ok=True)
    value = dict(poll_interval=poll_seconds(prefs.poll_interval),
                 collapsed=sorted(safe_groups(prefs.collapsed)))
    fd, name = tempfile.mkstemp(prefix='.preferences-', dir=str(root))
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(value, stream)
            stream.write('\n')
        os.replace(name, root / 'preferences.json')
    finally:
        if os.path.exists(name):
            os.unlink(name)
