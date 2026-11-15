import json
import os
import subprocess
import unittest

from herdr_fleet.client import HerdrClient, HerdrError


class FakeRunner:
    def __init__(self, result=None, output=None, returncode=0, exception=None):
        self.result = result or {}
        self.output = output
        self.returncode = returncode
        self.exception = exception
        self.calls = []

    def __call__(self, argv, **kwargs):
        self.calls.append((argv, kwargs))
        if self.exception:
            raise self.exception
        stdout = self.output if self.output is not None else json.dumps({'result': self.result})
        return subprocess.CompletedProcess(argv, self.returncode, stdout, 'private diagnostic')


class ClientTests(unittest.TestCase):
    def test_list_single_call_with_timeout_no_shell(self):
        runner = FakeRunner({'agents': []})
        self.assertEqual(HerdrClient(runner=runner).agents(), [])
        self.assertEqual(runner.calls[0][0], ['herdr', 'agent', 'list'])
        self.assertEqual(runner.calls[0][1]['timeout'], 2)
        self.assertNotIn('shell', runner.calls[0][1])

    def test_peek_is_explicit_bounded_plain_text(self):
        runner = FakeRunner(output='\n'.join(str(i) for i in range(30)))
        lines = HerdrClient(runner=runner).peek('w1:p1')
        self.assertEqual(len(lines), 15)
        self.assertEqual(lines[-1], '29')
        self.assertEqual(runner.calls[0][0], ['herdr', 'agent', 'read', 'w1:p1',
                                            '--source', 'recent-unwrapped', '--lines', '15', '--format', 'text'])
        with self.assertRaises(HerdrError):
            HerdrClient(runner=runner).peek('-option')

    def test_fuzzy_launcher_passes_mode_only_to_its_own_pane(self):
        runner = FakeRunner({'plugin_pane': {}})
        HerdrClient(runner=runner).open_dashboard('fuzzy')
        self.assertEqual(runner.calls[0][0][-2:], ['--env', 'HERDR_FLEET_SEARCH_MODE=fuzzy'])


    def test_focus_is_only_agent_mutation(self):
        runner = FakeRunner({'agent': {'pane_id': 'w1:p1'}})
        HerdrClient(runner=runner).focus('w1:p1')
        self.assertEqual(runner.calls[0][0], ['herdr', 'agent', 'focus', 'w1:p1'])
        for target in ('', '-option', 'w1:p1\nBAD'):
            with self.assertRaises(HerdrError):
                HerdrClient(runner=runner).focus(target)

    def test_bad_json_timeout_and_server_failure_are_safe(self):
        for runner in (FakeRunner(output='invalid'), FakeRunner(output='[]'),
                       FakeRunner(output='{}'), FakeRunner(returncode=1),
                       FakeRunner(exception=subprocess.TimeoutExpired('herdr', 2)),
                       FakeRunner(exception=OSError('missing'))):
            with self.assertRaises(HerdrError) as raised:
                HerdrClient(runner=runner).agents()
            self.assertNotIn('private diagnostic', str(raised.exception))

    def test_snapshot_labels_only(self):
        runner = FakeRunner({'snapshot': {'workspaces': [{'workspace_id': 'w1', 'label': 'Work'}],
                                         'tabs': [{'tab_id': 'w1:t1', 'label': 'API'}]}})
        self.assertEqual(HerdrClient(runner=runner).labels(), ({'w1': 'Work'}, {'w1:t1': 'API'}))


class PluginIdTests(unittest.TestCase):
    def open_args(self, **kwargs):
        runner = FakeRunner({})
        HerdrClient(runner=runner, **kwargs).open_dashboard()
        return runner.calls[0][0]

    def test_plugin_id_from_environment(self):
        old = os.environ.get('HERDR_PLUGIN_ID')
        os.environ['HERDR_PLUGIN_ID'] = 'custom-id'
        try:
            argv = self.open_args()
        finally:
            if old is None:
                del os.environ['HERDR_PLUGIN_ID']
            else:
                os.environ['HERDR_PLUGIN_ID'] = old
        self.assertEqual(argv[argv.index('--plugin') + 1], 'custom-id')

    def test_plugin_id_explicit_and_fallback(self):
        argv = self.open_args(plugin_id='explicit')
        self.assertEqual(argv[argv.index('--plugin') + 1], 'explicit')
        old = os.environ.pop('HERDR_PLUGIN_ID', None)
        try:
            argv = self.open_args()
        finally:
            if old is not None:
                os.environ['HERDR_PLUGIN_ID'] = old
        self.assertEqual(argv[argv.index('--plugin') + 1], 'herdr-fleet')
