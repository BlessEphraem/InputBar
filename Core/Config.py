import os
import sys
import json
from Core.Paths import CONFIG_FILE
from Core.Logging import dprint, eprint

def load_global_config():
    default_config = {
        "Position":       "Center",
        "Monitor":        0,
        "AlwaysOnTop":    True,
        "HideOnFocusLost":True,
        "HideOnPress":    False,  # Can be: False, "OnFocus", or "Always"
        "LoopList":       True,   # Loop navigation in the results list
        "ListMax":        200,    # Maximum number of displayed results
        "Theme":          "theme_default"  # Theme file name in Data/Themes/ (without .json)
    }
    if not os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "w") as f: json.dump(default_config, f, indent=4)
            return default_config
        except: return default_config
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            loaded_config = json.load(f)

        config_updated = False
        for key, value in default_config.items():
            if key not in loaded_config:
                loaded_config[key] = value
                config_updated = True

        if config_updated:
            with open(CONFIG_FILE, "w", encoding="utf-8") as fw:
                json.dump(loaded_config, fw, indent=4)
        return loaded_config
    except Exception as e:
        eprint(f"Error reading config: {e}")
        return default_config

def _restart_app():
    import subprocess
    dprint("Restarting application (Config Reload)")
    if getattr(sys, 'frozen', False):
        subprocess.Popen([sys.executable])
    else:
        subprocess.Popen([sys.executable] + sys.argv)
    sys.exit(0)

def _open_config():
    os.startfile(CONFIG_FILE)

def on_search(text):
    results = []
    search_term = text.lower().strip()

    if not search_term or "reload" in search_term:
        results.append({
            "name": "🔄 Config Reload",
            "score": 2000,
            "action": _restart_app,
            "icon_type": "settings"
        })

    if not search_term or "open" in search_term:
        results.append({
            "name": "📝 Config Open",
            "score": 1900,
            "action": _open_config,
            "icon_type": "settings"
        })

    return results
