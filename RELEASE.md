# 2.0.0

## Breaking Changes
- **IPC protocol**: plain-text `SHOW` / `SEARCH:text` still accepted (backward-compatible). New JSON envelope format introduced: `{"protocol": 1, "command": "show", "args": {}}`. Old scripts continue to work unchanged.
- **Dev mode data path**: generated data now routes to `src/gen/Data/` instead of `src/Data/`. A one-time migration runs automatically on first launch.
- **`--verbose` flag**: new CLI flag to enable DEBUG logging in compiled mode.

## Improvements
- **Logging**: timestamped format `[YYYY-MM-DD HH:MM:SS.mmmZ] [LEVEL] [module]`. Bootstrap log at `%TEMP%\InputBar\bootstrap.log` active before path resolution. Log rotation (5 MB max, 3 files kept). Levels: DEBUG / INFO / WARN / ERROR / FATAL.
- **Crash handler**: unhandled exceptions now write a `InputBar_crash_<timestamp>.log` to `%TEMP%` before exiting.
- **Atomic config writes**: Settings.json, hotkeys.json, Plugins.json now written via temp+rename to prevent corruption on crash.
- **Schema versioning**: Settings.json and hotkeys.json carry a `schema_version` field enabling structured migrations.
- **Graceful shutdown**: SIGTERM / SIGINT handled. Plugins `teardown()` called in reverse load order. 5-second hard timeout on shutdown.
- **WinKeyHook install prompt**: user is asked before installing WinKeyHook. SHA-256 integrity check runs if a hash is configured in `build/project.json`.
- **Path traversal guard**: `ConfigDirectory` values pointing at system directories are rejected.
- **Thread safety**: `_pipe_handle` protected by a lock. Reader thread uses `threading.Event` stop flag.
- **IPC `quit` command**: both plain-text `QUIT` and JSON `{"command":"quit"}` trigger a graceful shutdown.
- **Plugin teardown contract**: plugins may expose `teardown() -> None` — called on shutdown.
- **Named constants**: all magic timing/retry values named (no bare literals).
- **Type annotations**: all public functions in Core modules annotated.
- **`build/project.json`**: single source of truth for name, version, publisher, GUID. `build_app.bat` and `CMakeLists.txt` both read from it.
- **`pyproject.toml`**: ruff linter configured for the project.
- **`.docs/ARCHITECTURE.md`**: module map, startup sequence, directory layout.
- **`.docs/DECISIONS.md`**: ADRs for all major technical choices.

## Infrastructure
- **Git root**: `.git` moved from `src/` to project root (§3.1 compliance).
- **`.gitignore`**: root-level gitignore added. `build/`, `releases/`, publish scripts, `src/gen/`, `CONTEXT.md` all excluded.
- **Dev data isolation**: `src/gen/` directory (gitignored) holds all dev-mode generated data.
