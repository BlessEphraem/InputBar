import os
import json
from datetime import datetime, timedelta
from Core.Paths import HISTORY_FILE
from Core.Logging import eprint

MAX_TOTAL_ITEMS = 200
DAYS_TO_KEEP    = 90
_history_data   = {}

def load_history():
    global _history_data
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r") as f: _history_data = json.load(f)
        except: _history_data = {}
    else:
        _history_data = {}

def save_to_history(name):
    global _history_data
    _history_data[name] = {
        'count': _history_data.get(name, {}).get('count', 0) + 1,
        'date': datetime.now().isoformat()
    }
    try:
        with open(HISTORY_FILE, "w") as f: json.dump(_history_data, f)
    except Exception as e:
        eprint(f"Error saving history: {e}")

def get_score(item_name):
    if item_name in _history_data:
        last_used = datetime.fromisoformat(_history_data[item_name]['date'])
        if datetime.now() - last_used < timedelta(days=DAYS_TO_KEEP):
            return _history_data[item_name]['count'] * 5
    return 0

def process_search(text, plugins):
    query       = text.strip()
    query_lower = query.lower()
    parts       = query_lower.split(" ", 1)
    first_word  = parts[0] if parts else ""

    strict_plugins = []

    # Check if the first word matches a plugin's strict keyword
    for plugin in plugins:
        keywords = getattr(plugin, "_keywords", [])
        if first_word in keywords and first_word != "*":
            strict_plugins.append(plugin)

    all_results = []

    if strict_plugins:
        # Strict mode: the keyword is stripped from the query before passing to the plugin
        payload = query[len(first_word):].strip()

        for plugin in strict_plugins:
            try:
                res = plugin.on_search(payload)
                if res:
                    for item in res:
                        item["score"] = item.get("score", 100) + get_score(item["name"])
                        all_results.append(item)
            except Exception as e:
                eprint(f"Plugin error (Strict) {plugin.__name__}: {e}")
    else:
        # Global mode: only plugins marked as always-active (with "*") are queried
        for plugin in plugins:
            keywords = getattr(plugin, "_keywords", [])
            if "*" in keywords:
                try:
                    res = plugin.on_search(query)
                    if res:
                        for item in res:
                            item["score"] = item.get("score", 100) + get_score(item["name"])
                            all_results.append(item)
                except Exception as e:
                    eprint(f"Plugin error (Global) {plugin.__name__}: {e}")

    all_results.sort(key=lambda x: x.get("score", 0), reverse=True)
    return all_results[:MAX_TOTAL_ITEMS]
