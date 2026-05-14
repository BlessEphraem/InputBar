import sys
import os
import json
import signal
import threading
import time
import subprocess
import tempfile

# ── §2.3 pycache redirect (dev mode only) ─────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR   = SCRIPT_DIR
if "--config" in sys.argv:
    idx = sys.argv.index("--config")
    if idx + 1 < len(sys.argv):
        BASE_DIR = os.path.abspath(sys.argv[idx + 1])

if not getattr(sys, "frozen", False):
    import json as _json
    _cfg = os.path.join(SCRIPT_DIR, "Path", "Config.json")
    if os.path.exists(_cfg):
        try:
            with open(_cfg, "r", encoding="utf-8") as _f:
                _override = _json.load(_f).get("ConfigDirectory", "").strip()
            if _override:
                BASE_DIR = _override
        except Exception:
            pass
    del _json, _cfg

    if os.path.normcase(os.path.normpath(BASE_DIR)) == os.path.normcase(os.path.normpath(SCRIPT_DIR)):
        CACHE_DIR = os.path.join(BASE_DIR, "gen", "Data", "__pycache__")
    else:
        CACHE_DIR = os.path.join(BASE_DIR, "Data", "__pycache__")
    if not os.path.exists(CACHE_DIR):
        try:
            os.makedirs(CACHE_DIR)
        except Exception:
            pass
    sys.pycache_prefix = os.path.abspath(CACHE_DIR)

# ── §16 Crash handler — installed before any other import ─────────────────────
def _crash_handler(exc_type, exc_value, exc_tb):
    import traceback
    from datetime import datetime, timezone
    now      = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")
    tmp_dir  = tempfile.gettempdir()
    crash_log = os.path.join(tmp_dir, f"InputBar_crash_{now}.log")
    try:
        with open(crash_log, "w", encoding="utf-8") as _f:
            _f.write(f"InputBar crash — {now}Z\n")
            _f.write(f"Python {sys.version}\n\n")
            traceback.print_exception(exc_type, exc_value, exc_tb, file=_f)
    except Exception:
        pass
    sys.__excepthook__(exc_type, exc_value, exc_tb)
    sys.exit(1)


sys.excepthook = _crash_handler

# ── Qt and Core imports ────────────────────────────────────────────────────────
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import pyqtSignal, QObject
from PyQt6.QtNetwork import QLocalServer, QLocalSocket

import Core.Paths as Paths
from Core.Logging import (
    log_debug, log_info, log_warn, log_error, log_fatal,
    set_log_file, enable_debug,
)
from Core.Migrations import run_migrations
from Core.Settings import load_global_config
from Core.Theme import load_theme, sync_builtin_themes
from Core.Plugins import load_all_modules, teardown_all_plugins
from Core.Search import load_history
from Core.GUI import InputBarUI
from Core.Hotkeys import load_hotkeys, register_hotkeys, stop_hotkeys, check_winkeyhook_update
from Core.Updater import check_for_updates_async

# ── §3.4 Redirect log to definitive path now that Paths is resolved ───────────
set_log_file(Paths.LOG_FILE)
if Paths.VERBOSE_MODE:
    enable_debug()

log_info("InputBar starting up")

# ── Timing / IPC constants ─────────────────────────────────────────────────────
_IPC_CONNECT_TIMEOUT_MS  = 500
_IPC_READ_TIMEOUT_MS     = 500
_IPC_WRITE_TIMEOUT_MS    = 500
_IPC_SINGLETON_WAIT_S    = 0.1
_IPC_SINGLETON_RETRIES   = 15
_TRAY_SHOW_DELAY_MS      = 100
_TRAY_ICON_SWAP_MS       = 2000
_SHUTDOWN_TIMEOUT_S      = 5.0


class HotkeySignal(QObject):
    trigger = pyqtSignal()


class QuitSignal(QObject):
    trigger = pyqtSignal()


# ── §18 IPC message parser (dual mode: plain text + JSON) ─────────────────────

