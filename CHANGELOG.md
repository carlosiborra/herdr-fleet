# Changelog

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
