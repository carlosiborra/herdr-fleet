"""MANUAL ONLY. Not part of the automated suite or CI (unittest discovery ignores it).

Read-only latency spike. Run it against a throwaway session, never your real one:
    herdr --session scratch   # then, inside that session's pane:
    PYTHONPATH=src python3 tests/live_acceptance.py
It never records agent content."""
import os
import statistics
import sys
import time

from herdr_fleet.client import HerdrClient, HerdrError


def main():
    if os.environ.get('HERDR_ENV') != '1':
        print('Run this check inside a HerdR-managed pane.', file=sys.stderr)
        return 2
    client = HerdrClient(os.environ.get('HERDR_BIN_PATH', 'herdr'))
    samples = []
    count = 0
    for index in range(10):
        start = time.monotonic()
        try:
            count = len(client.agents())
        except HerdrError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        samples.append((time.monotonic() - start) * 1000)
        if index < 9:
            time.sleep(max(0.5, 1 - (time.monotonic() - start)))
    print('agent list: n=10, agents=%d, median=%.1fms, max=%.1fms' %
          (count, statistics.median(samples), max(samples)))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
