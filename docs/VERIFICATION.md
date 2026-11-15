# Verification and troubleshooting

This guide describes how version 0.2.1 is tested and provides a repeatable runtime check.

## Test coverage (version 0.2.1)

| Surface | Observed result |
| --- | --- |
| Unit and PTY suite | 45 tests pass on macOS (CI matrix: Ubuntu and macOS, Python 3.9 and 3.13) |
| Compilation | src/bin compileall and extensionless entrypoint py_compile pass |
| Rendering | Synthetic 40/80/160-column frames printed; width/control checks pass |
| CLI contract | HerdR 0.9.5 skill, schema and plugin-pane help inspected |
| CLI wire spike | Isolated Unix stub confirms newline-delimited JSON and plain-text read output |
| Real agent-list latency | Unmeasured. `tests/live_acceptance.py` is a manual spike; no result is claimed here |
| Native popup/focus/peek/theme | Manual check, see below |
| Persistent placement | Schema-supported; lifecycle unverified |
| Linux and newer HerdR versions | Not tested |

PTY checks cover normal quit, Escape, Ctrl-C, Enter focus, SIGINT/SIGTERM, resize, preview, outage recovery and unexpected render failure. macOS's PENDIN pending-input bit is normalized during attribute comparison; other terminal attributes are compared. Fake focus proves the app invokes its client and exits cleanly, not that the native server changes focus correctly.

## Native evaluation

Use a throwaway session (`herdr --session scratch`), not your working session. Do not manually set HERDR_ENV or guess a socket. Install the plugin and apply an unused binding as documented in the [README](../README.md).

1. Run `herdr --version`, `python3 --version` and `herdr config check`. Record versions and the config-check outcome, not config contents.
2. Optionally run `PYTHONPATH=src python3 tests/live_acceptance.py` (manual only, scratch session only). It makes ten read-only list requests at least 500 ms apart and prints aggregate latency/count only. Record median/max latency.
3. Invoke `herdr plugin action invoke carlosiborra.fleet.open`. Confirm the popup is centered at 120 columns and 34 rows, totals match expected agents and workspace/tab grouping is useful.
4. Navigate with arrows/j/k, collapse and expand groups, scroll deeply, and confirm pinned attention and selected details. Resize to roughly 40, 80 and 160 columns.
5. Select an agent, press `p`, and confirm a bounded preview. Dismiss or change selection and confirm previous preview content disappears. Do not save real output.
6. Press Enter on an agent. Confirm the popup closes and HerdR focuses the selected pane. Repeat using that agent's two-letter uppercase code.
7. Invoke `carlosiborra.fleet.search`, type a title fragment, select with arrows and press Enter. Repeat with `carlosiborra.fleet.fuzzy` and a subsequence query.
8. Reopen and exit with q/Escape/Ctrl-C. Confirm the original screen, cursor, input and wrapping work normally.

Stop on wrong-pane focus, retained preview data, abnormal terminal state or repeated hangs. Close only the plugin-owned popup and report which step failed, without pasting private terminal content. Do not stop your HerdR server or disrupt other agents to test outage handling; synthetic tests cover it.

## Troubleshooting

| Symptom | Check or action |
| --- | --- |
| Must run inside a HerdR-managed session | Open from a real HerdR terminal; do not bypass the guard |
| Binding does nothing | Confirm the plugin is installed and enabled, action ID is correct, key is unused, config checks and reloads |
| UI appears as captured command output | Use registered plugin actions/panes rather than an interactive command in action output |
| Labels unavailable | IDs remain usable; snapshot retrieval will retry |
| Focus failed | Pane may have disappeared; wait for a fresh list, select again, retry |
| Preview hidden | Widths below 60 suppress it; widen terminal and press p |
| Age resets after reopening | Expected: ages begin at first observation, not a server timestamp |
| No colors | Check NO_COLOR/COLORTERM and theme.custom; monochrome status remains usable |
| Terminal damaged after force-kill | In the affected shell, run `stty sane` and `reset`; SIGKILL bypasses cleanup |

## Reporting results

When reporting a problem, include the revision (`git rev-parse HEAD`), OS, HerdR and Python versions, test results, aggregate latency and which native step failed. Leave out real agent titles, paths, commands, pane contents and session IDs. Screenshots should use synthetic data.

Persistent placements and Linux stay explicitly unverified until separately exercised. CI runs the unit suite only; the manual steps above are never run in CI.
