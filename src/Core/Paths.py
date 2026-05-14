import os
import sys
import json
import tempfile
import shutil
import ctypes
import winreg

# ── Registry backup for data-dir resilience (§8.2) ────────────────────────────
_REG_KEY   = r"Software\Ephraem\InputBar"
_REG_VALUE = "ConfigDirectory"


def _reg_get_config_dir() -> str:
    """Read data-dir backup from registry (frozen only). Returns '' on any error."""
    if not getattr(sys, "frozen", False):
        return ""
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, _REG_KEY, access=winreg.KEY_READ)
        value, _ = winreg.QueryValueEx(key, _REG_VALUE)
        winreg.CloseKey(key)
        return value.strip() if isinstance(value, str) else ""
    except OSError:
        return ""


def _reg_set_config_dir(path: str) -> None:
    """Write data-dir backup to registry (frozen only). Silent on failure."""
    if not getattr(sys, "frozen", False):
        return
    try:
        key = winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, _REG_KEY, access=winreg.KEY_WRITE)
        winreg.SetValueEx(key, _REG_VALUE, 0, winreg.REG_SZ, path)
        winreg.CloseKey(key)
    except OSError:
        pass


# ── Exit codes (§15) ──────────────────────────────────────────────────────────
EXIT_SUCCESS       = 0
EXIT_GENERIC_ERROR = 1
EXIT_BAD_CONFIG    = 2
EXIT_MISSING_DEP   = 3
EXIT_IPC_FAILURE   = 4
EXIT_PERMISSION    = 5
EXIT_DATA_DIR_ERROR = 6
EXIT_USER_INTERRUPT = 130

# Parse global arguments
import argparse
parser = argparse.ArgumentParser()
parser.add_argument("--search",  type=str, help="Text to pre-fill in the search bar")
parser.add_argument("--config",  type=str, help="Custom root path for Data and Plugins")
parser.add_argument("--verbose", action="store_true", help="Enable DEBUG log level in compiled mode")
args, unknown = parser.parse_known_args()

IS_CLI_MODE     = bool(args.search)
CLI_SEARCH_TEXT = args.search if args.search else ""
VERBOSE_MODE    = bool(args.verbose)

# SCRIPT_DIR is the parent of the "Core" directory (i.e. src/)
SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# APP_ROOT: fixed location next to exe (frozen) or next to source root (dev)
if getattr(sys, "frozen", False):
    APP_ROOT = os.path.dirname(sys.executable)
else:
    APP_ROOT = SCRIPT_DIR

# Determine the default BASE_DIR (before any Config.json override)
if getattr(sys, "frozen", False):
    _default_base = os.path.dirname(sys.executable)
elif args.config:
    _default_base = os.path.abspath(args.config)
else:
    _default_base = SCRIPT_DIR

# ── Config.json ───────────────────────────────────────────────────────────────
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
else:
    # Config.json absent (e.g. after uninstall+reinstall) — restore from registry backup
    _config_dir_override = _reg_get_config_dir()

# ── §4.8 Path traversal prevention ────────────────────────────────────────────
_SYSTEM_DIRS = {
    os.environ.get("SystemRoot", "C:\\Windows").lower(),
    os.environ.get("ProgramFiles", "C:\\Program Files").lower(),
    os.environ.get("ProgramW6432", "C:\\Program Files").lower(),
    os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)").lower(),
    "c:\\windows",
    "c:\\system32",
}


def _is_safe_config_path(path: str) -> bool:
    """Reject paths that point at system directories or contain traversal."""
    try:
        canonical = os.path.realpath(os.path.abspath(path))
    except OSError:
        return False
    canonical_lower = canonical.lower()
    for sysdir in _SYSTEM_DIRS:
        if canonical_lower.startswith(sysdir):
            return False
    # Reject UNC paths that could point to network shares used for exfiltration
    if canonical.startswith("\\\\"):
        return False
    return True


