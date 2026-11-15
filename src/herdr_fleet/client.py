"""Timeout-bound CLI allowlist. Never inject input or retain agent output."""
import json
import os
import re
import subprocess


class HerdrError(RuntimeError):
    pass


class HerdrClient:
    def __init__(self, binary='herdr', timeout_seconds=2, runner=subprocess.run, plugin_id=None):
        self.binary = binary
        self.plugin_id = plugin_id or os.environ.get('HERDR_PLUGIN_ID') or 'herdr-fleet'
        self.timeout = timeout_seconds
        self.runner = runner

    def _output(self, args):
        try:
            completed = self.runner([self.binary] + list(args), text=True,
                                    capture_output=True, timeout=self.timeout, check=False)
        except subprocess.TimeoutExpired as exc:
            raise HerdrError('HerdR timed out; retrying') from exc
        except OSError as exc:
            raise HerdrError('HerdR unreachable; retrying') from exc
        if completed.returncode:
            # Raw diagnostics can contain sensitive content. Keep UI errors generic.
            raise HerdrError('HerdR command failed; retrying')
        return completed.stdout

    def _run(self, args):
        try:
            payload = json.loads(self._output(args))
        except (TypeError, ValueError) as exc:
            raise HerdrError('HerdR returned invalid JSON; retrying') from exc
        if not isinstance(payload, dict) or not isinstance(payload.get('result'), dict):
            raise HerdrError('HerdR returned an invalid response; retrying')
        return payload['result']

    @staticmethod
    def _target(target):
        if not isinstance(target, str) or not re.fullmatch(r'w[0-9]+:p[0-9]+', target):
            raise HerdrError('Invalid agent pane identity')
        return target

    def agents(self):
        agents = self._run(('agent', 'list')).get('agents')
        if not isinstance(agents, list):
            raise HerdrError('HerdR returned an invalid agent list; retrying')
        return agents

    def labels(self):
        snapshot = self._run(('api', 'snapshot')).get('snapshot')
        if not isinstance(snapshot, dict):
            raise HerdrError('Workspace labels unavailable')
        labels = []
        for field, key in (('workspaces', 'workspace_id'), ('tabs', 'tab_id')):
            entries = snapshot.get(field)
            if not isinstance(entries, list):
                raise HerdrError('Workspace labels unavailable')
            if any(not isinstance(e, dict) or not isinstance(e.get(key), str)
                   or not isinstance(e.get('label'), str) for e in entries):
                raise HerdrError('Workspace labels unavailable')
            labels.append({e[key]: e['label'] for e in entries})
        return tuple(labels)

    def peek(self, target):
        text = self._output(('agent', 'read', self._target(target), '--source',
                             'recent-unwrapped', '--lines', '15', '--format', 'text'))
        return tuple(text.splitlines()[-15:])

    def focus(self, target):
        return self._run(('agent', 'focus', self._target(target)))

    def open_dashboard(self, mode='tree'):
        # This launches only our own pane. It does not change any existing agent pane.
        args = ['plugin', 'pane', 'open', '--plugin', self.plugin_id,
                '--entrypoint', 'dashboard', '--focus']
        if mode in ('search', 'fuzzy'):
            args += ['--env', 'HERDR_FLEET_SEARCH_MODE=' + mode]
        self._run(args)
