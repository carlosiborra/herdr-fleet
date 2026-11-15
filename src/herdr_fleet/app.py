"""One-worker polling loop with responsive input and changed-row output."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import sys
import time

from .client import HerdrClient, HerdrError
from .controller import Controller
from .prefs import Preferences, load, save, poll_seconds
from .renderer import View, render, changed_rows, body_geometry
from .terminal import Terminal, TerminalExit
from .theme import Palette, color_mode, config_path, read_colors


def make_view(controller, now):
    target = controller.fleet.agents.get(controller.peek_target)
    return View(controller.fleet, controller.rows(), controller.selected, controller.offset,
                now, controller.error, controller.query, controller.filtering, controller.jump,
                controller.peek, target.agent.title if target else '', controller.poll_interval,
                controller.search_mode)


def run(controller, client, terminal, palette):
    previous, last_size = (), None
    next_poll, next_labels = 0, 0
    future, operation, target, generation = None, '', '', 0
    queued = None
    executor = ThreadPoolExecutor(max_workers=1)
    try:
        while True:
            now = time.monotonic()
            if future is not None and future.done():
                try:
                    result = future.result()
                    if operation == 'poll':
                        controller.update(result, now)
                        controller.error = ''
                    elif operation == 'labels':
                        controller.workspace_labels, controller.tab_labels = result
                    elif operation == 'peek' and generation == controller.peek_generation:
                        controller.receive_peek(target, result)
                    elif operation == 'focus':
                        return 0
                except (HerdrError, ValueError):
                    if operation != 'peek' or generation == controller.peek_generation:
                        controller.error = ('Workspace labels unavailable; using IDs' if operation == 'labels'
                                            else 'Preview unavailable; press p to dismiss' if operation == 'peek'
                                            else 'Focus failed; choose an agent and retry' if operation == 'focus'
                                            else 'HerdR unavailable or invalid response; retrying')
                future = None
            if future is None:
                if queued:
                    operation, target, generation = queued
                    queued = None
                    if operation == 'focus' or generation == controller.peek_generation:
                        future = executor.submit(getattr(client, operation), target)
                elif now >= next_poll:
                    operation = 'poll'
                    future = executor.submit(client.agents)
                    next_poll = now + controller.poll_interval
                elif now >= next_labels:
                    operation = 'labels'
                    future = executor.submit(client.labels)
                    next_labels = now + 30
            size = terminal.size()
            if size != last_size:
                previous = ()
                terminal.write('\x1b[2J')
                last_size = size
            view = make_view(controller, now)
            _, body_height, _ = body_geometry(view, *size)
            controller.ensure_visible(body_height)
            frame = render(make_view(controller, now), *size, palette)
            differences = changed_rows(previous, frame)
            if differences:
                terminal.write(''.join('\x1b[%d;1H\x1b[0m\x1b[2K%s' % (i + 1, line)
                                       for i, line in differences))
            previous = frame
            for key in terminal.keys():
                action = controller.handle(key)
                if action:
                    kind, value = action
                    if kind == 'quit':
                        return 130 if key == 'interrupt' else 0
                    queued = (kind, value, controller.peek_generation)
    finally:
        controller.discard_peek()
        controller.fleet.agents.clear()
        controller.workspace_labels.clear()
        controller.tab_labels.clear()
        if future:
            future.cancel()
        executor.shutdown(wait=False, cancel_futures=True)


def main(argv=None, environ=None, client=None):
    env = dict(os.environ if environ is None else environ)
    parser = argparse.ArgumentParser(description='Selectable live HerdR agent tree')
    parser.add_argument('--open', action='store_true', help='Launch the registered dashboard pane')
    parser.add_argument('--poll', type=float, help='Polling seconds, minimum 0.5')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--search', action='store_true', help='Open with substring search active')
    group.add_argument('--fuzzy', action='store_true', help='Open ranked agent fuzzy search')
    args = parser.parse_args(argv)
    if env.get('HERDR_ENV') != '1':
        print('HerdR Fleet must run inside a HerdR-managed session.', file=sys.stderr)
        return 2
    client = client or HerdrClient(env.get('HERDR_BIN_PATH', 'herdr'),
                                    plugin_id=env.get('HERDR_PLUGIN_ID'))
    mode = 'fuzzy' if args.fuzzy else 'search' if args.search else env.get('HERDR_FLEET_SEARCH_MODE', 'tree')
    if mode not in ('search', 'fuzzy'):
        mode = 'tree'
    if args.open:
        try:
            client.open_dashboard(mode)
            return 0
        except HerdrError:
            print('HerdR Fleet could not open its dashboard pane.', file=sys.stderr)
            return 1
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        print('HerdR Fleet requires an interactive terminal.', file=sys.stderr)
        return 2
    root = Path(env['HERDR_PLUGIN_CONFIG_DIR']) if env.get('HERDR_PLUGIN_CONFIG_DIR') else None
    prefs = load(root)
    if args.poll is not None:
        prefs = Preferences(poll_seconds(args.poll), prefs.collapsed)
    controller = Controller(prefs, username=env.get('USER', ''), search_mode=mode)
    palette = Palette(color_mode(env), read_colors(config_path(env)))
    try:
        with Terminal(sys.stdin, sys.stdout) as terminal:
            return run(controller, client, terminal, palette)
    except TerminalExit as exc:
        return 128 + exc.signum
    except KeyboardInterrupt:
        return 130
    except Exception:
        # Restore first and avoid printing data-bearing tracebacks to action logs.
        print('HerdR Fleet stopped after an unexpected error.', file=sys.stderr)
        return 1
    finally:
        try:
            save(root, Preferences(controller.poll_interval, frozenset(controller.collapsed)))
        except OSError:
            print('HerdR Fleet could not save UI preferences.', file=sys.stderr)
