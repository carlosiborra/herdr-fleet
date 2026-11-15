"""Terminal lifecycle and incremental input decoding."""
import os
import select
import signal
import termios
import tty


class TerminalExit(BaseException):
    def __init__(self, signum):
        self.signum = signum


class KeyDecoder:
    def __init__(self):
        self.pending = bytearray()

    def feed(self, data):
        self.pending.extend(data)
        keys = []
        while self.pending:
            first = self.pending[0]
            if first == 27:
                if len(self.pending) == 1:
                    break
                if self.pending[1] not in (ord('['), ord('O')):
                    del self.pending[0]
                    keys.append('escape')
                    continue
                end = next((i for i in range(2, len(self.pending))
                            if 64 <= self.pending[i] <= 126), None)
                if end is None:
                    if len(self.pending) > 32:
                        self.pending.clear()
                    break
                sequence = bytes(self.pending[:end + 1])
                del self.pending[:end + 1]
                keys.append({b'\x1b[A': 'up', b'\x1b[B': 'down', b'\x1b[C': 'right',
                             b'\x1b[D': 'left', b'\x1bOA': 'up', b'\x1bOB': 'down',
                             b'\x1bOC': 'right', b'\x1bOD': 'left'}.get(sequence, 'unknown'))
            elif first < 128:
                del self.pending[0]
                keys.append({13: 'enter', 10: 'enter', 3: 'interrupt',
                             127: 'backspace', 8: 'backspace'}.get(first, chr(first)))
            else:
                length = 2 if 194 <= first <= 223 else 3 if 224 <= first <= 239 else 4 if 240 <= first <= 244 else 1
                if len(self.pending) < length:
                    break
                keys.append(bytes(self.pending[:length]).decode('utf-8', errors='replace'))
                del self.pending[:length]
        return tuple(keys)

    def flush_escape(self):
        if self.pending and self.pending[0] == 27:
            self.pending.clear()
            return ('escape',)
        return ()


class Terminal:
    def __init__(self, stdin, stdout):
        self.stdin, self.stdout = stdin, stdout
        self.fd = stdin.fileno()
        self.attributes = None
        self.signals = {}
        self.decoder = KeyDecoder()

    def write(self, value):
        self.stdout.write(value)
        self.stdout.flush()

    @staticmethod
    def stop(signum, frame):
        raise TerminalExit(signum)

    def __enter__(self):
        self.attributes = termios.tcgetattr(self.fd)
        try:
            for sig in (signal.SIGINT, signal.SIGTERM):
                self.signals[sig] = signal.getsignal(sig)
                signal.signal(sig, self.stop)
            tty.setraw(self.fd)
            self.write('\x1b[?1049h\x1b[?25l\x1b[?7l\x1b[2J\x1b[H')
            return self
        except BaseException:
            self.__exit__(None, None, None)
            raise

    def __exit__(self, exc_type, exc, tb):
        try:
            if self.attributes is not None:
                termios.tcsetattr(self.fd, termios.TCSANOW, self.attributes)
        finally:
            for sig, handler in self.signals.items():
                signal.signal(sig, handler)
            try:
                self.write('\x1b[0m\x1b[?7h\x1b[?25h\x1b[?1049l')
            except (OSError, ValueError):
                pass

    def size(self):
        try:
            size = os.get_terminal_size(self.stdout.fileno())
            return max(1, size.columns), max(1, size.lines)
        except OSError:
            return 80, 24

    def keys(self, timeout=0.05):
        ready, _, _ = select.select([self.fd], [], [], timeout)
        if ready:
            data = os.read(self.fd, 1024)
            return self.decoder.feed(data) if data else ('q',)
        return self.decoder.flush_escape()