if _config_dir_override:
    if _is_safe_config_path(_config_dir_override):
        try:
            os.makedirs(_config_dir_override, exist_ok=True)
            BASE_DIR = _config_dir_override
        except Exception:
            BASE_DIR = _default_base
    else:
        # Unsafe path — ignore override, fall back to default
        BASE_DIR = _default_base
        _config_dir_override = ""
else:
    BASE_DIR = _default_base

# ── Session config tracking & migration ──────────────────────────────────────
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


_DATA_SUBDIRS = ("Data", "Plugins")


def _migrate_config_if_needed(old_path: str, new_path: str, first_run: bool = False) -> None:
    if os.path.normcase(os.path.normpath(old_path)) == \
       os.path.normcase(os.path.normpath(new_path)):
        return

    # Only migrate dirs that actually contain files (empty dirs = installer artefacts)
    to_move = [
        d for d in _DATA_SUBDIRS
        if os.path.isdir(os.path.join(old_path, d)) and _has_files(os.path.join(old_path, d))
    ]
    if not to_move:
        return

    if first_run:
        title   = "InputBar — Existing Data Found"
        message = (
            f"InputBar found existing data in the installation folder:\n\n"
            f"  {old_path}\n\n"
            f"Your configuration is set to store data at:\n  {new_path}\n\n"
            f"Do you want to move your existing data there now?\n"
            f"(Choosing No will start InputBar with a fresh default configuration.)"
        )
    else:
        title   = "InputBar — Configuration Path Changed"
        message = (
            f"The data directory has changed since the last session.\n\n"
            f"Previous location:\n  {old_path}\n\n"
            f"New location:\n  {new_path}\n\n"
            f"Do you want to move your existing data to the new location?"
        )

    if _msgbox_yesno(title, message):
        try:
            os.makedirs(new_path, exist_ok=True)
            for name in to_move:
                src = os.path.join(old_path, name)
                dst = os.path.join(new_path, name)
                shutil.copytree(src, dst, dirs_exist_ok=True)
                shutil.rmtree(src, ignore_errors=True)
        except Exception as exc:
            ctypes.windll.user32.MessageBoxW(
                0,
                f"Failed to move data:\n{exc}\n\nInputBar will launch with the new location.",
                "InputBar — Error",
                0x00000010
            )
    else:
        if _msgbox_yesno(
            "InputBar — Old Data Remains",
            f"Your previous configuration data still exists at:\n  {old_path}\n\n"
            f"Do you want to delete it now?\n"
            f"(InputBar will create fresh default files at the new location.)",
            _MB_ICONWARNING
        ):
            for name in to_move:
                shutil.rmtree(os.path.join(old_path, name), ignore_errors=True)


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
        "InputBar — Unused Data Found",
        f"InputBar found data in the installation folder that is no longer used:\n\n"
        f"{dirs_str}\n\n"
        f"Your active configuration is stored at:\n  {base_dir}\n\n"
        f"Do you want to delete this unused data?",
        _MB_ICONWARNING
    ):
        for d in dead:
            shutil.rmtree(d, ignore_errors=True)


if getattr(sys, "frozen", False) and not IS_CLI_MODE:
    _prev = _read_last_config()
    if _prev:
        _migrate_config_if_needed(_prev, BASE_DIR)
        _cleanup_dead_app_data_if_needed(APP_ROOT, BASE_DIR)
    elif BASE_DIR != APP_ROOT:
        # First frozen run with a custom data dir: offer to pull data from the install dir.
        # Skips _cleanup_dead_app_data_if_needed — migration dialog already covered that data.
        _migrate_config_if_needed(APP_ROOT, BASE_DIR, first_run=True)

# Create Config.json if absent
if not os.path.exists(ROOT_CONFIG_FILE):
    try:
        os.makedirs(ROOT_CONFIG_DIR, exist_ok=True)
        with open(ROOT_CONFIG_FILE, "w", encoding="utf-8") as _f:
            json.dump({"ConfigDirectory": BASE_DIR}, _f, indent=4)
    except Exception:
        pass

