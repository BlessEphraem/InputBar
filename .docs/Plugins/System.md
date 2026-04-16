# 🖥️ Plugin - System

<a href="../Plugins.md" style="text-decoration:none"><kbd style="background:#30363d;color:#e6edf3;border:none;padding:3px 10px;border-radius:5px">← Back to Plugins</kbd></a>

Provides system-level commands: lock, sleep, restart, and shutdown — all with a mandatory confirmation step.

> **Keywords:** `system` · `*` *(global — active on every search)* - [Edit in `Plugins.json`](../Plugins.md)

## Usage 

```
system lock       →  Lock the session
system sleep      →  Sleep
system restart    →  Restart the PC
system reboot     →  Restart the PC (alias)
system shutdown   →  Shut down
```

## Confirmation step
Every command requires a confirmation before executing.  
After selecting a command, a confirmation entry replaces the list:

```
⚠️ Confirm: 🔄 System Restart? (Press Enter to confirm)
```

Typing anything else cancels the pending action automatically.


