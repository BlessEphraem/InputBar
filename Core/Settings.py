import os
import sys
import json
from Core.Paths import SETTINGS_FILE
from Core.Logging import dprint, eprint


def load_global_config():
    default_config = {
        "Position":        "Center",
        "Monitor":         0,
        "AlwaysOnTop":     True,
        "HideOnFocusLost": True,
        "HideOnPress":     False,  # Can be: False, "OnFocus", or "Always"
        "LoopList":        True,   # Loop navigation in the results list
        "Theme":           "theme_default"  # Theme file name in Data/Themes/ (without .json)
    }
    if not os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "w") as f:
                json.dump(default_config, f, indent=4)
            return default_config
        except Exception:
            return default_config
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            loaded_config = json.load(f)

        config_updated = False
        for key, value in default_config.items():
            if key not in loaded_config:
                loaded_config[key] = value
                config_updated = True

        if config_updated:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as fw:
                json.dump(loaded_config, fw, indent=4)
        return loaded_config
    except Exception as e:
        eprint(f"Settings: read error ({e})")
        return default_config


def _restart_app():
    dprint("Settings: restarting application")
    if getattr(sys, 'frozen', False):
        import subprocess
        subprocess.Popen([sys.executable])
    else:
        import subprocess
        subprocess.Popen([sys.executable] + sys.argv)
    sys.exit(0)


def _open_settings():
    os.startfile(SETTINGS_FILE)


def on_search(text):
    results    = []
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
