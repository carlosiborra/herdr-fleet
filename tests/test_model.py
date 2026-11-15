import unittest

from herdr_fleet.model import Fleet, build_rows, elapsed, clean_title
from fixtures import agent, fleet


class ModelTests(unittest.TestCase):
    def test_clean_title_keeps_meaningful_segments_and_original_data(self):
        title = 'Project \u00b7 Build API | example.user \u00b7 3'
        self.assertEqual(clean_title(title, 'Project', 'example.user'), 'Build API')
        self.assertEqual(clean_title('Project | Build | Test', 'Project'), 'Build | Test')
        self.assertEqual(clean_title('Benchmark | 3', 'Other'), 'Benchmark | 3')
        self.assertEqual(clean_title('Build | other.user', '', 'example.user'), 'Build | other.user')
        f = Fleet()
        f.update([agent(title=title)], 0)
        rows = build_rows(f, tab_labels={'w1:t1': 'Project'}, username='example.user')
        self.assertEqual(next(r.label for r in rows if r.kind == 'agent'), 'Build API')
        self.assertIn('Project', next(r.label for r in rows if r.kind == 'attention'))
        self.assertEqual(f.agents['w1:p1'].agent.title, title)

    def test_tab_badge_counts_agents(self):
        f = Fleet()
        f.update([agent(), agent('w1:p2', 'idle')], 0)
        tabs = [r for r in build_rows(f, tab_labels={'w1:t1': 'Project'}) if r.kind == 'tab']
        self.assertEqual(tabs[0].label, 'Project  [2 agents]')

    def test_fuzzy_matches_subsequences_and_ranks_closest_first(self):
        from herdr_fleet.search import fuzzy_score
        self.assertIsNotNone(fuzzy_score('bapi', 'Build API'))
        self.assertIsNone(fuzzy_score('xyz', 'Build API'))
        f = Fleet()
        f.update([agent(title='broad application interface'),
                  agent('w1:p2', title='bapi')], 0)
        rows = build_rows(f, query='bapi', match_mode='fuzzy')
        self.assertEqual([r.agent.pane_id for r in rows], ['w1:p2', 'w1:p1'])
        self.assertEqual(build_rows(f, query='xyz', match_mode='fuzzy'), ())
        self.assertEqual(len(build_rows(f, match_mode='fuzzy')), 2)

    def test_empty(self):
        f = Fleet()
        f.update([], 0)
        self.assertEqual(build_rows(f), ())

    def test_tree_groups_and_attention(self):
        f = Fleet()
        f.update(fleet(), 0)
        rows = build_rows(f, workspace_labels={'w1': 'Engineering'})
        self.assertEqual([r.key for r in rows if r.kind == 'workspace'],
                         ['workspace:w1', 'workspace:w2', 'workspace:w3'])
        self.assertEqual([r.key for r in rows if r.kind == 'attention'],
                         ['attention:w2:p2', 'attention:w1:p2',
                          'attention:w1:p1', 'attention:w2:p1'])
        self.assertIn('Engineering', next(r.label for r in rows if r.kind == 'workspace'))

    def test_blocked_agent_is_pinned_before_completed_ones(self):
        f = Fleet()
        f.update([agent('w1:p%d' % index, 'done', tab='w1:t1', seq=index)
                  for index in range(5)] + [agent('w2:p1', 'blocked', 'w2', 'w2:t1')], 0)
        pinned = [r.key for r in build_rows(f) if r.kind == 'attention']
        self.assertEqual(pinned[0], 'attention:w2:p1')

    def test_stable_order_despite_payload_and_status_changes(self):
        f = Fleet()
        original = [agent(), agent('w1:p2', 'idle')]
        f.update(original, 10)
        codes = {k: v.code for k, v in f.agents.items()}
        changed = [agent('w1:p2', 'working', seq=2), agent(status='done', seq=2)]
        f.update(changed, 20)
        self.assertEqual([r.agent.pane_id for r in build_rows(f) if r.kind == 'agent'],
                         ['w1:p1', 'w1:p2'])
        self.assertEqual({k: v.code for k, v in f.agents.items()}, codes)

    def test_observed_age_and_transition_highlight(self):
        f = Fleet()
        f.update([agent()], 10)
        self.assertFalse(f.agents['w1:p1'].transition_seen)
        self.assertEqual(f.agents['w1:p1'].since, 10)
        f.update([agent(title='New title')], 25)
        self.assertEqual(f.agents['w1:p1'].since, 10)
        f.update([agent(status='done', seq=2)], 30)
        self.assertTrue(f.agents['w1:p1'].transition_seen)
        self.assertEqual(f.agents['w1:p1'].since, 30)
        self.assertGreater(f.agents['w1:p1'].highlight_until, 30)
        self.assertEqual(elapsed(252), '4m12s')

    def test_session_replacement_and_sequence_only_transition(self):
        f = Fleet()
        f.update([agent()], 1)
        f.update([agent(seq=2)], 4)
        self.assertEqual(f.agents['w1:p1'].since, 4)
        f.update([agent(seq=2, session='new')], 8)
        self.assertFalse(f.agents['w1:p1'].transition_seen)
        self.assertEqual(f.agents['w1:p1'].since, 8)

    def test_filter_and_collapse_keep_ancestors(self):
        f = Fleet()
        f.update(fleet(), 0)
        rows = build_rows(f, collapsed={'workspace:w1'}, query='claude')
        self.assertTrue(any(r.kind == 'agent' for r in rows))
        self.assertEqual([r.key for r in rows if r.kind == 'workspace'], ['workspace:w1'])
        rows = build_rows(f, collapsed={'workspace:w1'})
        self.assertFalse(any(r.kind == 'agent' and r.agent.workspace_id == 'w1' for r in rows))
        rows = build_rows(f, query='engineering', workspace_labels={'w1': 'Engineering'})
        self.assertEqual(sum(r.kind == 'agent' for r in rows), 3)

    def test_invalid_update_is_atomic_and_removed_agents_disappear(self):
        f = Fleet()
        f.update([agent()], 1)
        with self.assertRaises(ValueError):
            f.update([agent(), {'pane_id': 'bad'}], 2)
        self.assertEqual(len(f.agents), 1)
        with self.assertRaises(ValueError):
            f.update([agent(), agent()], 3)
        f.update([], 4)
        self.assertEqual(f.agents, {})

    def test_jump_codes_are_unique_stable_and_reuse_removed_slots(self):
        f = Fleet()
        f.update([agent('w1:p%d' % i) for i in range(35)], 0)
        self.assertEqual(len({o.code for o in f.agents.values()}), 35)
        survivor = f.agents['w1:p34'].code
        f.update([agent('w1:p34'), agent('w1:p99')], 1)
        self.assertEqual(f.agents['w1:p34'].code, survivor)
        self.assertEqual(f.agents['w1:p99'].code, 'AA')


if __name__ == '__main__':
    unittest.main()
