import fcntl
import os
from pathlib import Path
import pty
import select
import signal
import struct
import subprocess
import sys
import termios
import time
import unittest


class TerminalTests(unittest.TestCase):
    def launch(self, *args):
        master, slave = pty.openpty()
        before = termios.tcgetattr(slave)
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 24, 80, 0, 0))
        root = Path(__file__).resolve().parent.parent
        env = dict(os.environ, PYTHONPATH=str(root / 'src'))
        process = subprocess.Popen([sys.executable, str(root / 'tests' / 'pty_dashboard.py')] + list(args),
                                   stdin=slave, stdout=slave, stderr=slave, env=env)
        return master, slave, before, process

    @staticmethod
    def read_until(master, token, budget=3):
        output = bytearray()
        deadline = time.monotonic() + budget
        while time.monotonic() < deadline and token not in output:
            ready, _, _ = select.select([master], [], [], 0.05)
            if ready:
                output.extend(os.read(master, 65536))
        return bytes(output)

    def assert_restored(self, slave, before):
        after = termios.tcgetattr(slave)
        # macOS sets PENDIN when restoring canonical input. It is pending
        # input state, not a terminal mode. Compare every other flag and byte.
        pending = getattr(termios, 'PENDIN', 0)
        after[3] &= ~pending
        expected = list(before)
        expected[3] &= ~pending
        self.assertEqual(after, expected)

    def test_exit_keys_signals_and_focus_restore_terminal(self):
        for action in (b'q', b'\x1b', b'\x03', b'\r', signal.SIGINT, signal.SIGTERM):
            with self.subTest(action=action):
                master, slave, before, process = self.launch()
                try:
                    frame = self.read_until(master, b'Implement API')
                    self.assertIn(b'FLEET', frame)
                    self.assertIn(b'\x1b[?1049h', frame)
                    if isinstance(action, bytes):
                        os.write(master, action)
                    else:
                        process.send_signal(action)
                    tail = self.read_until(master, b'\x1b[?1049l')
                    process.wait(timeout=3)
                    self.assertIn(b'\x1b[?25h', tail)
                    self.assertIn(b'\x1b[?1049l', tail)
                    self.assert_restored(slave, before)
                    expected = 128 + action if isinstance(action, int) else 130 if action == b'\x03' else 0
                    self.assertEqual(process.returncode, expected)
                finally:
                    if process.poll() is None:
                        process.kill()
                        process.wait()
                    os.close(master)
                    os.close(slave)

    def test_resize_and_peek_in_running_app(self):
        master, slave, before, process = self.launch()
        try:
            self.assertIn(b'Implement API', self.read_until(master, b'Implement API'))
            os.write(master, b'p')
            self.assertIn(b'Synthetic preview', self.read_until(master, b'Synthetic preview'))
            fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 24, 40, 0, 0))
            process.send_signal(signal.SIGWINCH)
            narrow = self.read_until(master, b'j/k', budget=1)
            self.assertIn(b'j/k', narrow)
            os.write(master, b'q')
            self.read_until(master, b'\x1b[?1049l')
            process.wait(timeout=3)
            self.assert_restored(slave, before)
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()
            os.close(master)
            os.close(slave)

    def test_outage_retries_and_recovers(self):
        master, slave, before, process = self.launch('--fail-once')
        try:
            error = self.read_until(master, b'retrying')
            self.assertIn(b'retrying', error)
            recovered = self.read_until(master, b'Implement API')
            self.assertIn(b'Implement API', recovered)
            os.write(master, b'q')
            self.read_until(master, b'\x1b[?1049l')
            process.wait(timeout=3)
            self.assert_restored(slave, before)
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()
            os.close(master)
            os.close(slave)

    def test_unexpected_error_restores_terminal(self):
        master, slave, before, process = self.launch('--crash')
        try:
            tail = self.read_until(master, b'\x1b[?1049l')
            process.wait(timeout=3)
            self.assertIn(b'\x1b[?25h', tail)
            self.assertIn(b'\x1b[?1049l', tail)
            self.assertEqual(process.returncode, 1)
            self.assert_restored(slave, before)
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()
            os.close(master)
            os.close(slave)
