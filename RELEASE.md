# **RELEASE NOTE: 1.3.0**

## WinKeyHook — External Daemon

The bundled `winkey_hook.exe` (previously shipped in `Lib\Core\`) has been removed and replaced by the **WinKeyHook Daemon**, an independent open-source tool available at:
https://github.com/BlessEphraem/WinKeyHook

**What changes for you:**
- The installer automatically removes the old `Lib\Core\winkey_hook.exe` if present.
- On first launch, InputBar automatically installs the WinKeyHook Daemon if it is not already present (a UAC prompt will appear).
- Once installed, InputBar launches the daemon automatically whenever a `win`, `lwin`, or `rwin` hotkey is configured.
- If the daemon is already running (e.g. from another app), InputBar connects to it directly without re-launching it.
