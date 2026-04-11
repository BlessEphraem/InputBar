import os
import sys
import shutil
from Core.Paths import CACHE_DIR
from Core.Logging import dprint, eprint

_confirm_step = False

def _request_confirm():
    global _confirm_step
    _confirm_step = True
    return "KEEP_OPEN_AND_REFRESH"

def _do_clear_and_restart():
    dprint("Clearing cache...")
    try:
        if os.path.exists(CACHE_DIR):
            shutil.rmtree(CACHE_DIR)
            dprint("Cache cleared successfully.")
    except Exception as e:
        eprint(f"Error clearing cache: {e}")

    dprint("Restarting application (Cache Clear)")
    os.execl(sys.executable, sys.executable, *sys.argv)

def on_search(text):
    global _confirm_step
    query = text.lower().strip()

    # If the search query changes, cancel the pending confirmation
    if _confirm_step and getattr(on_search, "_last_query", None) != query:
        _confirm_step = False
    on_search._last_query = query

    results = []

    if _confirm_step:
        results.append({
            "name": "⚠️ Confirm cache deletion? (Press Enter to confirm)",
            "score": 5000,
            "action": _do_clear_and_restart,
            "icon_type": "settings"
        })
        return results

    if not query or "clear" in query:
        results.append({
            "name": "🧹 Cache Clear (Delete temporary files)",
            "score": 2000,
            "action": _request_confirm,
            "icon_type": "settings"
        })

    return results
