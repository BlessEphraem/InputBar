import os
import sys
import json
import argparse
import tempfile

# Parse global arguments
parser = argparse.ArgumentParser()
parser.add_argument('--search', type=str, help="Text to pre-fill in the search bar")
parser.add_argument('--config', type=str, help="Custom root path for Data and Plugins")
args, unknown = parser.parse_known_args()

IS_CLI_MODE     = bool(args.search)
CLI_SEARCH_TEXT = args.search if args.search else ""

# SCRIPT_DIR is the parent of the "Core" directory
SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# APP_ROOT: fixed location next to exe (frozen) or next to source root (dev)
if getattr(sys, 'frozen', False):
    APP_ROOT = os.path.dirname(sys.executable)
else:
    APP_ROOT = SCRIPT_DIR

# Determine the default BASE_DIR (before any Config.json override)
if getattr(sys, 'frozen', False):
    _default_base = os.path.dirname(sys.executable)
elif args.config:
    _default_base = os.path.abspath(args.config)
else:
    _default_base = SCRIPT_DIR

# ── Config.json (APP_ROOT/Path/, writable by the app without admin) ──────────
# Contains only {"ConfigDirectory": "<path>"} to let the user redirect where
# Data/ and Plugins/ live. Empty string = use default.
# Stored in Path/ (a subdirectory pre-created by the installer with users-full
# permissions) so the app can create and update it without elevated rights.
ROOT_CONFIG_DIR  = os.path.join(APP_ROOT, "Path")
ROOT_CONFIG_FILE = os.path.join(ROOT_CONFIG_DIR, "Config.json")

_config_dir_override = ""
if os.path.exists(ROOT_CONFIG_FILE):
    try:
        with open(ROOT_CONFIG_FILE, "r", encoding="utf-8") as _f:
            _root_cfg = json.load(_f)
        _config_dir_override = _root_cfg.get("ConfigDirectory", "").strip()
    except Exception:
        pass

if _config_dir_override:
    try:
        os.makedirs(_config_dir_override, exist_ok=True)
        BASE_DIR = _config_dir_override
    except Exception:
        BASE_DIR = _default_base
else:
    BASE_DIR = _default_base

# Create Config.json if absent — works in both dev and frozen mode because
# Path/ (frozen) is pre-created by the installer with users-full permissions,
# and in dev mode SCRIPT_DIR is writable.
if not os.path.exists(ROOT_CONFIG_FILE):
    try:
        os.makedirs(ROOT_CONFIG_DIR, exist_ok=True)
        with open(ROOT_CONFIG_FILE, "w", encoding="utf-8") as _f:
            json.dump({"ConfigDirectory": BASE_DIR}, _f, indent=4)
    except Exception:
        pass

# ── Derived directories ──────────────────────────────────────────────────────
CORE_DIR   = os.path.join(SCRIPT_DIR, "Core")
DATA_DIR   = os.path.join(BASE_DIR, "Data")
THEMES_DIR = os.path.join(DATA_DIR, "Themes")
# CACHE_DIR only meaningful in dev mode — frozen builds never write .pyc files.
CACHE_DIR  = os.path.join(DATA_DIR, "__pycache__") if not getattr(sys, 'frozen', False) else None

# PLUGINS_DIR: where plugin .py files live (code, not data).
# Always relative to SCRIPT_DIR so it never moves with ConfigDirectory.
# Frozen: SCRIPT_DIR == Lib/  → Lib/Plugins/
# Dev:    SCRIPT_DIR == src/  → src/Plugins/
PLUGINS_DIR = os.path.join(SCRIPT_DIR, "Plugins")

# PLUGINS_DATA_DIR: where plugin data files (*.data, *.json) live.
# Always follows BASE_DIR so ConfigDirectory redirects carry data with it.
# In frozen mode this is separate from PLUGINS_DIR (code = Lib/Plugins, data = {app}/Plugins).
PLUGINS_DATA_DIR = os.path.join(BASE_DIR, "Plugins")

# Built-in themes bundled with the app (read-only source)
if getattr(sys, 'frozen', False):
    BUILTIN_THEMES_DIR = os.path.join(getattr(sys, '_MEIPASS', os.path.dirname(sys.executable)), 'Assets', 'Themes')
else:
    BUILTIN_THEMES_DIR = os.path.join(SCRIPT_DIR, 'Assets', 'Themes')

_dirs_to_create = [
    CORE_DIR, DATA_DIR, THEMES_DIR,
    os.path.join(PLUGINS_DATA_DIR, "App"),
    os.path.join(PLUGINS_DATA_DIR, "Shell"),
    os.path.join(PLUGINS_DATA_DIR, "Everything"),
]
if CACHE_DIR:
    _dirs_to_create.append(CACHE_DIR)

for folder in _dirs_to_create:
    if not os.path.exists(folder):
        try: os.makedirs(folder)
        except Exception: pass

# ── Data files ───────────────────────────────────────────────────────────────
HISTORY_FILE  = os.path.join(DATA_DIR, "search_history.json")
PLUGINS_FILE  = os.path.join(DATA_DIR, "Plugins.json")
SETTINGS_FILE = os.path.join(DATA_DIR, "Settings.json")

LOG_FILE = os.path.join(tempfile.gettempdir(), "InputBar.log")



