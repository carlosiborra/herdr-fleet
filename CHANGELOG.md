# Changelog

## 0.2.0

- Pass the plugin ID from `HERDR_PLUGIN_ID` when opening the dashboard pane (falls back to `herdr-fleet`).
- Read the theme from `$XDG_CONFIG_HOME/herdr/config.toml` when set, otherwise `~/.config/herdr/config.toml`.
- Manifest: `min_herdr_version` is now 0.9.5 (the tested version), clearer description, platforms `linux` and `macos`.
- Standalone repository: install with `herdr plugin install`, GitHub Actions CI (Ubuntu and macOS, Python 3.9 and 3.13), MIT license, security policy.
- `tests/live_acceptance.py` is documented as manual-only against a throwaway session; docs no longer claim a measured agent-list latency.

## 0.1.0

- Initial release: live grouped tree of agents, attention section, status counts, output peek, two-letter jump codes, substring and fuzzy search.
