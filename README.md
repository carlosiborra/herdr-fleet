# herdr-fleet

An agent triage dashboard for [HerdR](https://herdr.dev). One popup shows every coding agent in your session: who needs you, what is working, what just finished.

```text

WIDTH 40 (synthetic fixture)
FLEET  2work 1done 1idle 1block 1?
Live session  |  age ? = start time unk…
/
────────────────────────────────────────
  NEEDS ATTENTION 4
› AB ✓ [CL] Implementation: Review Un… ?
  AE ! [CX] Site: Approval required    ?
  AA ◴ [CX] Implementation: Implement… ?
  AD ◴ [CX] Site: Long title Long tit… ?
  ▾ Engineering  [1 working, 1 done, 1 …
  ├─ ▾ Implementation  [2 agents]
  │  ├─ AA ◴ [CX] Implement API        ?
  │  └─ AB ✓ [CL] Review Unicode 界 c… ?
  └─ ▾ Review  [1 agent]
     └─ AC ○ [CX] Awaiting task        ?
  ▾ Docs  [1 working, 1 blocked]
  └─ ▾ Site  [2 agents]
     ├─ AD ◴ [CX] Long title Long tit… ?
     └─ AE ! [CX] Approval required    ?
  ▾ Personal  [1 unknown]
  └─ ▾ w3:t1  [1 agent]
     └─ AF ? [CX] Unclassified         ?



TITLE  Review Unicode 界 café
w1 / w1:t1 / w1:p2 | claude | done age …
j/k ↑↓  Enter go  h/l fold  p / q

WIDTH 80 (synthetic fixture)
AGENT FLEET  |  2 working  1 done  1 idle  1 blocked  1 unknown
Live session  |  age ? = start time unknown  |  AA..ZZ jump
/
────────────────────────────────────────────────────────────────────────────────
  NEEDS ATTENTION 4
› AB ✓ [CL] Implementation: Review Unicode 界 café                    done age ?
  AE ! [CX] Site: Approval required                                blocked age ?
  AA ◴ [CX] Implementation: Implement API                          working age ?
  AD ◴ [CX] Site: Long title Long title Long title Long title Lon… working age ?
  ▾ Engineering  [1 working, 1 done, 1 idle]
  ├─ ▾ Implementation  [2 agents]
  │  ├─ AA ◴ [CX] Implement API                                    working age ?
  │  └─ AB ✓ [CL] Review Unicode 界 café                              done age ?
  └─ ▾ Review  [1 agent]
     └─ AC ○ [CX] Awaiting task                                       idle age ?
PEEK  Review Unicode
Synthetic preview only
Tests pass; waiting for review







TITLE  Review Unicode 界 café
w1 / w1:t1 / w1:p2 | claude | done age unknown | /example/project
j/k move  h/l fold  Enter focus  p peek  / filter  q/Esc close

WIDTH 160 (synthetic fixture)
AGENT FLEET  |  2 working  1 done  1 idle  1 blocked  1 unknown
Live session  |  age ? = start time unknown  |  AA..ZZ jump
/
────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
  NEEDS ATTENTION 4                                                                                      │ PEEK  Review Unicode
› AB ✓ [CL] Implementation: Review Unicode 界 café                                            done age ? │ Synthetic preview only
  AE ! [CX] Site: Approval required                                                        blocked age ? │ Tests pass; waiting for review
  AA ◴ [CX] Implementation: Implement API                                                  working age ? │
  AD ◴ [CX] Site: Long title Long title Long title Long title Long title Long title Long … working age ? │
  ▾ Engineering  [1 working, 1 done, 1 idle]                                                             │
  ├─ ▾ Implementation  [2 agents]                                                                        │
  │  ├─ AA ◴ [CX] Implement API                                                            working age ? │
  │  └─ AB ✓ [CL] Review Unicode 界 café                                                      done age ? │
  └─ ▾ Review  [1 agent]                                                                                 │
     └─ AC ○ [CX] Awaiting task                                                               idle age ? │
  ▾ Docs  [1 working, 1 blocked]                                                                         │
  └─ ▾ Site  [2 agents]                                                                                  │
     ├─ AD ◴ [CX] Long title Long title Long title Long title Long title Long title Long … working age ? │
     └─ AE ! [CX] Approval required                                                        blocked age ? │
  ▾ Personal  [1 unknown]                                                                                │
  └─ ▾ w3:t1  [1 agent]                                                                                  │
     └─ AF ? [CX] Unclassified                                                             unknown age ? │
                                                                                                         │
                                                                                                         │
                                                                                                         │
TITLE  Review Unicode 界 café
w1 / w1:t1 / w1:p2 | claude | done age unknown | /example/project
j/k move  h/l fold  Enter focus  p peek  / filter  q/Esc close
```

(Synthetic data, 40-column frame. More frames in [docs/PREVIEW.txt](docs/PREVIEW.txt).)

## Features

- Attention section pinned on top: unseen completions, blocked agents, work in progress.
- Status counts per workspace and for the whole fleet.
- Output peek: press `p` to see the last 15 lines of the selected agent.
- Two-letter jump codes: type `AB` to focus that agent immediately.
- Grouped tree of workspaces, tabs and agents with fold/unfold, state age and substring filter.
- `herdr-fleet.fuzzy`: a convenience action that opens a flat, ranked, subsequence-matching finder (`bapi` matches `Build API`).
- Theme colors follow your HerdR `[theme.custom]` settings; `NO_COLOR` is respected.

## How it differs from the built-in agent sidebar

The sidebar is always on and compact. Fleet is an on-demand, larger view built for triage: it ranks what needs attention, shows durations and a peek of recent output, and lets you jump with a two-key code. It does not replace the sidebar.

## Requirements

- HerdR 0.9.5 or newer (uses `plugin pane open --env` and `agent read --source recent-unwrapped`)
- Python 3.9 or newer (standard library only)
- macOS or Linux

## Install

```sh
herdr plugin install carlosiborra/herdr-fleet
```

## Keybinding

Add to your HerdR `config.toml`, choosing keys that are free:

```toml
[[keys.command]]
key = "prefix+a"
type = "plugin_action"
command = "herdr-fleet.open"
description = "agent fleet dashboard"

[[keys.command]]
key = "prefix+shift+a"
type = "plugin_action"
command = "herdr-fleet.search"
description = "search agents in the fleet dashboard"
```

Then run `herdr config check` and `herdr server reload-config`. The plugin never edits your configuration. Actions: `herdr-fleet.open` (tree), `herdr-fleet.search` (tree with search active), `herdr-fleet.fuzzy` (ranked finder).

## Keys

| Key | Action |
| --- | --- |
| `j` / `k`, down / up | Select rows |
| `h` / left, `l` / right | Collapse / expand the selected group |
| Enter on a group | Toggle its children |
| Enter on an agent | Focus that pane and exit |
| Two uppercase letters, e.g. `AB` | Focus the matching agent |
| `p` | Peek at the selected agent's last 15 lines; again to dismiss |
| `/` | Filter by title, workspace, tab or agent type |
| Enter while filtering | Keep filter, return to navigation |
| Escape | Cancel filter or jump prefix, or exit |
| `q`, Ctrl-C | Exit and restore the terminal |

## Preferences

Stored in `$HERDR_PLUGIN_CONFIG_DIR/preferences.json`: the poll interval (default 1 s, minimum 0.5 s) and which workspaces/tabs are folded. Nothing else is written. To override the interval for one run, pass `--poll 2` to `bin/herdr-fleet`.

## Privacy and trust

HerdR plugins are not sandboxed; this one runs as your user. What it does:

- Runs the `herdr` CLI (`$HERDR_BIN_PATH`) with a fixed allowlist: `agent list`, `api snapshot`, `agent read` (only when you press `p`), `agent focus` (only when you select an agent) and `plugin pane open` (its own popup).
- Reads agent titles, workspace/tab labels, working directories and recent pane output for the peek. These stay in memory and are discarded on dismissal or exit.
- Reads the `[theme.custom]` colors from `$XDG_CONFIG_HOME/herdr/config.toml` (or `~/.config/herdr/config.toml`).
- Writes only the fold/poll preferences above.
- No network access, no input injection, no notifications, no project scanning.

See [SECURITY.md](SECURITY.md) to report issues.

## Update and uninstall

```sh
herdr plugin update
herdr plugin uninstall herdr-fleet
```

Remove your keybindings as well.

## Development and tests

```sh
PYTHONPATH=src python3 -m unittest discover -s tests
python3 -m compileall -q src bin
PYTHONPATH=src python3 tests/render_snapshots.py
```

Tests use synthetic agents, a fake CLI runner and a local pseudo-terminal; they never contact a real HerdR server. `tests/live_acceptance.py` is manual-only, must be run against a throwaway session (`herdr --session scratch`) and is not run by CI. See [CONTRIBUTING.md](CONTRIBUTING.md), [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) and [docs/VERIFICATION.md](docs/VERIFICATION.md).

## License

MIT, see [LICENSE](LICENSE).
