"""
Migrations — one-time migrations and first-run seeding.
Call run_migrations() once at startup, after Core.Paths is imported.
"""
import os
import json
import shutil

from Core.Paths import (
    DATA_DIR, SETTINGS_FILE,
    PLUGINS_DIR, PLUGINS_DATA_DIR,
    atomic_write_json,
)
from Core.Logging import log_debug, log_error

_SETTINGS_KEYS = {
    "Position", "Monitor", "AlwaysOnTop", "HideOnFocusLost",
    "HideOnPress", "LoopList", "Theme",
}

_REMOVED_SETTINGS_KEYS: set[str] = {"ListMax"}

_SEED_FILES: list[tuple[str, str]] = [
    ("App",   "aliases.data"),
    ("Shell", "favorites.data"),
    ("Shell", "default_shell.json"),
]


def _migrate_old_config() -> None:
    """Migrate Data/Config.json → Data/Settings.json (one-time, old-version upgrade)."""
    old_path = os.path.join(DATA_DIR, "Config.json")
    if not os.path.exists(old_path):
        return

    try:
        with open(old_path, "r", encoding="utf-8") as f:
            old_data = json.load(f)

        if (isinstance(old_data, dict)
                and _SETTINGS_KEYS.intersection(old_data.keys())
                and "ConfigDirectory" not in old_data
                and not os.path.exists(SETTINGS_FILE)):
            atomic_write_json(SETTINGS_FILE, old_data)
            log_debug("Migrations: Data/Config.json migrated → Settings.json")

        os.remove(old_path)
        log_debug("Migrations: Data/Config.json removed")
    except Exception as e:
        log_error(f"Migrations: migration error ({e})")


def _seed_plugin_data() -> None:
    """Copy bundled plugin data templates into PLUGINS_DATA_DIR if absent."""
    for sub, fname in _SEED_FILES:
        dst = os.path.join(PLUGINS_DATA_DIR, sub, fname)
        if not os.path.exists(dst):
            src = os.path.join(PLUGINS_DIR, sub, fname)
            if os.path.exists(src):
                try:
                    shutil.copy2(src, dst)
                    log_debug(f"Migrations: seeded {sub}/{fname} → {dst}")
                except Exception as e:
                    log_error(f"Migrations: seed error {sub}/{fname} ({e})")


def _purge_removed_settings() -> None:
    """Remove keys that no longer exist from an existing Settings.json."""
    if not os.path.exists(SETTINGS_FILE):
        return
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        stale = _REMOVED_SETTINGS_KEYS.intersection(data.keys())
        if stale:
            for key in stale:
                del data[key]
            atomic_write_json(SETTINGS_FILE, data)
            log_debug(f"Migrations: removed deprecated key(s): {', '.join(stale)}")
    except Exception as e:
        log_error(f"Migrations: error purging deprecated settings ({e})")


def run_migrations() -> None:
    """Entry point — call once at startup after Core.Paths is imported."""
    _migrate_old_config()
    _purge_removed_settings()
    _seed_plugin_data()
