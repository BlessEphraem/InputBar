import os
import json
import inspect as _inspect
import itertools
from datetime import datetime, timedelta
from Core.Paths import HISTORY_FILE
from Core.Logging import eprint

DAYS_TO_KEEP    = 90
_history_data   = {}

def load_history():
    global _history_data
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r") as f: _history_data = json.load(f)
        except Exception: _history_data = {}
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

def get_score(item_name, now=None):
    if item_name in _history_data:
        last_used = datetime.fromisoformat(_history_data[item_name]['date'])
        if now is None: now = datetime.now()
        if now - last_used < timedelta(days=DAYS_TO_KEEP):
            return _history_data[item_name]['count'] * 5
    return 0

# Cache per plugin whether on_search accepts is_strict — avoids calling
# inspect.signature() on every search query.
_plugin_has_is_strict: dict = {}


def _accepts_is_strict(plugin) -> bool:
    """Return True if plugin.on_search accepts an is_strict keyword argument."""
    key = id(plugin)
    if key not in _plugin_has_is_strict:
        try:
            sig = _inspect.signature(plugin.on_search)
            _plugin_has_is_strict[key] = "is_strict" in sig.parameters
        except Exception:
            _plugin_has_is_strict[key] = False
    return _plugin_has_is_strict[key]


def process_search(text, plugins):
    now = datetime.now()
    query       = text.strip()
    query_lower = query.lower()
    parts       = query_lower.split(" ", 1)
    first_word  = parts[0] if parts else ""

    strict_plugins = []

    # Pass 1: first word matches a plugin keyword exactly (space-separated)
    for plugin in plugins:
        keywords = getattr(plugin, "_keywords", [])
        if first_word in keywords and first_word != "*":
            strict_plugins.append(plugin)

    # Pass 2: single non-alphanumeric prefix keyword — matches without requiring a space.
    # e.g. keyword "/" matches "/fastfetch" in addition to "/ fastfetch".
    if not strict_plugins:
        for plugin in plugins:
            keywords = getattr(plugin, "_keywords", [])
            for kw in keywords:
                if (kw != "*" and len(kw) == 1 and not kw.isalnum()
                        and query_lower.startswith(kw) and len(query_lower) > 1):
                    first_word = kw
                    strict_plugins.append(plugin)
                    break

    if strict_plugins:
        # Strict mode: the keyword is stripped from the query before passing to the plugin
        payload = query[len(first_word):].strip()

        for plugin in strict_plugins:
            try:
                # Pass is_strict=True to allow plugins to behave differently
                # if the keyword was explicitly typed.
                if _accepts_is_strict(plugin):
                    res = plugin.on_search(payload, is_strict=True)
                else:
                    res = plugin.on_search(payload)

                if res:
                    limit = getattr(plugin, "_limit", 15)
                    for item in itertools.islice(res, limit):
                        item["score"] = item.get("score", 100) + get_score(item["name"], now=now)
                        yield item
            except Exception as e:
                eprint(f"Plugin error (Strict) {plugin.__name__}: {e}")
    else:
        # Global mode: only plugins marked as always-active (with "*") are queried
        for plugin in plugins:
            keywords = getattr(plugin, "_keywords", [])
            if "*" in keywords:
                try:
                    if _accepts_is_strict(plugin):
                        res = plugin.on_search(query, is_strict=False)
                    else:
                        res = plugin.on_search(query)

                    if res:
                        limit = getattr(plugin, "_limit", 15)
                        for item in itertools.islice(res, limit):
                            item["score"] = item.get("score", 100) + get_score(item["name"], now=now)
                            yield item
                except Exception as e:
                    eprint(f"Plugin error (Global) {plugin.__name__}: {e}")