def _parse_ipc_message(raw: str) -> tuple[str, str]:
    """Parse incoming IPC message. Returns (command, arg).
    Accepts both legacy plain text and new JSON envelope format.
    """
    stripped = raw.strip()
    if stripped.startswith("{"):
        try:
            obj = json.loads(stripped)
            cmd = obj.get("command", "").lower()
            arg = obj.get("args", {}).get("text", "") if isinstance(obj.get("args"), dict) else ""
            return cmd, arg
        except (json.JSONDecodeError, AttributeError):
            pass
    # Legacy plain text
    if stripped.upper() == "SHOW":
        return "show", ""
    if stripped.upper().startswith("SEARCH:"):
        return "search", stripped[7:]
    if stripped.upper() == "QUIT":
        return "quit", ""
    return stripped.lower(), ""


# ── System tray ───────────────────────────────────────────────────────────────

def _tray_icon_path() -> str:
    if getattr(sys, "frozen", False):
        base = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
        return os.path.join(base, "Assets", "Icons", "Logo.ico")
    return os.path.join(SCRIPT_DIR, "Assets", "Icons", "Logo.ico")


def setup_tray_icon(window, data_dir: str, quit_callback) -> QSystemTrayIcon:
    app = QApplication.instance()
    app.setApplicationName("InputBar")

    import ctypes
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("InputBar.App.1.0")
    except Exception as e:
        log_error(f"Tray: SetAppUserModelID error ({e})")

    tray_icon = QSystemTrayIcon(window)

    from PyQt6.QtWidgets import QStyle
    from PyQt6.QtCore import QTimer

    safe_icon = app.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)
    tray_icon.setIcon(safe_icon)

    menu = QMenu(window)

    def open_config():
        try:
            os.startfile(data_dir)
        except Exception as e:
            log_error(f"Tray: error opening Data folder ({e})")

    config_action = QAction("Configuration", window)
    config_action.triggered.connect(open_config)
    menu.addAction(config_action)
    menu.addSeparator()

    quit_action = QAction("Exit", window)
    quit_action.triggered.connect(quit_callback)
    menu.addAction(quit_action)

    tray_icon._menu    = menu
    tray_icon._actions = [config_action, quit_action]
    tray_icon.setContextMenu(menu)
    tray_icon.setToolTip("InputBar")

    def _delayed_show():
        tray_icon.show()
        log_debug("Tray: displayed with fallback icon")

        def _swap_to_custom():
            icon_path   = _tray_icon_path()
            custom_icon = QIcon(icon_path)
            if not custom_icon.isNull():
                tray_icon.setIcon(custom_icon)
                log_debug("Tray: switched to Logo.ico")
            else:
                log_error(f"Tray: unable to load Logo.ico from {icon_path}")

        QTimer.singleShot(_TRAY_ICON_SWAP_MS, _swap_to_custom)

    QTimer.singleShot(_TRAY_SHOW_DELAY_MS, _delayed_show)
    log_debug("Tray: QSystemTrayIcon initialised")
    return tray_icon


# ── §13 Graceful shutdown ──────────────────────────────────────────────────────

def _graceful_shutdown(server: QLocalServer, app: QApplication) -> None:
    """Execute shutdown in reverse startup order with a 5-second hard timeout."""
    log_info("InputBar shutting down")

    def _force_exit():
        log_fatal("Graceful shutdown timeout exceeded after 5s — forcing exit", exit_code=1)

    timer = threading.Timer(_SHUTDOWN_TIMEOUT_S, _force_exit)
    timer.daemon = True
    timer.start()

    try:
        stop_hotkeys()
        server.close()
        teardown_all_plugins()
        log_info("InputBar shutdown complete")
    finally:
        timer.cancel()
        app.quit()


