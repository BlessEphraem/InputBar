import os
from Core.Logging import eprint

# List of system commands (easily customizable)
commands = [
    {"name": "🔒 System Lock",      "cmd": "rundll32.exe user32.dll,LockWorkStation",       "keys": ["lock"]},
    {"name": "🌙 System Sleep",     "cmd": "rundll32.exe powrprof.dll,SetSuspendState 0,1,0","keys": ["sleep"]},
    {"name": "🔄 System Restart",   "cmd": "shutdown /r /t 0",                               "keys": ["restart", "reboot"]},
    {"name": "🔌 System Shut Down", "cmd": "shutdown /s /t 0",                               "keys": ["shutdown", "shut down", "poweroff"]},
]

# Global state for the pending confirmation
_pending_cmd  = None
_pending_name = None

def _request_confirm(cmd, name):
    """Stores the command as pending and tells the UI to refresh without closing."""
    global _pending_cmd, _pending_name
    _pending_cmd  = cmd
    _pending_name = name
    return "KEEP_OPEN_AND_REFRESH"

def exec_cmd():
    """Executes the final command after confirmation."""
    global _pending_cmd, _pending_name
    if _pending_cmd:
        try:
            os.system(_pending_cmd)
        except Exception as e:
            eprint(f"System error: {e}")

    # Reset state after execution
    _pending_cmd  = None
    _pending_name = None

def on_search(text):
    global _pending_cmd, _pending_name
    query = text.strip().lower()

    # Safety: if the user types something different, cancel the pending confirmation
    if _pending_cmd and getattr(on_search, "_last_query", None) != query:
        _pending_cmd  = None
        _pending_name = None
    on_search._last_query = query

    # Confirmation mode: only show the validation button
    if _pending_cmd:
        return [{
            "name": f"⚠️ Confirm: {_pending_name}? (Press Enter to confirm)",
            "score": 5000,
            "action": exec_cmd,
            "icon_type": "settings"
        }]

    # Normal search mode
    if query.startswith("system "):
        query = query.replace("system ", "", 1).strip()

    results = []
    for c in commands:
        match = False

        if not query or "system".startswith(query):
            match = True
        else:
            for k in c["keys"]:
                if k.startswith(query) or query in k:
                    match = True
                    break

        if match:
            results.append({
                "name": c["name"],
                "score": 1000,
                "action": lambda cmd=c["cmd"], name=c["name"]: _request_confirm(cmd, name),
                "icon_type": "settings"
            })

    return results
