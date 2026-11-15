"""Read only the custom theme colors; no third-party TOML parser required."""
from dataclasses import dataclass, field
import re
from pathlib import Path


DEFAULT = dict(accent='#e6b450', text='#bfbdb6', subtext0='#8a8f98',
               selection_bg='#232a36', green='#70bf56', yellow='#f9af4f',
               red='#f26d78', blue='#53bdfa', mauve='#d0a1ff')


def read_colors(path):
    colors = dict(DEFAULT)
    try:
        source = path.read_text(encoding='utf-8')
    except (OSError, UnicodeError):
        return colors
    in_custom = False
    for line in source.splitlines():
        if line.strip().startswith('['):
            in_custom = line.strip() == '[theme.custom]'
        elif in_custom:
            match = re.fullmatch(r'\s*(\w+)\s*=\s*[\"\'](#[0-9a-fA-F]{6})[\"\']\s*(?:#.*)?', line)
            if match and match[1] in colors:
                colors[match[1]] = match[2]
    return colors


def config_path(env):
    base = env.get('XDG_CONFIG_HOME')
    root = Path(base) if base else Path.home() / '.config'
    return root / 'herdr' / 'config.toml'


def color_mode(env):
    if 'NO_COLOR' in env or env.get('TERM') == 'dumb':
        return 'none'
    if env.get('COLORTERM', '').lower() in ('truecolor', '24bit'):
        return 'truecolor'
    return '256'


def nearest_256(rgb):
    levels = (0, 95, 135, 175, 215, 255)
    indexes = [min(range(6), key=lambda i: abs(levels[i] - c)) for c in rgb]
    cube = 16 + 36 * indexes[0] + 6 * indexes[1] + indexes[2]
    gray = min(range(24), key=lambda i: sum((8 + i * 10 - c) ** 2 for c in rgb))
    cube_error = sum((levels[i] - c) ** 2 for i, c in zip(indexes, rgb))
    gray_error = sum((8 + gray * 10 - c) ** 2 for c in rgb)
    return 232 + gray if gray_error < cube_error else cube


@dataclass(frozen=True)
class Palette:
    mode: str = 'truecolor'
    colors: dict = field(default_factory=lambda: dict(DEFAULT))

    def paint(self, text, color='text', selected=False, bold=False):
        if self.mode == 'none':
            return text
        def escape(key, background=False):
            hex_value = self.colors.get(key, DEFAULT.get(key, DEFAULT['text']))
            rgb = tuple(int(hex_value[i:i + 2], 16) for i in (1, 3, 5))
            channel = 48 if background else 38
            return ('\x1b[%d;2;%d;%d;%dm' % ((channel,) + rgb)
                    if self.mode == 'truecolor' else '\x1b[%d;5;%dm' % (channel, nearest_256(rgb)))
        return escape(color) + (escape('selection_bg', True) if selected else '') + (
            '\x1b[1m' if bold else '') + text + '\x1b[0m'
