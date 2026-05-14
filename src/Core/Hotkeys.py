import ctypes
import hashlib
import json
import os
import queue
import subprocess
import threading
import time
from typing import Callable

import win32file
import win32pipe
import pywintypes

from Core.Paths import (
    DATA_DIR, SETTINGS_FILE, WINKEYHOOK_EXE, WINKEYHOOK_SETUP_EXE,
    atomic_write_json,
)
from Core.Logging import log_debug, log_error, log_warn

HOTKEYS_FILE = os.path.join(DATA_DIR, "hotkeys.json")

# ── Hotkeys schema ────────────────────────────────────────────────────────────
_HOTKEYS_SCHEMA_VERSION = 1

# ── WinKeyHook pipe constants ─────────────────────────────────────────────────
PIPE_NAME          = r"\\.\pipe\WinKeyHook"
_HOTKEY_NAME       = "show_inputbar"
_READ_BUFFER_SIZE  = 4096

# Retry / timing constants
_PIPE_CONNECT_RETRIES    = 20
_PIPE_RETRY_DELAY_S      = 0.1
_PIPE_RECONNECT_DELAY_S  = 0.5
_PIPE_POLL_INTERVAL_S    = 0.01
_PIPE_IDLE_WAIT_S        = 0.3

# Install prompt
_MB_YESNO        = 0x00000004
_MB_ICONQUESTION = 0x00000020
_IDYES           = 6

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

# ── State ─────────────────────────────────────────────────────────────────────
_pipe_lock:       threading.Lock       = threading.Lock()
_pipe_handle:     object | None        = None
_write_queue:     queue.Queue          = queue.Queue()
_reader_thread:   threading.Thread | None = None
_registered_spec: str                  = ""
_is_running:      threading.Event      = threading.Event()


# ── hotkeys.json ──────────────────────────────────────────────────────────────

def _migrate_from_config() -> str | None:
    if not os.path.exists(SETTINGS_FILE):
        return None
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        hotkey = cfg.pop("hotkey", None)
        if hotkey is not None:
            atomic_write_json(SETTINGS_FILE, cfg)
            log_debug(f"Hotkeys: 'hotkey' migrated from Settings.json → '{hotkey}'")
            return hotkey
    except Exception as e:
        log_error(f"Hotkeys: Settings.json migration error ({e})")
    return None


def load_hotkeys() -> dict:
    default_hotkeys = {
        "schema_version": _HOTKEYS_SCHEMA_VERSION,
        "show_inputbar":  "ctrl+space",
    }

    if not os.path.exists(HOTKEYS_FILE):
        migrated = _migrate_from_config()
        if migrated:
            default_hotkeys["show_inputbar"] = migrated
        try:
            atomic_write_json(HOTKEYS_FILE, default_hotkeys)
            log_debug(f"Hotkeys: file created ({HOTKEYS_FILE})")
        except Exception as e:
            log_error(f"Hotkeys: error creating file ({e})")
        return default_hotkeys

    try:
        with open(HOTKEYS_FILE, "r", encoding="utf-8") as f:
            user_hotkeys = json.load(f)
    except Exception as e:
        log_error(f"Hotkeys: read error ({e})")
        return default_hotkeys

    updated = False
    for key, value in default_hotkeys.items():
        if key not in user_hotkeys:
            user_hotkeys[key] = value
            updated = True

    for key, value in list(user_hotkeys.items()):
        if key == "schema_version":
            continue
        normalised = _normalize_hotkey(value)
        if normalised != value:
            log_debug(f"Hotkeys: normalised '{value}' → '{normalised}'")
            user_hotkeys[key] = normalised
            updated = True

    if updated:
        try:
            atomic_write_json(HOTKEYS_FILE, user_hotkeys)
            log_debug("Hotkeys: hotkeys.json updated")
        except Exception as e:
            log_error(f"Hotkeys: save error ({e})")

    return user_hotkeys


# ── Parsing & translation ─────────────────────────────────────────────────────

def _normalize_hotkey(hotkey: str) -> str:
    parts = [p.strip().lower() for p in hotkey.split("+") if p.strip()]
    return "+".join(_ALIASES.get(p, p) for p in parts)


def _parse_hotkey(hotkey: str) -> tuple[bool, list[str]]:
    parts   = [p.strip().lower() for p in hotkey.split("+") if p.strip()]
    has_win = any(p in _WIN_KEY_NAMES for p in parts)
    return has_win, parts


def _translate_to_wkh(hotkey: str) -> str:
    parts = [p.strip().lower() for p in hotkey.split("+") if p.strip()]
    return "+".join(_TO_WKH.get(p, p.upper()) for p in parts)


# ── Security: SHA-256 verification ───────────────────────────────────────────

