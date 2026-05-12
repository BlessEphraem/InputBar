import os
import json
import queue
import subprocess
import threading
import time

import win32file
import win32pipe
import pywintypes

from Core.Paths import DATA_DIR, SETTINGS_FILE, WINKEYHOOK_EXE, WINKEYHOOK_SETUP_EXE
from Core.Logging import dprint, eprint

HOTKEYS_FILE = os.path.join(DATA_DIR, "hotkeys.json")

_WIN_KEY_NAMES = {"lwin", "rwin", "win"}

_MODIFIERS = {"ctrl", "alt", "shift", "lwin", "rwin", "win",
              "lctrl", "rctrl", "lalt", "ralt", "lshift", "rshift"}

_ALIASES: dict[str, str] = {
    "left ctrl":    "lctrl",
    "right ctrl":   "rctrl",
    "left alt":     "lalt",
    "right alt":    "ralt",
    "left shift":   "lshift",
    "right shift":  "rshift",
    "left win":     "lwin",
    "right win":    "rwin",
    "numpad0": "num0", "numpad1": "num1", "numpad2": "num2",
    "numpad3": "num3", "numpad4": "num4", "numpad5": "num5",
    "numpad6": "num6", "numpad7": "num7", "numpad8": "num8",
    "numpad9": "num9",
    "num *": "num*", "num +": "num+", "num -": "num-",
    "num .": "num.", "num /": "num/",
    "media next track": "next track",
    "media prev track": "previous track",
    "media play/pause": "play/pause",
    "media stop":       "stop",
    "esc": "escape",
    "windows": "win",
}

# Canonical short form → keyboard lib name (fallback path only)
_TO_KB_LIB: dict[str, str] = {
    "lctrl":  "left ctrl",
    "rctrl":  "right ctrl",
    "lalt":   "left alt",
    "ralt":   "right alt",
    "lshift": "left shift",
    "rshift": "right shift",
    "num0": "numpad0", "num1": "numpad1", "num2": "numpad2",
    "num3": "numpad3", "num4": "numpad4", "num5": "numpad5",
    "num6": "numpad6", "num7": "numpad7", "num8": "numpad8",
    "num9": "numpad9",
    "num*": "num *", "num+": "num +", "num-": "num -",
    "num.": "num .", "num/": "num /",
    "next track":     "media next track",
    "previous track": "media prev track",
    "play/pause":     "media play/pause",
    "stop":           "media stop",
}

# InputBar canonical → WinKeyHook spec token
# Keys with spaces or different names need explicit mapping; rest just .upper()
_TO_WKH: dict[str, str] = {
    "page up":        "PGUP",
    "page down":      "PGDN",
    "print screen":   "PRINT",
    "scroll lock":    "SCROLL",
    "caps lock":      "CAPS",
    "num lock":       "NUMLOCK",
    "num*":           "0x6A",
    "num+":           "0x6B",
    "num-":           "0x6D",
    "num.":           "0x6E",
    "num/":           "0x6F",
    "volume mute":    "0xAD",
    "volume down":    "0xAE",
    "volume up":      "0xAF",
    "next track":     "0xB0",
    "previous track": "0xB1",
    "stop":           "0xB2",
    "play/pause":     "0xB3",
}

PIPE_NAME    = r"\\.\pipe\WinKeyHook"
_HOTKEY_NAME = "show_inputbar"

_pipe_handle:     object | None       = None
_write_queue:     queue.Queue         = queue.Queue()
_reader_thread:   threading.Thread | None = None
_registered_spec: str                 = ""


# ─────────────────────────────────────────────
#  hotkeys.json config
# ─────────────────────────────────────────────

def _migrate_from_config() -> str | None:
    if not os.path.exists(SETTINGS_FILE):
        return None
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        hotkey = cfg.pop("hotkey", None)
        if hotkey is not None:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=4)
            dprint(f"Hotkeys: 'hotkey' key migrated from Settings.json → '{hotkey}'")
            return hotkey
    except Exception as e:
        eprint(f"Hotkeys: Settings.json migration error ({e})")
    return None


def load_hotkeys() -> dict:
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
#  Parsing & translation
# ─────────────────────────────────────────────

def _normalize_hotkey(hotkey: str) -> str:
    parts = [p.strip().lower() for p in hotkey.split("+") if p.strip()]
    return "+".join(_ALIASES.get(p, p) for p in parts)


def _parse_hotkey(hotkey: str) -> tuple[bool, list[str]]:
    parts   = [p.strip().lower() for p in hotkey.split("+") if p.strip()]
    has_win = any(p in _WIN_KEY_NAMES for p in parts)
    return has_win, parts


def _translate_to_wkh(hotkey: str) -> str:
    """Convert InputBar canonical format to WinKeyHook spec (e.g. 'lwin+a' → 'LWIN+A')."""
    parts = [p.strip().lower() for p in hotkey.split("+") if p.strip()]
    return "+".join(_TO_WKH.get(p, p.upper()) for p in parts)


# ─────────────────────────────────────────────
#  WinKeyHook daemon client
# ─────────────────────────────────────────────

def _try_connect() -> bool:
    global _pipe_handle
    try:
        h = win32file.CreateFile(
            PIPE_NAME,
            win32file.GENERIC_READ | win32file.GENERIC_WRITE,
            0, None, win32file.OPEN_EXISTING, 0, None,
        )
        _pipe_handle = h
        dprint("Hotkeys: connected to WinKeyHook pipe")
        return True
    except pywintypes.error:
        return False


def _ensure_installed() -> bool:
    if os.path.exists(str(WINKEYHOOK_EXE)):
        return True
    if not os.path.exists(str(WINKEYHOOK_SETUP_EXE)):
        eprint("Hotkeys: WinKeyHook setup not found in Lib/")
        return False
    dprint("Hotkeys: WinKeyHook not installed — running silent installer...")
    try:
        subprocess.run([
            "powershell", "-Command",
            f'Start-Process -FilePath "{WINKEYHOOK_SETUP_EXE}" -ArgumentList "/SILENT" -Verb RunAs -Wait',
        ], check=True, capture_output=True)
    except Exception as e:
        eprint(f"Hotkeys: WinKeyHook install failed ({e})")
        return False
    return os.path.exists(str(WINKEYHOOK_EXE))


def _launch_daemon() -> None:
    if not os.path.exists(str(WINKEYHOOK_EXE)):
        eprint(f"Hotkeys: WinKeyHook.exe not found at {WINKEYHOOK_EXE}")
        return
    try:
        proc = subprocess.Popen(
            [str(WINKEYHOOK_EXE), "0"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        first = proc.stdout.readline().strip()
        dprint(f"Hotkeys: WinKeyHook daemon → {first.decode(errors='replace')}")
    except Exception as e:
        eprint(f"Hotkeys: failed to launch WinKeyHook daemon ({e})")


def _start_reader(callback_show) -> None:
    global _reader_thread

    def _run():
        global _pipe_handle
        buf = b""
        while True:
            h = _pipe_handle
            if h is None:
                time.sleep(0.3)
                continue
            try:
                # Drain outbound queue — reader thread is sole pipe writer
                while True:
                    try:
                        msg = _write_queue.get_nowait()
                        win32file.WriteFile(h, msg)
                    except queue.Empty:
                        break
                    except pywintypes.error:
                        break

                avail = win32pipe.PeekNamedPipe(h, 0)[1]
                if avail == 0:
                    time.sleep(0.01)
                    continue

                _, data = win32file.ReadFile(h, 4096)
                if not data:
                    continue
                buf += data
                while b"\n" in buf:
                    raw, buf = buf.split(b"\n", 1)
                    line = raw.decode(errors="replace").strip()
                    if line:
                        dprint(f"Hotkeys [pipe←]: {line}")
                        if line.startswith(f"TRIGGERED {_HOTKEY_NAME}"):
                            callback_show()

            except pywintypes.error as e:
                eprint(f"Hotkeys: pipe error ({e}) — reconnecting")
                _pipe_handle = None
                buf = b""
                while not _write_queue.empty():
                    try: _write_queue.get_nowait()
                    except queue.Empty: break
                time.sleep(0.5)
                if _try_connect() and _registered_spec:
                    _write_queue.put(f"REGISTER {_registered_spec} {_HOTKEY_NAME}\n".encode())

    _reader_thread = threading.Thread(target=_run, daemon=True, name="WinKeyHook-reader")
    _reader_thread.start()
    dprint("Hotkeys: reader thread started")


# ─────────────────────────────────────────────
#  Main entry point
# ─────────────────────────────────────────────

def register_hotkeys(hotkeys_config: dict, callback_show) -> None:
    global _registered_spec

    show_key = hotkeys_config.get("show_inputbar", "").strip()
    if not show_key:
        dprint("Hotkeys: no 'show_inputbar' configured")
        return

    has_win, parts = _parse_hotkey(show_key)
    wkh_spec = _translate_to_wkh(show_key)

    _ensure_installed()

    connected = _try_connect()
    if not connected:
        _launch_daemon()
        for _ in range(20):
            time.sleep(0.1)
            if _try_connect():
                connected = True
                break

    if connected:
        _registered_spec = wkh_spec
        _write_queue.put(f"REGISTER {wkh_spec} {_HOTKEY_NAME}\n".encode())
        _start_reader(callback_show)
        dprint(f"Hotkeys: registered '{show_key}' → '{wkh_spec}' via WinKeyHook daemon")
        return

    # WinKeyHook unavailable: fall back to keyboard lib for non-Win hotkeys
    if has_win:
        eprint(
            f"Hotkeys: WinKeyHook daemon not available — "
            f"Win key hotkey '{show_key}' cannot be registered"
        )
        return

    dprint(f"Hotkeys: WinKeyHook unavailable — falling back to keyboard lib for '{show_key}'")
    try:
        import keyboard as kb
        kb_parts  = [_TO_KB_LIB.get(p, p) for p in parts]
        kb_hotkey = "+".join(kb_parts)
        kb.add_hotkey(kb_hotkey, callback_show)
        dprint(f"Hotkeys: fallback registered '{show_key}' via keyboard lib")
    except Exception as e:
        eprint(f"Hotkeys: fallback failed for '{show_key}' ({e})")


def stop_hotkeys() -> None:
    global _pipe_handle, _registered_spec
    if _pipe_handle is not None:
        if _registered_spec:
            try:
                msg = f"UNREGISTER {_HOTKEY_NAME}\n".encode()
                win32file.WriteFile(_pipe_handle, msg)
            except Exception:
                pass
        try:
            win32file.CloseHandle(_pipe_handle)
        except Exception:
            pass
        _pipe_handle = None
        _registered_spec = ""
        dprint("Hotkeys: pipe closed, hotkeys stopped")
