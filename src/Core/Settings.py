import os
import sys
import json
from Core.Paths import SETTINGS_FILE, atomic_write_json
from Core.Logging import log_debug, log_error

# Current schema version — bump when adding/removing/renaming any key
_SCHEMA_VERSION = 1

_DEFAULTS: dict = {
    "schema_version":  _SCHEMA_VERSION,
    "Position":        "Center",
    "Monitor":         0,
    "AlwaysOnTop":     True,
    "HideOnFocusLost": True,
    "HideOnPress":     False,
    "LoopList":        True,
    "Theme":           "theme_default",
}

# Keys removed from the schema that must be purged from user files
_REMOVED_KEYS: set[str] = {"ListMax"}

# Keys the user should never see/edit directly
_INTERNAL_KEYS: set[str] = {"schema_version"}


def _migrate(data: dict) -> dict:
    """Upgrade data from an older schema version to current."""
    version = data.get("schema_version", 0)
    # Future: add elif version == 1: ... blocks here
    if version < _SCHEMA_VERSION:
        data["schema_version"] = _SCHEMA_VERSION
    return data


def load_global_config() -> dict:
    if not os.path.exists(SETTINGS_FILE):
        try:
            atomic_write_json(SETTINGS_FILE, _DEFAULTS)
        except Exception:
            pass
        return dict(_DEFAULTS)

    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            loaded = json.load(f)

        loaded = _migrate(loaded)

        updated = False

        # Inject missing keys
        for key, value in _DEFAULTS.items():
            if key not in loaded:
                loaded[key] = value
                updated = True

        # Purge removed / obsolete keys
        for key in list(loaded.keys()):
            if key in _REMOVED_KEYS:
                del loaded[key]
                updated = True

        if updated:
            atomic_write_json(SETTINGS_FILE, loaded)

        return loaded

    except Exception as e:
        log_error(f"Settings: read error ({e})")
        return dict(_DEFAULTS)


def _restart_app() -> None:
    log_debug("Settings: restarting application")
    if getattr(sys, "frozen", False):
        import subprocess
        subprocess.Popen([sys.executable])
    else:
        import subprocess
        subprocess.Popen([sys.executable] + sys.argv)
    sys.exit(0)


def _open_settings() -> None:
    os.startfile(SETTINGS_FILE)


def on_search(text: str) -> list[dict]:
    results: list[dict] = []
    search_term = text.lower().strip()

    if not search_term or "reload" in search_term:
        results.append({
            "name":      "Settings Reload",
            "score":     2000,
            "action":    _restart_app,
            "icon_type": "settings",
        })

    if not search_term or "open" in search_term:
        results.append({
            "name":      "Settings Open",
            "score":     1900,
            "action":    _open_settings,
            "icon_type": "settings",
        })

    return results