def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_expected_sha256() -> str:
    """Read expected WinKeyHook installer hash from build/project.json if available."""
    try:
        # project.json lives at APP_ROOT/../build/project.json relative to exe,
        # or at SCRIPT_DIR/../../build/project.json in dev mode
        from Core.Paths import APP_ROOT, SCRIPT_DIR
        candidates = [
            os.path.join(os.path.dirname(APP_ROOT), "build", "project.json"),
            os.path.join(SCRIPT_DIR, "..", "..", "build", "project.json"),
        ]
        for path in candidates:
            path = os.path.normpath(path)
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f).get("winkeyhook_sha256", "")
    except Exception:
        pass
    return ""


# ── WinKeyHook daemon client ──────────────────────────────────────────────────

def _try_connect() -> bool:
    global _pipe_handle
    try:
        h = win32file.CreateFile(
            PIPE_NAME,
            win32file.GENERIC_READ | win32file.GENERIC_WRITE,
            0, None, win32file.OPEN_EXISTING, 0, None,
        )
        with _pipe_lock:
            _pipe_handle = h
        log_debug("Hotkeys: connected to WinKeyHook pipe")
        return True
    except pywintypes.error:
        return False


def _prompt_install() -> bool:
    """Ask user before installing WinKeyHook. Returns True if user agreed."""
    result = ctypes.windll.user32.MessageBoxW(
        0,
        "WinKeyHook is required to register global hotkeys (including Win key combinations).\n\n"
        "Install it now?\n\n"
        "The installer will run with administrator privileges.",
        "InputBar — Dependency Required",
        _MB_YESNO | _MB_ICONQUESTION,
    )
    return result == _IDYES


def _ensure_installed() -> bool:
    if os.path.exists(str(WINKEYHOOK_EXE)):
        return True
    if not os.path.exists(str(WINKEYHOOK_SETUP_EXE)):
        log_error("Hotkeys: WinKeyHook setup not found in Lib/")
        return False

    if not _prompt_install():
        log_warn("Hotkeys: user declined WinKeyHook installation")
        return False

    # §4.4 Verify SHA-256 before execution
    expected_hash = _load_expected_sha256()
    if expected_hash:
        actual_hash = _sha256_file(str(WINKEYHOOK_SETUP_EXE))
        if actual_hash.lower() != expected_hash.lower():
            ctypes.windll.user32.MessageBoxW(
                0,
                f"WinKeyHook installer integrity check failed.\n\n"
                f"Expected: {expected_hash}\n"
                f"Got:      {actual_hash}\n\n"
                f"Installation aborted. Please re-download InputBar.",
                "InputBar — Security Error",
                0x00000010,  # MB_ICONERROR
            )
            log_error(f"Hotkeys: SHA-256 mismatch on WinKeyHook installer — install aborted")
            return False
    else:
        log_warn("Hotkeys: no expected SHA-256 configured — skipping integrity check")

    log_debug("Hotkeys: installing WinKeyHook (user approved)...")
    try:
        subprocess.run([
            "powershell", "-Command",
            f'Start-Process -FilePath "{WINKEYHOOK_SETUP_EXE}" -ArgumentList "/SILENT" -Verb RunAs -Wait',
        ], check=True, capture_output=True)
    except Exception as e:
        log_error(f"Hotkeys: WinKeyHook install failed ({e})")
        return False
    return os.path.exists(str(WINKEYHOOK_EXE))


