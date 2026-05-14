"""
Logging — timestamped, levelled, rotating log writer.

Bootstrap phase: writes to %TEMP%\\InputBar\\bootstrap.log (hardcoded, no deps).
After Paths resolves: call set_log_file(path) to redirect to the definitive log.

Levels:   DEBUG  INFO  WARN  ERROR  FATAL
Dev mode: all levels active.
Frozen:   INFO+ by default; DEBUG activated by --verbose CLI flag.
"""

import os
import sys
import threading
from datetime import datetime, timezone

# ── Bootstrap path (hardcoded — must not import from other local modules) ──────
_BOOTSTRAP_DIR = os.path.join(os.environ.get("TEMP", os.path.join(os.path.expanduser("~"), "AppData", "Local", "Temp")), "InputBar")
_BOOTSTRAP_LOG = os.path.join(_BOOTSTRAP_DIR, "bootstrap.log")

_LOG_FILE: str = _BOOTSTRAP_LOG
_LOG_LOCK      = threading.Lock()
_DEBUG_ENABLED = not getattr(sys, "frozen", False)  # always on in dev; off in release by default

# Rotation policy
_MAX_BYTES  = 5 * 1024 * 1024   # 5 MB
_KEEP_COUNT = 3                  # keep bootstrap + 2 rotated archives


def _ensure_bootstrap_dir() -> None:
    try:
        os.makedirs(_BOOTSTRAP_DIR, exist_ok=True)
    except OSError:
        pass


def set_log_file(path: str) -> None:
    """Redirect writes from bootstrap log to the definitive log file."""
    global _LOG_FILE
    with _LOG_LOCK:
        _LOG_FILE = path


def enable_debug() -> None:
    """Activate DEBUG level in compiled mode (triggered by --verbose flag)."""
    global _DEBUG_ENABLED
    _DEBUG_ENABLED = True


def _rotate_if_needed(log_path: str) -> None:
    """Rotate log_path if it exceeds _MAX_BYTES. Keeps _KEEP_COUNT archives."""
    try:
        if not os.path.exists(log_path):
            return
        if os.path.getsize(log_path) < _MAX_BYTES:
            return
        for i in range(_KEEP_COUNT, 0, -1):
            older = f"{log_path}.{i}"
            newer = f"{log_path}.{i - 1}" if i > 1 else log_path
            if os.path.exists(older):
                os.remove(older)
            if os.path.exists(newer):
                os.rename(newer, older)
    except OSError:
        pass


def _get_caller_module() -> str:
    """Walk the call stack to find the first frame outside Logging.py."""
    try:
        frame = sys._getframe(3)
        filename = frame.f_code.co_filename
        return os.path.splitext(os.path.basename(filename))[0]
    except (AttributeError, ValueError):
        return "unknown"


def _write(level: str, msg: str) -> None:
    now = datetime.now(timezone.utc)
    ts  = now.strftime("%Y-%m-%d %H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"
    module = _get_caller_module()
    line   = f"[{ts}] [{level:<5}] [{module}] {msg}\n"

    with _LOG_LOCK:
        target = _LOG_FILE
        _rotate_if_needed(target)
        try:
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, "a", encoding="utf-8") as f:
                f.write(line)
        except OSError:
            pass


# ── Public API ─────────────────────────────────────────────────────────────────

def log_debug(msg: str) -> None:
    if _DEBUG_ENABLED:
        _write("DEBUG", msg)


def log_info(msg: str) -> None:
    _write("INFO", msg)


def log_warn(msg: str) -> None:
    _write("WARN", msg)


def log_error(msg: str) -> None:
    _write("ERROR", msg)


def log_fatal(msg: str, exit_code: int = 1) -> None:
    _write("FATAL", msg)
    sys.exit(exit_code)


# Aliases — keep old callers working without rename
dprint = log_debug
eprint = log_error


# ── Startup: rotate bootstrap log if oversized ────────────────────────────────
_ensure_bootstrap_dir()
_rotate_if_needed(_BOOTSTRAP_LOG)
