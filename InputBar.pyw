import sys
import os
import argparse
import time
import subprocess
import threading

# --- CACHE SETUP BEFORE ANY OTHER IMPORTS ---
parser = argparse.ArgumentParser()
parser.add_argument('--search', type=str, help="Text to pre-fill in the search bar")
parser.add_argument('--config', type=str, help="Custom root path for Data and Plugins")
args, unknown = parser.parse_known_args()

IS_CLI_MODE = bool(args.search)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR   = os.path.abspath(args.config) if args.config else SCRIPT_DIR
CACHE_DIR  = os.path.join(BASE_DIR, "Data", "__pycache__")

if not os.path.exists(CACHE_DIR):
    try: os.makedirs(CACHE_DIR)
    except: pass
sys.pycache_prefix = os.path.abspath(CACHE_DIR)

# --- IMPORT MODULES AFTER CACHE IS SET UP ---
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import pyqtSignal, QObject
from PyQt6.QtNetwork import QLocalServer, QLocalSocket

import Core.Paths as Paths
from Core.Logging import dprint, eprint
from Core.Config import load_global_config
from Core.Theme import load_theme, sync_builtin_themes
from Core.Plugins import load_all_modules
from Core.Search import load_history
from Core.GUI import InputBarUI
from Core.Hotkeys import load_hotkeys, register_hotkeys, stop_hotkeys
from Core.Updater import check_for_updates_async


class HotkeySignal(QObject):
    trigger = pyqtSignal()


class QuitSignal(QObject):
    trigger = pyqtSignal()


# ─────────────────────────────────────────────
#  System tray via QSystemTrayIcon (PyQt6)
# ─────────────────────────────────────────────

def _tray_icon_path() -> str:
    if getattr(sys, 'frozen', False):
        base = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
        return os.path.join(base, 'Assets', 'Icons', 'Logo.ico')
    return os.path.join(SCRIPT_DIR, 'Assets', 'Icons', 'Logo.ico')