# ── Derived directories ───────────────────────────────────────────────────────
CORE_DIR = os.path.join(SCRIPT_DIR, "Core")

# §2.3 dev mode: gen/Data/ only when BASE_DIR is the source root (avoids polluting workspace).
# Custom BASE_DIR (and frozen mode) always use BASE_DIR/Data directly.
if getattr(sys, "frozen", False):
    DATA_DIR = os.path.join(BASE_DIR, "Data")
elif os.path.normcase(os.path.normpath(BASE_DIR)) == os.path.normcase(os.path.normpath(SCRIPT_DIR)):
    _gen_dir = os.path.join(BASE_DIR, "gen")
    DATA_DIR = os.path.join(_gen_dir, "Data")
    # One-time migration: if old src/Data/ exists and gen/Data/ is absent, move it.
    _old_data = os.path.join(BASE_DIR, "Data")
    if os.path.isdir(_old_data) and not os.path.isdir(DATA_DIR):
        try:
            os.makedirs(os.path.dirname(DATA_DIR), exist_ok=True)
            shutil.copytree(_old_data, DATA_DIR)
            shutil.rmtree(_old_data, ignore_errors=True)
        except Exception:
            DATA_DIR = _old_data  # fallback to old location on error
else:
    DATA_DIR = os.path.join(BASE_DIR, "Data")

THEMES_DIR = os.path.join(DATA_DIR, "Themes")
CACHE_DIR  = os.path.join(DATA_DIR, "__pycache__") if not getattr(sys, "frozen", False) else None

PLUGINS_DIR      = os.path.join(SCRIPT_DIR, "Plugins")
PLUGINS_DATA_DIR = os.path.join(BASE_DIR, "Plugins")

if getattr(sys, "frozen", False):
    BUILTIN_THEMES_DIR = os.path.join(
        getattr(sys, "_MEIPASS", os.path.dirname(sys.executable)), "Assets", "Themes"
    )
else:
    BUILTIN_THEMES_DIR = os.path.join(SCRIPT_DIR, "Assets", "Themes")

_dirs_to_create = [
    CORE_DIR, DATA_DIR, THEMES_DIR,
    os.path.join(PLUGINS_DATA_DIR, "App"),
    os.path.join(PLUGINS_DATA_DIR, "Shell"),
    os.path.join(PLUGINS_DATA_DIR, "Everything"),
]
if CACHE_DIR:
    _dirs_to_create.append(CACHE_DIR)

for _folder in _dirs_to_create:
    if not os.path.exists(_folder):
        try:
            os.makedirs(_folder)
        except Exception:
            pass

# ── Data files ────────────────────────────────────────────────────────────────
HISTORY_FILE  = os.path.join(DATA_DIR, "search_history.json")
PLUGINS_FILE  = os.path.join(DATA_DIR, "Plugins.json")
SETTINGS_FILE = os.path.join(DATA_DIR, "Settings.json")

LOG_FILE = os.path.join(tempfile.gettempdir(), "InputBar.log")

_write_last_config(BASE_DIR)
_reg_set_config_dir(BASE_DIR)

# WinKeyHook daemon paths
_pf              = os.environ.get("ProgramW6432", os.environ.get("ProgramFiles", "C:\\Program Files"))
WINKEYHOOK_EXE   = os.path.join(_pf, "Ephraem", "Daemons", "WinKeyHook.exe")
WINKEYHOOK_SETUP_EXE = os.path.join(APP_ROOT, "Lib", "WinKeyHook_setup.exe")


# ── §8.3 Atomic JSON write helper ─────────────────────────────────────────────

def atomic_write_json(path: str, data: object) -> None:
    """Write JSON atomically: write to .tmp → rename to final path."""
    tmp = path + ".tmp"
    try:
        dir_ = os.path.dirname(path)
        if dir_:
            os.makedirs(dir_, exist_ok=True)
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        os.replace(tmp, path)
    except Exception:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise
