import os
import sys
import json
import subprocess
import threading

from Core.Paths import DATA_DIR, CONFIG_FILE
from Core.Logging import dprint, eprint

HOTKEYS_FILE = os.path.join(DATA_DIR, "hotkeys.json")

_WIN_KEY_NAMES = {"lwin", "rwin", "win"}

# Modifier keys recognised for parsing
_MODIFIERS = {"ctrl", "alt", "shift", "lwin", "rwin", "win",
              "lctrl", "rctrl", "lalt", "ralt", "lshift", "rshift"}

# Input variants → canonical short form.
# Applied to every key token when loading/normalising a hotkey string.
_ALIASES: dict[str, str] = {
    # Ctrl
    "left ctrl":    "lctrl",
    "right ctrl":   "rctrl",
    # Alt
    "left alt":     "lalt",
    "right alt":    "ralt",
    # Shift
    "left shift":   "lshift",
    "right shift":  "rshift",
    # Win (already short, kept for completeness)
    "left win":     "lwin",
    "right win":    "rwin",
    # Numpad — long → short
    "numpad0": "num0", "numpad1": "num1", "numpad2": "num2",
    "numpad3": "num3", "numpad4": "num4", "numpad5": "num5",
    "numpad6": "num6", "numpad7": "num7", "numpad8": "num8",
    "numpad9": "num9",
    "num *": "num*", "num +": "num+", "num -": "num-",
    "num .": "num.", "num /": "num/",
    # Media
    "media next track": "next track",
    "media prev track": "previous track",
    "media play/pause": "play/pause",
    "media stop":       "stop",
    # Escape alias
    "esc": "escape",
    # Windows alias
    "windows": "win",
}

# Canonical short form → name expected by the `keyboard` lib (non-Win path only).
_TO_KB_LIB: dict[str, str] = {
    "lctrl":  "left ctrl",
    "rctrl":  "right ctrl",
    "lalt":   "left alt",
    "ralt":   "right alt",
    "lshift": "left shift",
    "rshift": "right shift",
    # Numpad
    "num0": "numpad0", "num1": "numpad1", "num2": "numpad2",
    "num3": "numpad3", "num4": "numpad4", "num5": "numpad5",
    "num6": "numpad6", "num7": "numpad7", "num8": "numpad8",
    "num9": "numpad9",
    "num*": "num *", "num+": "num +", "num-": "num -",
    "num.": "num .", "num/": "num /",
    # Media
    "next track":     "media next track",
    "previous track": "media prev track",
    "play/pause":     "media play/pause",
    "stop":           "media stop",
}

# Mapping: canonical key name → Virtual Key code (Windows VK_*)
_KEY_TO_VK: dict[str, int] = {
    # Letters
    "a": 0x41, "b": 0x42, "c": 0x43, "d": 0x44, "e": 0x45,
    "f": 0x46, "g": 0x47, "h": 0x48, "i": 0x49, "j": 0x4A,
    "k": 0x4B, "l": 0x4C, "m": 0x4D, "n": 0x4E, "o": 0x4F,
    "p": 0x50, "q": 0x51, "r": 0x52, "s": 0x53, "t": 0x54,
    "u": 0x55, "v": 0x56, "w": 0x57, "x": 0x58, "y": 0x59,
    "z": 0x5A,
    # Digits
    "0": 0x30, "1": 0x31, "2": 0x32, "3": 0x33, "4": 0x34,
    "5": 0x35, "6": 0x36, "7": 0x37, "8": 0x38, "9": 0x39,
    # Function keys
    "f1": 0x70, "f2": 0x71, "f3": 0x72, "f4": 0x73,
    "f5": 0x74, "f6": 0x75, "f7": 0x76, "f8": 0x77,
    "f9": 0x78, "f10": 0x79, "f11": 0x7A, "f12": 0x7B,
    "f13": 0x7C, "f14": 0x7D, "f15": 0x7E, "f16": 0x7F,
    "f17": 0x80, "f18": 0x81, "f19": 0x82, "f20": 0x83,
    # Modifiers — generic
    "ctrl": 0x11, "alt": 0x12, "shift": 0x10,
    # Modifiers — sided (canonical short forms)
    "lctrl": 0xA2, "rctrl": 0xA3,
    "lalt":  0xA4, "ralt":  0xA5,
    "lshift":0xA0, "rshift":0xA1,
    # Navigation
    "space": 0x20, "enter": 0x0D, "tab": 0x09, "escape": 0x1B,
    "backspace": 0x08, "delete": 0x2E, "insert": 0x2D,
    "home": 0x24, "end": 0x23, "page up": 0x21, "page down": 0x22,
    "up": 0x26, "down": 0x28, "left": 0x25, "right": 0x27,
    # Numpad (canonical short forms)
    "num0": 0x60, "num1": 0x61, "num2": 0x62, "num3": 0x63,
    "num4": 0x64, "num5": 0x65, "num6": 0x66, "num7": 0x67,
    "num8": 0x68, "num9": 0x69,
    "num*": 0x6A, "num+": 0x6B, "num-": 0x6D, "num.": 0x6E, "num/": 0x6F,
    "num enter": 0x6C,
    # Media (canonical short forms)
    "volume mute": 0xAD, "volume down": 0xAE, "volume up": 0xAF,
    "next track": 0xB0, "previous track": 0xB1,
    "stop": 0xB2, "play/pause": 0xB3,
    # Misc
    "print screen": 0x2C, "scroll lock": 0x91, "pause": 0x13,
    "caps lock": 0x14, "num lock": 0x90,
    "win": 0x5B, "lwin": 0x5B, "rwin": 0x5C,
}

