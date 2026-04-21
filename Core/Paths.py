import os
import sys
import json
import argparse
import tempfile
import shutil
import ctypes

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
LAST_CONFIG_FILE = os.path.join(ROOT_CONFIG_DIR, "last_session_config.txt")

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

# ── Session config tracking & migration ─────────────────────────────────────
_MB_YESNO        = 0x00000004
_MB_ICONQUESTION = 0x00000020
_MB_ICONWARNING  = 0x00000030
_IDYES           = 6


def _read_last_config() -> str:
    if not os.path.exists(LAST_CONFIG_FILE):
        return ""
    try:
        with open(LAST_CONFIG_FILE, "r", encoding="utf-8") as _f:
            return _f.read().strip()
    except Exception:
        return ""


def _write_last_config(path: str) -> None:
    try:
        os.makedirs(ROOT_CONFIG_DIR, exist_ok=True)
        with open(LAST_CONFIG_FILE, "w", encoding="utf-8") as _f:
            _f.write(os.path.normpath(path))
    except Exception:
        pass


def _msgbox_yesno(title: str, message: str, icon: int = _MB_ICONQUESTION) -> bool:
    return ctypes.windll.user32.MessageBoxW(0, message, title, _MB_YESNO | icon) == _IDYES


def _migrate_config_if_needed(old_path: str, new_path: str) -> None:
    if os.path.normcase(os.path.normpath(old_path)) == \
       os.path.normcase(os.path.normpath(new_path)):
        return
    if not os.path.isdir(old_path):
        return

    if _msgbox_yesno(
        "InputBar \u2014 Configuration Path Changed",
        f"The data directory has changed since the last session.\n\n"
        f"Previous location:\n  {old_path}\n\n"
        f"New location:\n  {new_path}\n\n"
        f"Do you want to move your existing data to the new location?"
    ):
        try:
            os.makedirs(new_path, exist_ok=True)
            for item in os.listdir(old_path):
                src = os.path.join(old_path, item)
                dst = os.path.join(new_path, item)
                if os.path.isdir(src):
                    shutil.copytree(src, dst, dirs_exist_ok=True)
                else:
                    shutil.copy2(src, dst)
            shutil.rmtree(old_path, ignore_errors=True)
        except Exception as exc:
            ctypes.windll.user32.MessageBoxW(
                0,
                f"Failed to move data:\n{exc}\n\nInputBar will launch with the new location.",
                "InputBar \u2014 Error",
                0x00000010
            )
    else:
        if _msgbox_yesno(
            "InputBar \u2014 Old Data Remains",
            f"Your previous configuration data still exists at:\n  {old_path}\n\n"
            f"Do you want to delete it now?\n"
            f"(InputBar will create fresh default files at the new location.)",
            _MB_ICONWARNING
        ):
            shutil.rmtree(old_path, ignore_errors=True)


def _has_files(path: str) -> bool:
    for _, _, files in os.walk(path):
        if files:
            return True
    return False


def _cleanup_dead_app_data_if_needed(app_root: str, base_dir: str) -> None:
    if os.path.normcase(os.path.normpath(base_dir)) == \
       os.path.normcase(os.path.normpath(app_root)):
        return

    dead = [
        d for d in (
            os.path.join(app_root, "Data"),
            os.path.join(app_root, "Plugins"),
        )
        if os.path.isdir(d) and _has_files(d)
    ]
    if not dead:
        return

    dirs_str = "\n".join(f"  {d}" for d in dead)
    if _msgbox_yesno(
        "InputBar \u2014 Unused Data Found",
        f"InputBar found data in the installation folder that is no longer used:\n\n"
        f"{dirs_str}\n\n"
        f"Your active configuration is stored at:\n  {base_dir}\n\n"
        f"Do you want to delete this unused data?",
        _MB_ICONWARNING
    ):
        for d in dead:
            shutil.rmtree(d, ignore_errors=True)


if getattr(sys, 'frozen', False) and not IS_CLI_MODE:
    _prev = _read_last_config()
    if _prev:
        _migrate_config_if_needed(_prev, BASE_DIR)
    _cleanup_dead_app_data_if_needed(APP_ROOT, BASE_DIR)


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

_write_last_config(BASE_DIR)

