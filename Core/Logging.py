import os
from Core.Paths import LOG_FILE

# Clear/create the log file on startup
try:
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write("")
except: pass

def dprint(msg):
    """Writes [DEBUG] messages to the log file."""
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[DEBUG] {msg}\n")
    except: pass

def eprint(msg):
    """Writes [ERROR] messages to the log file."""
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[ERROR] {msg}\n")
    except: pass
