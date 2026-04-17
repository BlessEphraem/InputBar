# **RELEASE NOTE: 1.2.2**

## New Configuration Key - Per-plugin result limit
Each plugin now exposes a `"limit"` key in `Plugins.json` (default `15`). Raise it to see more results per plugin, lower it for a tighter list.

## Updated Plugin - Shell

- **Custom terminal emulators** — Define any terminal (WezTerm, Alacritty, Windows Terminal…) in `default_shell.json` under `"extra_shells"` and use it as your default shell or as a per-entry prefix in `favorites.data`.
- **`/` keyword** — Type `/ <command>` as a shorter alternative to `shell <command>`.
- **Silent execution** — Use `extra_shells` with `cmd /c` or PowerShell `-WindowStyle Hidden` to run commands without a visible window (see [Shell docs](.docs/Plugins/Shell.md) for examples).
- **CWD fix** — Shell commands now open in the user's home directory instead of InputBar's install folder.

## Quick Fixes

- **App plugin** — Auxiliary shortcuts (Help, Uninstall, ReadMe…) no longer appear in results. `Get-StartApps`, Start Menu `.lnk` files, and registry entries are now all filtered by name and target executable. Non-executable UWP entries (documents, text files…) registered via `Get-StartApps` are no longer indexed.
- **`ListMax` setting removed** — superseded by `MaxItemToShow` in the theme. Existing `Settings.json` files are cleaned up automatically on first launch.
