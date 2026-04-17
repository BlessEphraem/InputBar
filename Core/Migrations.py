"""
Migrations.py — centralises all one-time migrations and first-run seeding.

Call run_migrations() once at startup, after Core.Paths is imported.
"""
import os
import json
import shutil

from Core.Paths import (
    DATA_DIR, SETTINGS_FILE,
    PLUGINS_DIR, PLUGINS_DATA_DIR,
)
from Core.Logging import dprint, eprint

# Settings keys used to recognise the old Data/Config.json format
_SETTINGS_KEYS = {
    "Position", "Monitor", "AlwaysOnTop", "HideOnFocusLost",
    "HideOnPress", "LoopList", "Theme",
}

# Keys that have been removed from Settings and must be purged from existing files
_REMOVED_SETTINGS_KEYS = {"ListMax"}

# Plugin data files that must be seeded into PLUGINS_DATA_DIR on first run
# or whenever ConfigDirectory is redirected to a new location.
_SEED_FILES = [
    ("App",   "aliases.data"),
    ("Shell", "favorites.data"),
    ("Shell", "default_shell.json"),
]


def _migrate_old_config():
    """
    Migrates Data/Config.json → Data/Settings.json (one-time, old-version upgrade).
    The old file is always removed afterwards whether or not migration was needed.
    """
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
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(old_data, f, indent=4)
            dprint("Update: Data/Config.json migrated → Settings.json")

        os.remove(old_path)
        dprint("Update: Data/Config.json removed")
    except Exception as e:
        eprint(f"Update: migration error ({e})")


def _seed_plugin_data():
    """
    Copies bundled plugin data file templates into PLUGINS_DATA_DIR if absent.
    Runs on every startup so a newly redirected ConfigDirectory gets its defaults.
    """
    for sub, fname in _SEED_FILES:
        dst = os.path.join(PLUGINS_DATA_DIR, sub, fname)
        if not os.path.exists(dst):
            src = os.path.join(PLUGINS_DIR, sub, fname)
            if os.path.exists(src):
                try:
                    shutil.copy2(src, dst)
                    dprint(f"Update: seeded {sub}/{fname} → {dst}")
                except Exception as e:
                    eprint(f"Update: seed error {sub}/{fname} ({e})")


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
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
            dprint(f"Update: removed deprecated settings key(s): {', '.join(stale)}")
    except Exception as e:
        eprint(f"Update: error purging deprecated settings ({e})")


def run_migrations() -> None:
    """Entry point — call once at startup after Core.Paths is imported."""
    _migrate_old_config()
    _purge_removed_settings()
    _seed_plugin_data()