def main() -> None:
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    # ── §8.1 Dependency pre-check: WinKeyHook (before GUI) ────────────────────
    # _ensure_installed is called lazily inside register_hotkeys if not done here.
    # Early call surfaces the install prompt before the window appears.
    from Core.Hotkeys import check_dependency
    check_dependency()

    # ── Singleton: try connecting to existing instance ─────────────────────────
    socket = QLocalSocket()
    socket.connectToServer("InputBar_Singleton_Lock")

    if not socket.waitForConnected(_IPC_CONNECT_TIMEOUT_MS):
        if Paths.IS_CLI_MODE:
            flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            subprocess.Popen([sys.executable, __file__], creationflags=flags)

            for _ in range(_IPC_SINGLETON_RETRIES):
                time.sleep(_IPC_SINGLETON_WAIT_S)
                socket.connectToServer("InputBar_Singleton_Lock")
                if socket.waitForConnected(_IPC_CONNECT_TIMEOUT_MS):
                    break

    if socket.state() == QLocalSocket.LocalSocketState.ConnectedState:
        if Paths.IS_CLI_MODE and Paths.CLI_SEARCH_TEXT:
            socket.write(f"SEARCH:{Paths.CLI_SEARCH_TEXT}".encode("utf-8"))
        else:
            socket.write(b"SHOW")
        socket.waitForBytesWritten(_IPC_WRITE_TIMEOUT_MS)
        socket.waitForReadyRead(-1)
        socket.disconnectFromServer()
        sys.exit(Paths.EXIT_SUCCESS)

    # ── Become the resident server ─────────────────────────────────────────────
    server = QLocalServer()
    server.removeServer("InputBar_Singleton_Lock")
    server.listen("InputBar_Singleton_Lock")

    run_migrations()
    global_config  = load_global_config()
    sync_builtin_themes()
    theme          = load_theme(global_config.get("Theme", "theme_default"))
    load_history()
    plugins        = load_all_modules()
    hotkeys_config = load_hotkeys()

    window = InputBarUI(global_config, theme, plugins)
    window.active_client = None

    quit_signal = QuitSignal()

    def _do_quit():
        _graceful_shutdown(server, app)

    quit_signal.trigger.connect(_do_quit)

    # ── §13.1 SIGTERM / SIGINT handling ───────────────────────────────────────
    signal.signal(signal.SIGTERM, lambda *_: quit_signal.trigger.emit())
    signal.signal(signal.SIGINT,  lambda *_: quit_signal.trigger.emit())

    tray_icon = None
    try:
        tray_icon = setup_tray_icon(window, Paths.DATA_DIR, quit_signal.trigger.emit)
    except Exception as e:
        log_error(f"Tray: QSystemTrayIcon startup failed ({e})")

    check_for_updates_async()

    def handle_new_connection():
        client = server.nextPendingConnection()
        if not client.waitForReadyRead(_IPC_READ_TIMEOUT_MS):
            return
        raw = client.readAll().data().decode("utf-8")

        if window.active_client:
            try:
                window.active_client.disconnectFromServer()
            except Exception:
                pass
        window.active_client = client

        command, arg = _parse_ipc_message(raw)
        log_debug(f"IPC: received command='{command}' arg='{arg}'")

        if command == "show":
            window.toggle_visibility()
        elif command == "search":
            window.toggle_visibility(arg)
        elif command == "quit":
            quit_signal.trigger.emit()

    server.newConnection.connect(handle_new_connection)

    hotkey_handler = HotkeySignal()
    hotkey_handler.trigger.connect(window.toggle_visibility)

    def _on_hotkey():
        hotkey_handler.trigger.emit()

    register_hotkeys(hotkeys_config, _on_hotkey)
    check_winkeyhook_update()

    if Paths.IS_CLI_MODE and Paths.CLI_SEARCH_TEXT:
        window.search_bar.setText(Paths.CLI_SEARCH_TEXT)
        window.show_input_bar()

    exit_code = app.exec()

    if tray_icon:
        try:
            tray_icon.hide()
        except Exception:
            pass

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
