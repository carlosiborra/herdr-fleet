import tempfile
import unittest
from pathlib import Path

from herdr_fleet.app import Controller
from herdr_fleet.prefs import Preferences, load, save, poll_seconds
from herdr_fleet.terminal import KeyDecoder
from herdr_fleet.theme import color_mode, config_path, read_colors, Palette
from fixtures import agent, fleet


class AppTests(unittest.TestCase):
    def test_fuzzy_action_starts_navigation_and_enter_search_selects(self):
        c = Controller(Preferences(), search_mode='fuzzy')
        c.update(fleet(), 0)
        self.assertFalse(c.filtering)
        c.handle('/')
        for char in 'imapi':
            c.handle(char)
        self.assertIsNone(c.handle('enter'))
        self.assertFalse(c.filtering)
        self.assertEqual(c.query, 'imapi')
        self.assertEqual(c.handle('enter'), ('focus', 'w1:p1'))
        self.assertIsNone(c.handle('escape'))
        self.assertEqual(c.handle('escape'), ('quit', ''))

    def test_search_action_selects_idle_agent_before_group(self):
        c = Controller(Preferences(), search_mode='search')
        c.update(fleet(), 0)
        self.assertFalse(c.filtering)
        c.handle('j')
        self.assertEqual(c.query, '')
        c.handle('/')
        for char in 'Await':
            c.handle(char)
        self.assertIsNone(c.handle('enter'))
        self.assertFalse(c.filtering)
        self.assertEqual(c.handle('enter'), ('focus', 'w1:p3'))

    def test_deep_selection_and_return_to_pinned_attention(self):
        from herdr_fleet.renderer import View, render, body_geometry
        c = Controller(Preferences())
        c.update([agent('w1:p%d' % i, title='Task %02d' % i) for i in range(30)], 0)
        c.selected = 'agent:w1:p29'
        _, height, _ = body_geometry(View(c.fleet, c.rows()), 80, 24)
        c.ensure_visible(height)
        lines = render(View(c.fleet, c.rows(), c.selected, c.offset), 80, 24, Palette(mode='none'))
        self.assertTrue(any('› ' in line and 'Task 29' in line for line in lines[4:-3]))
        self.assertIn('Task 00', lines[5])
        c.selected = 'attention:w1:p0'
        c.ensure_visible(height)
        lines = render(View(c.fleet, c.rows(), c.selected, c.offset), 80, 24, Palette(mode='none'))
        self.assertIn('› ', lines[5])
        for small_height in (1, 4, 7):
            c.selected = 'agent:w1:p29'
            c.ensure_visible(small_height)
            self.assertGreaterEqual(c.offset, 0)

    def controller(self):
        c = Controller(Preferences())
        c.update(fleet(), 0)
        return c

    def test_select_focus_and_direct_jump(self):
        c = self.controller()
        self.assertEqual(c.handle('enter'), ('focus', 'w2:p2'))
        c.handle('j')
        self.assertEqual(c.handle('enter'), ('focus', 'w1:p2'))
        code = c.fleet.agents['w1:p3'].code
        self.assertIsNone(c.handle(code[0]))
        self.assertEqual(c.handle(code[1]), ('focus', 'w1:p3'))

    def test_enter_on_group_collapses_and_arrows_move(self):
        c = self.controller()
        c.selected = 'workspace:w1'
        self.assertIsNone(c.handle('enter'))
        self.assertIn('workspace:w1', c.collapsed)
        c.handle('right')
        self.assertNotIn('workspace:w1', c.collapsed)
        c.selected = 'agent:w1:p1'
        c.handle('left')
        self.assertEqual(c.selected, 'tab:w1:t1')
        self.assertIn('tab:w1:t1', c.collapsed)

    def test_filter_unicode_and_escape(self):
        c = self.controller()
        c.handle('/')
        for char in '界':
            c.handle(char)
        self.assertEqual(c.query, '界')
        self.assertTrue(any(r.agent and '界' in r.agent.title for r in c.rows()))
        c.handle('enter')
        self.assertFalse(c.filtering)
        c.handle('escape')
        self.assertEqual(c.handle('q'), ('quit', ''))

    def test_peek_toggle_selection_and_removal_discard(self):
        c = self.controller()
        self.assertEqual(c.handle('p'), ('peek', 'w2:p2'))
        c.receive_peek('w2:p2', ('private output',))
        self.assertEqual(c.peek, ('private output',))
        c.handle('j')
        self.assertIsNone(c.peek)
        c.receive_peek('w2:p2', ('late output',))
        self.assertIsNone(c.peek)
        c.handle('p')
        c.receive_peek('w2:p2', ('preview',))
        c.update([], 1)
        self.assertIsNone(c.peek)

    def test_changed_session_discards_peek(self):
        c = Controller(Preferences())
        c.update([agent()], 0)
        c.handle('p')
        c.receive_peek('w1:p1', ('preview',))
        c.update([agent(session='replacement')], 1)
        self.assertIsNone(c.peek)

    def test_preferences_allowlist_and_poll_floor(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prefs = Preferences(0.01, frozenset({'workspace:w1', 'tab:w1:t1'}))
            save(root, prefs)
            stored = (root / 'preferences.json').read_text()
            self.assertNotIn('cwd', stored)
            self.assertEqual(load(root).poll_interval, 0.5)
            (root / 'preferences.json').write_text('{"poll_interval": 1, "collapsed": ["private title", "workspace:w1"], "output": "secret"}')
            self.assertEqual(load(root).collapsed, frozenset({'workspace:w1'}))
            save(root, load(root))
            self.assertNotIn('secret', (root / 'preferences.json').read_text())
        for value in (float('nan'), float('inf'), 'bad', None, True):
            self.assertEqual(poll_seconds(value), 1)

    def test_incremental_keys_unicode_arrows_escape_and_interrupt(self):
        d = KeyDecoder()
        self.assertEqual(d.feed(b'\x1b['), ())
        self.assertEqual(d.feed(b'A'), ('up',))
        raw = '界'.encode()
        self.assertEqual(d.feed(raw[:1]), ())
        self.assertEqual(d.feed(raw[1:]), ('界',))
        self.assertEqual(d.feed(b'\x1b'), ())
        self.assertEqual(d.flush_escape(), ('escape',))
        self.assertEqual(d.feed(b'\r\x03\x7f'), ('enter', 'interrupt', 'backspace'))

    def test_theme_and_color_modes(self):
        self.assertEqual(color_mode({'NO_COLOR': ''}), 'none')
        self.assertEqual(color_mode({'COLORTERM': 'truecolor'}), 'truecolor')
        self.assertEqual(color_mode({'TERM': 'xterm-256color'}), '256')
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'theme.toml'
            path.write_text('[theme.custom]\naccent = "#123456"\n[other]\ntext = "#ffffff"\n')
            colors = read_colors(path)
            self.assertEqual(colors['accent'], '#123456')
            self.assertEqual(colors['text'], '#bfbdb6')
        self.assertIn(';5;', Palette(mode='256').paint('hello'))
        self.assertNotIn(';2;', Palette(mode='256').paint('hello'))


class ConfigPathTests(unittest.TestCase):
    def test_xdg_config_home_used_when_set(self):
        self.assertEqual(config_path({'XDG_CONFIG_HOME': '/xdg'}), Path('/xdg/herdr/config.toml'))

    def test_default_under_home_dot_config(self):
        self.assertEqual(config_path({}), Path.home() / '.config' / 'herdr' / 'config.toml')
        self.assertEqual(config_path({'XDG_CONFIG_HOME': ''}),
                         Path.home() / '.config' / 'herdr' / 'config.toml')
