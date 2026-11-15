"""Safe terminal text and cell-aware clipping."""
import re
import unicodedata


ESCAPES = re.compile(r'\x1b(?:\][^\x07\x1b]*(?:\x07|\x1b\\)|\[[0-?]*[ -/]*[@-~]|[ -/]*[@-~])')


def strip_controls(value):
    value = ESCAPES.sub('', str(value))
    return ''.join(c for c in value if unicodedata.category(c) not in ('Cc', 'Cf', 'Cs'))


def char_width(c):
    if unicodedata.combining(c) or unicodedata.category(c) in ('Mn', 'Me'):
        return 0
    return 2 if unicodedata.east_asian_width(c) in ('W', 'F') else 1


def cell_width(value):
    return sum(char_width(c) for c in strip_controls(value))


def fit(value, width, pad=False):
    value = strip_controls(value)
    width = max(0, width)
    clipped = cell_width(value) > width
    budget = max(0, width - 1) if clipped else width
    out = []
    used = 0
    for c in value:
        size = char_width(c)
        if used + size > budget:
            break
        out.append(c)
        used += size
    if clipped and width:
        out.append('…')
        used += 1
    if pad:
        out.append(' ' * (width - used))
    return ''.join(out)
