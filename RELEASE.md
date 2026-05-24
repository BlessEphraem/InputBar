# 2.0.1

## Fixes
- **WinKeyHook launch fallback**: daemon startup now tries three strategies in order — (1) Task Scheduler task `WinKeyHook` (silent, no UAC prompt), (2) direct process launch (works when exe carries no `requireAdministrator` manifest), (3) `ShellExecute runas` (shows UAC prompt once as last resort). Previous behaviour used only strategy 2, causing silent failure on hardened systems.
