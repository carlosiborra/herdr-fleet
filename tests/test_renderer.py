import unittest

from herdr_fleet.model import Fleet, build_rows
from herdr_fleet.renderer import View, render, changed_rows
from herdr_fleet.theme import Palette
from herdr_fleet.text import cell_width, strip_controls
from fixtures import agent, fleet


class RendererTests(unittest.TestCase):
    def test_attention_stays_pinned_while_tree_scrolls(self):
        f = Fleet()
        f.update([agent('w1:p%d' % i, title='Task %02d' % i) for i in range(30)], 0)
        view = View(f, build_rows(f), selected='agent:w1:p29', offset=20, now=10)
        lines = render(view, 80, 24, Palette(mode='none'))
        self.assertIn('NEEDS ATTENTION', lines[4])
        self.assertIn('Task 00', lines[5])
        self.assertIn('Task 20', '\n'.join(lines[4:-3]))

    def test_original_title_and_identity_in_selected_details(self):
        title = 'Project \u00b7 Build API | example.user \u00b7 3'
        f = Fleet()
        f.update([agent(title=title)], 0)
        rows = build_rows(f, tab_labels={'w1:t1': 'Project'}, username='example.user')
        lines = render(View(f, rows, selected='agent:w1:p1', now=10), 160, 24, Palette(mode='none'))
        self.assertIn('Build API', '\n'.join(lines[4:-3]))
        self.assertNotIn('example.user', '\n'.join(lines[4:-3]))
        self.assertIn(title, lines[-3])
        self.assertIn('w1:p1', lines[-2])

    def setUp(self):
        self.f = Fleet()
        self.f.update(fleet(), 0)

    def view(self, **kwargs):
        return View(self.f, build_rows(self.f), now=252, **kwargs)

    def test_widths_and_unicode(self):
        for width in (1, 10, 40, 80, 160):
            for height in (1, 4, 24):
                lines = render(self.view(), width, height, Palette(mode='none'))
                self.assertEqual(len(lines), height)
                self.assertTrue(all(cell_width(line) <= width for line in lines))
        self.assertIn('…', '\n'.join(render(self.view(), 40, 24, Palette(mode='none'))))

    def test_statuses_and_type_badges_without_color(self):
        text = '\n'.join(render(self.view(), 160, 30, Palette(mode='none')))
        for label in ('working', 'done', 'idle', 'blocked', 'unknown', '[CX]', '[CL]'):
            self.assertIn(label, text)
        self.assertNotIn('\x1b', text)
        self.assertIn('age ?', text)
        self.f.update([dict(a, state_change_seq=a.get('state_change_seq', 0) + 1) for a in fleet()], 252)
        text = '\n'.join(render(View(self.f, build_rows(self.f), now=260), 160, 30, Palette(mode='none')))
        self.assertIn('age 8s', text)

    def test_empty_error_and_filter(self):
        f = Fleet()
        view = View(f, (), error='Herdr unavailable; retrying', query='nomatch')
        text = '\n'.join(render(view, 80, 15, Palette(mode='none')))
        self.assertIn('Herdr unavailable', text)
        self.assertIn('No matching agents', text)

    def test_peek_responsive_and_sanitized(self):
        view = self.view(peek=('danger\x1b[2Jhidden\x1b]52;c;bad\x07', 'last line'),
                         peek_title='Selected agent')
        narrow = '\n'.join(render(view, 40, 24, Palette(mode='none')))
        medium = '\n'.join(render(view, 80, 24, Palette(mode='none')))
        wide = '\n'.join(render(view, 160, 24, Palette(mode='none')))
        self.assertNotIn('last line', narrow)
        self.assertIn('last line', medium)
        self.assertIn('last line', wide)
        self.assertNotIn('\x1b', wide)

    def test_row_diff_and_spinner(self):
        lines = render(self.view(), 80, 24, Palette(mode='none'))
        self.assertEqual(changed_rows(lines, lines), ())
        self.assertEqual(changed_rows(('a', 'b'), ('a', 'c')), ((1, 'c'),))
        next_lines = render(View(self.f, build_rows(self.f), now=252.3),
                            80, 24, Palette(mode='none'))
        differences = changed_rows(lines, next_lines)
        self.assertGreater(len(differences), 0)
        self.assertLess(len(differences), 10)

    def test_untrusted_titles_cannot_emit_controls(self):
        f = Fleet()
        f.update([agent(title='hello\x1b[31mred\r\nBAD\x1b]0;title\x07')], 0)
        text = '\n'.join(render(View(f, build_rows(f)), 80, 20, Palette(mode='none')))
        self.assertNotIn('\x1b', text)
        self.assertNotIn('\r', text)
        self.assertEqual(strip_controls('a\x1b[31mb'), 'ab')


if __name__ == '__main__':
    unittest.main()