# Internal state
_hook_proc   = None  # winkey_hook.exe subprocess
_hook_thread = None  # stdout reader thread


# ─────────────────────────────────────────────
#  hotkeys.json config
# ─────────────────────────────────────────────

def _migrate_from_config() -> str | None:
    """
    If Config.json still contains a 'hotkey' key, migrate it to hotkeys.json
    and remove it from Config.json.
    """
    if not os.path.exists(CONFIG_FILE):
        return None
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        hotkey = cfg.pop("hotkey", None)
        if hotkey is not None:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=4)
            dprint(f"Hotkeys: 'hotkey' key migrated from Config.json → '{hotkey}'")
            return hotkey
    except Exception as e:
        eprint(f"Hotkeys: Config.json migration error ({e})")
    return None


def load_hotkeys() -> dict:
    """
    Loads Data/hotkeys.json, creates it if missing, and injects new default keys.
    Handles migration from the legacy Config.json['hotkey'] field.
    """
    default_hotkeys = {
        "show_inputbar": "ctrl+space",
    }

    if not os.path.exists(HOTKEYS_FILE):
        migrated = _migrate_from_config()
        if migrated:
            default_hotkeys["show_inputbar"] = migrated

        try:
            with open(HOTKEYS_FILE, "w", encoding="utf-8") as f:
                json.dump(default_hotkeys, f, indent=4)
            dprint(f"Hotkeys: file created ({HOTKEYS_FILE})")
        except Exception as e:
            eprint(f"Hotkeys: error creating file ({e})")
        return default_hotkeys

    try:
        with open(HOTKEYS_FILE, "r", encoding="utf-8") as f:
            user_hotkeys = json.load(f)
    except Exception as e:
        eprint(f"Hotkeys: read error ({e})")
        return default_hotkeys

    updated = False
    for key, value in default_hotkeys.items():
        if key not in user_hotkeys:
            user_hotkeys[key] = value
            updated = True

    # Normalise all values to canonical short forms and rewrite if anything changed
    for key, value in user_hotkeys.items():
        normalised = _normalize_hotkey(value)
        if normalised != value:
            dprint(f"Hotkeys: normalised '{value}' → '{normalised}'")
            user_hotkeys[key] = normalised
            updated = True

    if updated:
        try:
            with open(HOTKEYS_FILE, "w", encoding="utf-8") as f:
                json.dump(user_hotkeys, f, indent=4)
            dprint("Hotkeys: hotkeys.json updated")
        except Exception as e:
            eprint(f"Hotkeys: save error ({e})")

    return user_hotkeys


# ─────────────────────────────────────────────
#  Parsing
# ─────────────────────────────────────────────

def _normalize_hotkey(hotkey: str) -> str:
    """
    Normalises a hotkey string to canonical short forms.
    Example: "Left Ctrl+F1"  → "lctrl+f1"
    Example: "numpad0+space" → "num0+space"
    """
    parts = [p.strip().lower() for p in hotkey.split("+") if p.strip()]
    return "+".join(_ALIASES.get(p, p) for p in parts)


