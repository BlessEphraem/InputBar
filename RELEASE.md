# **RELEASE NOTE: 1.3.0**

## WinKeyHook — External Daemon

The bundled `winkey_hook.exe` (previously shipped in `Lib\Core\`) has been removed and replaced by the **WinKeyHook Daemon**, an independent open-source tool available at:
https://github.com/BlessEphraem/WinKeyHook

**What changes for you:**
- The installer automatically removes the old `Lib\Core\winkey_hook.exe` if present.
- InputBar detects whether the WinKeyHook Daemon is installed and launches it automatically when needed (e.g. when a `win`, `lwin`, or `rwin` hotkey is configured).
- If the daemon is not installed or is outdated, InputBar will warn you.
- Install WinKeyHook separately from its own installer — it runs system-wide and is shared across all apps that need low-level Windows key interception.