def _launch_daemon() -> None:
    if not os.path.exists(str(WINKEYHOOK_EXE)):
        log_error(f"Hotkeys: WinKeyHook.exe not found at {WINKEYHOOK_EXE}")
        return
    try:
        proc = subprocess.Popen(
            [str(WINKEYHOOK_EXE), "0"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        first = proc.stdout.readline().strip()
        log_debug(f"Hotkeys: WinKeyHook daemon → {first.decode(errors='replace')}")
    except Exception as e:
        log_error(f"Hotkeys: failed to launch WinKeyHook daemon ({e})")


def _start_reader(callback_show: Callable) -> None:
    global _reader_thread

    def _run() -> None:
        global _pipe_handle
        buf = b""
        while _is_running.is_set():
            with _pipe_lock:
                h = _pipe_handle
            if h is None:
                time.sleep(_PIPE_IDLE_WAIT_S)
                continue
            try:
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
                    time.sleep(_PIPE_POLL_INTERVAL_S)
                    continue

                _, data = win32file.ReadFile(h, _READ_BUFFER_SIZE)
                if not data:
                    continue
                buf += data
                while b"\n" in buf:
                    raw, buf = buf.split(b"\n", 1)
                    line = raw.decode(errors="replace").strip()
                    if line:
                        log_debug(f"Hotkeys [pipe←]: {line}")
                        if line.startswith(f"TRIGGERED {_HOTKEY_NAME}"):
                            callback_show()

            except pywintypes.error as e:
                log_error(f"Hotkeys: pipe error ({e}) — reconnecting")
                with _pipe_lock:
                    _pipe_handle = None
                buf = b""
                while not _write_queue.empty():
                    try:
                        _write_queue.get_nowait()
                    except queue.Empty:
                        break
                if not _is_running.is_set():
                    break
                time.sleep(_PIPE_RECONNECT_DELAY_S)
                if _try_connect() and _registered_spec:
                    _write_queue.put(f"REGISTER {_registered_spec} {_HOTKEY_NAME}\n".encode())

    _reader_thread = threading.Thread(target=_run, daemon=True, name="WinKeyHook-reader")
    _reader_thread.start()
    log_debug("Hotkeys: reader thread started")


# ── Main entry points ─────────────────────────────────────────────────────────

_UPDATE_TIMEOUT_S = 30


def check_dependency() -> bool:
    """
    Pre-check: verify WinKeyHook is installed (or install it).
    Called early in startup before GUI — see §8.1.
    Returns True if WinKeyHook is available (or not needed yet).
    """
    return _ensure_installed()


def check_winkeyhook_update() -> None:
    """
    Run 'WinKeyHook.exe --update' in a background daemon thread.
    WinKeyHook handles version comparison and installer launch internally.
    No-op in dev mode or if WinKeyHook is not installed.
    """
    if not os.path.exists(str(WINKEYHOOK_EXE)):
        return

    def _run() -> None:
        log_debug("Hotkeys: checking WinKeyHook for updates...")
        try:
            result = subprocess.run(
                [str(WINKEYHOOK_EXE), "--update"],
                capture_output=True,
                text=True,
                timeout=_UPDATE_TIMEOUT_S,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            for line in result.stdout.splitlines():
                if line.strip():
                    log_debug(f"WinKeyHook update: {line.strip()}")
        except subprocess.TimeoutExpired:
            log_warn("Hotkeys: WinKeyHook update check timed out")
        except Exception as e:
            log_warn(f"Hotkeys: WinKeyHook update check failed ({e})")

    threading.Thread(target=_run, daemon=True, name="WinKeyHook-updater").start()


def register_hotkeys(hotkeys_config: dict, callback_show: Callable) -> None:
    global _registered_spec

    show_key = hotkeys_config.get("show_inputbar", "").strip()
    if not show_key:
        log_debug("Hotkeys: no 'show_inputbar' configured")
        return

    has_win, parts = _parse_hotkey(show_key)
    wkh_spec = _translate_to_wkh(show_key)

    _is_running.set()

    connected = _try_connect()
    if not connected:
        _launch_daemon()
        for _ in range(_PIPE_CONNECT_RETRIES):
            time.sleep(_PIPE_RETRY_DELAY_S)
            if _try_connect():
                connected = True
                break

    if connected:
        _registered_spec = wkh_spec
        _write_queue.put(f"REGISTER {wkh_spec} {_HOTKEY_NAME}\n".encode())
        _start_reader(callback_show)
        log_debug(f"Hotkeys: registered '{show_key}' → '{wkh_spec}' via WinKeyHook")
        return

    if has_win:
        log_error(
            f"Hotkeys: WinKeyHook unavailable — "
            f"Win key hotkey '{show_key}' cannot be registered"
        )
        return

    log_debug(f"Hotkeys: WinKeyHook unavailable — falling back to keyboard lib for '{show_key}'")
    try:
        import keyboard as kb
        kb_parts  = [_TO_KB_LIB.get(p, p) for p in parts]
        kb_hotkey = "+".join(kb_parts)
        kb.add_hotkey(kb_hotkey, callback_show)
        log_debug(f"Hotkeys: fallback registered '{show_key}' via keyboard lib")
    except Exception as e:
        log_error(f"Hotkeys: fallback failed for '{show_key}' ({e})")


def stop_hotkeys() -> None:
    global _pipe_handle, _registered_spec

    _is_running.clear()

    with _pipe_lock:
        h = _pipe_handle

    if h is not None:
        if _registered_spec:
            try:
                win32file.WriteFile(h, f"UNREGISTER {_HOTKEY_NAME}\n".encode())
            except Exception:
                pass
        try:
            win32file.CloseHandle(h)
        except Exception:
            pass
        with _pipe_lock:
            _pipe_handle = None
        _registered_spec = ""
        log_debug("Hotkeys: pipe closed, hotkeys stopped")

    if _reader_thread is not None and _reader_thread.is_alive():
        _reader_thread.join(timeout=2.0)