def _parse_hotkey(hotkey: str) -> tuple[bool, list[str]]:
    """
    Splits a (already normalised) hotkey string into parts.
    Returns (has_win_key, parts).
    Example: "lwin+a"     → (True,  ["lwin", "a"])
    Example: "ctrl+space" → (False, ["ctrl", "space"])
    """
    parts   = [p.strip().lower() for p in hotkey.split("+") if p.strip()]
    has_win = any(p in _WIN_KEY_NAMES for p in parts)
    return has_win, parts


def _secondary_keys(parts: list[str]) -> list[str]:
    """Returns all non-Windows keys in the combination."""
    return [p for p in parts if p not in _WIN_KEY_NAMES]


def _keys_to_vk_args(keys: list[str]) -> list[str]:
    """Converts a list of key names to hex arguments for winkey_hook.exe."""
    args = []
    for k in keys:
        vk = _KEY_TO_VK.get(k)
        if vk:
            args.append(hex(vk))
        else:
            eprint(f"Hotkeys: unknown VK for key '{k}' — skipped")
    return args


# ─────────────────────────────────────────────
#  Hook exe path
# ─────────────────────────────────────────────

def _hook_exe_path() -> str:
    if getattr(sys, 'frozen', False):
        # Compiled mode: winkey_hook.exe is inside Core/ within sys._MEIPASS
        base = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
        return os.path.join(base, 'Core', 'winkey_hook.exe')
    # Dev mode: same directory as this .py file
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'winkey_hook.exe')


# ─────────────────────────────────────────────
#  Win Key management via winkey_hook.exe
# ─────────────────────────────────────────────

def _start_win_hook(callback, secondary_keys: list[str]):
    """
    Launches winkey_hook.exe with the parent PID and the VK codes of secondary keys.
    Reads "TRIGGERED" from stdout to fire the callback.
    """
    global _hook_proc, _hook_thread

    exe = _hook_exe_path()
    if not os.path.exists(exe):
        eprint(f"Hotkeys: winkey_hook.exe not found ({exe})")
        return

    vk_args = _keys_to_vk_args(secondary_keys)
    cmd     = [exe, str(os.getpid())] + vk_args

    dprint(f"Hotkeys: launching {' '.join(cmd)}")

    try:
        _hook_proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    except Exception as e:
        eprint(f"Hotkeys: error launching winkey_hook.exe ({e})")
        return

    def _reader():
        try:
            for raw in _hook_proc.stdout:
                line = raw.decode("utf-8", errors="ignore").strip()
                dprint(f"Hotkeys [hook]: {line}")

                if line == "TRIGGERED":
                    callback()
                elif line == "HOOK_STARTED":
                    dprint("Hotkeys: winkey_hook active")
                elif line.startswith("ERREUR"):
                    eprint(f"Hotkeys: winkey_hook error ({line})")
        except Exception as e:
            eprint(f"Hotkeys: hook reader thread error ({e})")

    _hook_thread = threading.Thread(target=_reader, daemon=True)
    _hook_thread.start()
    dprint("Hotkeys: Win Key thread started")


# ─────────────────────────────────────────────
#  Main entry point
# ─────────────────────────────────────────────

def register_hotkeys(hotkeys_config: dict, callback_show):
    """
    Registers the hotkeys defined in hotkeys_config.
    Auto-routing: normal keys → keyboard lib, Win key → winkey_hook.exe
    """
    show_key = hotkeys_config.get("show_inputbar", "").strip()

    if not show_key:
        dprint("Hotkeys: no 'show_inputbar' shortcut configured.")
        return

    has_win, parts = _parse_hotkey(show_key)

    if has_win:
        sec = _secondary_keys(parts)
        dprint(f"Hotkeys: Win key detected ({show_key}) — starting winkey_hook.exe")
        _start_win_hook(callback_show, sec)
    else:
        try:
            import keyboard as kb
            # Translate canonical short forms back to names the keyboard lib understands
            kb_parts  = [_TO_KB_LIB.get(p, p) for p in parts]
            kb_hotkey = "+".join(kb_parts)
            kb.add_hotkey(kb_hotkey, callback_show)
            dprint(f"Hotkeys: shortcut registered ({show_key})")
        except Exception as e:
            eprint(f"Hotkeys: shortcut '{show_key}' invalid or unsupported ({e})")


def stop_hotkeys():
    """Gracefully stops winkey_hook.exe if running."""
    global _hook_proc
    if _hook_proc and _hook_proc.poll() is None:
        try:
            _hook_proc.terminate()
            dprint("Hotkeys: winkey_hook.exe terminated")
        except Exception as e:
            eprint(f"Hotkeys: error stopping hook ({e})")
        _hook_proc = None