def setup_tray_icon(window, data_dir: str, quit_callback) -> QSystemTrayIcon:
    """
    Creates and configures the QSystemTrayIcon.
    The icon is parented to the main window to ensure a valid HWND on Windows.
    """
    app = QApplication.instance()
    # Help Windows 11 identify this app (avoids generic grouping under pythonw.exe)
    app.setApplicationName("InputBar")

    import ctypes
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("InputBar.App.1.0")
    except Exception as e:
        eprint(f"Tray: SetAppUserModelID error ({e})")

    # Parent = window (InputBarUI). Critical on Windows to bind the icon to a valid HWND.
    tray_icon = QSystemTrayIcon(window)

    from PyQt6.QtWidgets import QStyle
    from PyQt6.QtGui import QIcon
    from PyQt6.QtCore import QTimer

    # 1. Load a safe system icon first (100% compatible Windows HICON)
    safe_icon = app.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)
    tray_icon.setIcon(safe_icon)

    menu = QMenu(window)

    def open_config():
        try:
            import os
            os.startfile(data_dir)
        except Exception as e:
            eprint(f"Tray: error opening Data folder ({e})")

    config_action = QAction("Configuration", window)
    config_action.triggered.connect(open_config)
    menu.addAction(config_action)

    menu.addSeparator()

    quit_action = QAction("Exit", window)
    quit_action.triggered.connect(quit_callback)
    menu.addAction(quit_action)

    # Keep strong Python references to prevent garbage collection
    tray_icon._menu    = menu
    tray_icon._actions = [config_action, quit_action]

    tray_icon.setContextMenu(menu)
    tray_icon.setToolTip("InputBar")

    def _delayed_show():
        tray_icon.show()
        dprint("Tray: Initial display with fallback icon (ComputerIcon).")

        # 2. After 2 seconds, attempt to switch to Logo.ico
        def _swap_to_custom():
            icon_path   = _tray_icon_path()
            custom_icon = QIcon(icon_path)
            if not custom_icon.isNull():
                tray_icon.setIcon(custom_icon)
                dprint("Tray: Switched to Logo.ico.")
            else:
                eprint(f"Tray: Unable to load Logo.ico from {icon_path}.")

        QTimer.singleShot(2000, _swap_to_custom)

    # Allow the main HWND to be created before showing the tray icon
    QTimer.singleShot(100, _delayed_show)

    dprint("Tray: QSystemTrayIcon initialised")
    return tray_icon


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    # --- 1. ATTEMPT TO CONNECT TO THE RESIDENT SERVER ---
    socket = QLocalSocket()
    socket.connectToServer("InputBar_Singleton_Lock")

    if not socket.waitForConnected(500):
        # Server is not running.
        # If called by AHK (CLI), launch the server as a background process.
        if Paths.IS_CLI_MODE:
            flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            subprocess.Popen([sys.executable, __file__], creationflags=flags)

            # Wait up to 1.5s for the server to be ready
            for _ in range(15):
                time.sleep(0.1)
                socket.connectToServer("InputBar_Singleton_Lock")
                if socket.waitForConnected(500):
                    break

    # If connected, act as a CLIENT (e.g. called from AHK)
    if socket.state() == QLocalSocket.LocalSocketState.ConnectedState:
        if Paths.IS_CLI_MODE and Paths.CLI_SEARCH_TEXT:
            socket.write(f"SEARCH:{Paths.CLI_SEARCH_TEXT}".encode('utf-8'))
        else:
            socket.write(b"SHOW")

        socket.waitForBytesWritten(500)
        socket.waitForReadyRead(-1)
        socket.disconnectFromServer()
        sys.exit(0)

    # --- 2. INITIALISE THE RESIDENT SERVER (runs only once) ---
    server = QLocalServer()
    server.removeServer("InputBar_Singleton_Lock")
    server.listen("InputBar_Singleton_Lock")

    global_config = load_global_config()
    sync_builtin_themes()
    theme         = load_theme(global_config.get("Theme", "theme_default"))
    load_history()
    plugins       = load_all_modules()
    hotkeys_config = load_hotkeys()

    window = InputBarUI(global_config, theme, plugins)
    window.active_client = None

    # Thread-safe signal to quit from the pystray thread
    quit_signal = QuitSignal()
    quit_signal.trigger.connect(lambda: (stop_hotkeys(), app.quit()))

    data_dir = (
        os.path.join(os.path.dirname(sys.executable), 'Data')
        if getattr(sys, 'frozen', False)
        else os.path.join(SCRIPT_DIR, 'Data')
    )

    tray_icon = None
    try:
        tray_icon = setup_tray_icon(window, data_dir, quit_signal.trigger.emit)
    except Exception as e:
        eprint(f"Tray: QSystemTrayIcon startup failed ({e})")

    check_for_updates_async()

    def handle_new_connection():
        client = server.nextPendingConnection()
        if client.waitForReadyRead(500):
            msg = client.readAll().data().decode('utf-8')

            if window.active_client:
                try: window.active_client.disconnectFromServer()
                except: pass
            window.active_client = client

            if msg == "SHOW":
                window.toggle_visibility()
            elif msg.startswith("SEARCH:"):
                window.toggle_visibility(msg[7:])

    server.newConnection.connect(handle_new_connection)

    # Qt signal to call toggle_visibility from any thread
    hotkey_handler = HotkeySignal()
    hotkey_handler.trigger.connect(window.toggle_visibility)

    def _on_hotkey():
        hotkey_handler.trigger.emit()

    register_hotkeys(hotkeys_config, _on_hotkey)

    if Paths.IS_CLI_MODE and Paths.CLI_SEARCH_TEXT:
        window.search_bar.setText(Paths.CLI_SEARCH_TEXT)
        window.show_input_bar()

    exit_code = app.exec()
    stop_hotkeys()
    if tray_icon:
        try:
            tray_icon.hide()
        except Exception:
            pass
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
