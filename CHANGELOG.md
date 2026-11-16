# Changelog

## Unreleased

- CI: run the Linux jobs on `ubuntu-24.04`. `ubuntu-latest` moved to Ubuntu 26, where Python 3.9 (still supported by this plugin) is not available.

## 0.2.2

- Naming: the product is spelled "Herdr" everywhere (README, docs, manifest name "Herdr Fleet", user-facing strings, tests); `herdr` is the command. The vendored helpers (`theme.py`, `terminal.py`, `search.py`, `text.py`) contained no HerdR spelling, so their recorded hashes are unchanged.
- README: pitch, benefits, install and keybinding now open the page; demo GIF follows, text previews are collapsed, and a suite list and non-affiliation note were added.

## 0.2.1

- Docs: demo GIF and badges in the README (the demo uses synthetic agents only).
- GitHub issue templates (bug report, feature request) with a security-advisory contact link.
- Test: `tests/test_vendored.py` guards the vendored helpers (`theme.py`, `terminal.py`, `search.py`, `text.py`) against accidental drift; changing one now requires updating its recorded hash and this changelog.

## 0.2.0

- Plugin id is now `carlosiborra.fleet` (namespaced, so it cannot clash with other `herdr-fleet` plugins). Bind actions as `carlosiborra.fleet.<action>`.

- Pass the plugin ID from `HERDR_PLUGIN_ID` when opening the dashboard pane (falls back to `carlosiborra.fleet`).
- Read the theme from `$XDG_CONFIG_HOME/herdr/config.toml` when set, otherwise `~/.config/herdr/config.toml`.
- Manifest: `min_herdr_version` is now 0.9.5 (the tested version), clearer description, platforms `linux` and `macos`.
- Standalone repository: install with `herdr plugin install`, GitHub Actions CI (Ubuntu and macOS, Python 3.9 and 3.13), MIT license, security policy.
- `tests/live_acceptance.py` is documented as manual-only against a throwaway session; docs no longer claim a measured agent-list latency.

## 0.1.0

- Initial release: live grouped tree of agents, attention section, status counts, output peek, two-letter jump codes, substring and fuzzy search.
