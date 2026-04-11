import os
import sys
import ctypes
import subprocess
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLineEdit,
                             QListWidget, QListWidgetItem, QGraphicsDropShadowEffect,
                             QFrame, QFileIconProvider, QStyle, QApplication)
from PyQt6.QtCore import Qt, QEvent, QFileInfo, QSize, QTimer
from PyQt6.QtGui import QCursor, QColor, QIcon

from Core.Paths import IS_CLI_MODE
from Core.Search import process_search, save_to_history
from Core.Logging import eprint

# Custom UserRole constants for list items
_ROLE_ACTION   = Qt.ItemDataRole.UserRole       # callable action or file path
_ROLE_ITEMTYPE = Qt.ItemDataRole.UserRole + 1   # "app" | None
_ROLE_EXEPATH  = Qt.ItemDataRole.UserRole + 2   # resolved exe path (may be None)


class InputBarUI(QWidget):
    def __init__(self, config, theme, plugins):
        super().__init__()
        self.config  = config
        self.theme   = theme
        self.plugins = plugins
        self.cli_mode = IS_CLI_MODE
        self.action_executed = False
        self.icon_provider   = QFileIconProvider()
        # App sub-menu state (right arrow)
        # None = normal mode; dict = {"saved_query", "action", "exe_path", "app_name"}
        self._submenu_state = None

        self.focus_timer = QTimer(self)
        self.focus_timer.timeout.connect(self.check_focus)

        self.init_ui()

    def check_focus(self):
        """Polls every 100ms to check whether the window still has Windows focus."""
        if not self.isVisible():
            self.focus_timer.stop()
            return

    def init_ui(self):
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
        if self.config.get("AlwaysOnTop", True):
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)

        w_cfg  = self.theme.get("window", {})
        win_w  = int(w_cfg.get("width",  620))
        win_h  = int(w_cfg.get("height", 500))
        margin = int(w_cfg.get("margin", 50))
        self.setFixedSize(win_w, win_h)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(margin, margin, margin, margin)
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        c = self.theme.get("container", {})

        self.container = QFrame()
        self.container.setObjectName("Container")
        self.container.setStyleSheet(f"""
            QFrame#Container {{
                background-color: {c.get('background', 'rgba(46, 46, 46, 0.85)')};
                border: {c.get('border', 'none')};
                border-radius: {c.get('border_radius', '0px')};
            }}
        """)

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(int(c.get("shadow_blur",     25)))
        shadow.setXOffset(  int(c.get("shadow_x_offset",  0)))
        shadow.setYOffset(  int(c.get("shadow_y_offset",  5)))
        sc = c.get("shadow_color", [0, 0, 0, 180])
        shadow.setColor(QColor(sc[0], sc[1], sc[2], sc[3]))
        self.container.setGraphicsEffect(shadow)

        padding = int(c.get("padding", 10))
        self.inner_layout = QVBoxLayout(self.container)
        self.inner_layout.setContentsMargins(padding, padding, padding, padding)
        self.inner_layout.setSpacing(int(c.get("spacing", 8)))

        s = self.theme.get("search_bar", {})

        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText(s.get("placeholder", "Search..."))
        self.search_bar.setStyleSheet(f"""
            QLineEdit {{
                background-color: {s.get('background', 'rgba(61, 61, 61, 0.90)')};
                color: {s.get('text_color', 'white')};
                border: {s.get('border', 'none')};
                border-radius: {s.get('border_radius', '4px')};
                padding: {s.get('padding', '12px')};
                font-size: {s.get('font_size', '18px')};
                font-family: {s.get('font_family', 'Segoe UI')};
            }}
        """)
        self.search_bar.textChanged.connect(self.update_results_ui)
        self.inner_layout.addWidget(self.search_bar)

        r  = self.theme.get("results_list", {})
        sb = self.theme.get("scrollbar", {})

        self.results_list = QListWidget()
        self.results_list.setIconSize(QSize(24, 24))
        self.results_list.setStyleSheet(f"""
            QListWidget {{
                background-color: {r.get('background', 'transparent')};
                color: {r.get('text_color', '#ddd')};
                border: none;
                font-size: {r.get('font_size', '15px')};
                font-family: {r.get('font_family', 'Segoe UI')};
                outline: none;
            }}
            QListWidget::item {{
                padding: {r.get('item_padding', '8px')};
                border-radius: {r.get('item_border_radius', '4px')};
            }}
            QListWidget::item:selected {{
                background-color: {r.get('selected_background', 'rgba(0, 120, 212, 1.0)')};
                color: {r.get('selected_text_color', 'white')};
            }}
            QScrollBar:vertical {{
                background: {sb.get('background', 'transparent')};
                width: {sb.get('width', '6px')};
                border: none;
            }}
            QScrollBar::handle:vertical {{
                background: {sb.get('handle_color', 'rgba(100, 100, 100, 0.6)')};
                border-radius: {sb.get('border_radius', '3px')};
                min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {sb.get('handle_hover_color', 'rgba(150, 150, 150, 0.8)')};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: transparent;
            }}
        """)
        self.results_list.setFixedHeight(int(r.get("height", 350)))
        self.results_list.hide()
        self.inner_layout.addWidget(self.results_list)

        self.main_layout.addWidget(self.container)

        # Install global event filter for keyboard shortcuts
        self.search_bar.installEventFilter(self)
        self.results_list.installEventFilter(self)

        self.hide()

    def update_results_ui(self, text):
        if not text.strip():
            self.results_list.hide()
            self.results_list.clear()
            return

        self.results_list.clear()
        all_results = process_search(text, self.plugins)

        # Enforce ListMax cap
        list_max = self.config.get("ListMax", 200)
        try:
            list_max = max(0, min(int(list_max), 200))
        except:
            list_max = 200

        if all_results:
            all_results = all_results[:list_max]
            for res in all_results:
                item = QListWidgetItem(res["name"])
                item.setData(_ROLE_ACTION,   res["action"])
                item.setData(_ROLE_ITEMTYPE, res.get("item_type"))
                item.setData(_ROLE_EXEPATH,  res.get("exe_path"))

                icon_path = res.get("icon_path")
                if icon_path and os.path.exists(icon_path):
                    item.setIcon(QIcon(icon_path.replace("\\", "/")))
                elif res.get("icon_type") == "file":
                    action_val = res.get("action", "")
                    file_path  = action_val if isinstance(action_val, str) else ""
                    item.setIcon(self.icon_provider.icon(QFileInfo(file_path)))
                elif res.get("icon_type") == "calc":
                    item.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon))
                elif res.get("icon_type") == "settings":
                    item.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView))

                self.results_list.addItem(item)
            self.results_list.show()
            self.results_list.setCurrentRow(0)
        else:
            self.results_list.hide()

    def launch_app(self):
        current_item = self.results_list.currentItem()
        if current_item:
            self.action_executed = True
            action = current_item.data(_ROLE_ACTION)
            save_to_history(current_item.text())

            try:
                if callable(action):
                    res = action()
                    if res == "KEEP_OPEN_AND_REFRESH":
                        self.update_results_ui(self.search_bar.text())
                        return
                else:
                    os.startfile(action)
                self.hide()
            except Exception as e:
                eprint(f"Launch error: {e}")
                self.hide()

    def toggle_visibility(self, search_text=None):
        hide_on_press = self.config.get("HideOnPress", False)

        is_vis    = self.isVisible()
        is_active = self.isActiveWindow()

        should_hide = False

        if is_vis:
            hide_val = str(hide_on_press).lower()
            if hide_val in ["always", "true", "1"]:
                should_hide = True
            elif hide_val == "onfocus":
                should_hide = is_active
            # else False (default behaviour)

        if should_hide:
            self.hide()
        else:
            if search_text is not None:
                self.search_bar.setText(search_text)
            else:
                self.search_bar.clear()
            self.show_input_bar()

    def show_input_bar(self):
        pos_mode = self.config.get("Position", "Center")

        if pos_mode == "AtMouse":
            pos = QCursor.pos()
            self.move(pos.x() - self.width() // 2, pos.y() - 60)
        else:
            screens     = QApplication.screens()
            monitor_idx = self.config.get("Monitor", 0)
            if monitor_idx < 0: monitor_idx = 0
            elif monitor_idx >= len(screens): monitor_idx = len(screens) - 1

            screen = screens[monitor_idx]
            geom   = screen.availableGeometry()
            w, h   = self.width(), self.height()
            x, y   = geom.x(), geom.y()

            if pos_mode == "Center":
                x += (geom.width() - w) // 2
                y += (geom.height() - h) // 2
            elif pos_mode == "Left":       y += (geom.height() - h) // 2
            elif pos_mode == "Right":      x += geom.width() - w;  y += (geom.height() - h) // 2
            elif pos_mode == "Top":        x += (geom.width() - w) // 2
            elif pos_mode == "Bottom":     x += (geom.width() - w) // 2; y += geom.height() - h
            elif pos_mode == "TopRight":   x += geom.width() - w
            elif pos_mode == "BottomLeft": y += geom.height() - h
            elif pos_mode == "BottomRight":x += geom.width() - w;  y += geom.height() - h
            else:
                x += (geom.width() - w) // 2
                y += (geom.height() - h) // 2

            self.move(x, y)

        self.setWindowState(self.windowState() & ~Qt.WindowState.WindowMinimized | Qt.WindowState.WindowActive)
        self.show()
        self.raise_()
        self.activateWindow()

        # Delay focus request by 50ms to let Windows render the window first
        def force_focus():
            self.activateWindow()
            self.search_bar.setFocus(Qt.FocusReason.ActiveWindowFocusReason)
            self.search_bar.selectAll()

        QTimer.singleShot(50, force_focus)

        if self.config.get("HideOnFocusLost", True):
            self.focus_timer.start(100)

    # Global event filter for keyboard shortcuts
    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Escape:
                self.hide()
                return True
            elif event.key() == Qt.Key.Key_Return:
                self.launch_app()
                return True
            elif event.key() == Qt.Key.Key_Down and self.results_list.isVisible():
                loop_list = self.config.get("LoopList", True)
                current   = self.results_list.currentRow()
                max_idx   = self.results_list.count() - 1
                if current < max_idx:
                    self.results_list.setCurrentRow(current + 1)
                elif loop_list:
                    self.results_list.setCurrentRow(0)
                return True
            elif event.key() == Qt.Key.Key_Up and self.results_list.isVisible():
                loop_list = self.config.get("LoopList", True)
                current   = self.results_list.currentRow()
                if current > 0:
                    self.results_list.setCurrentRow(current - 1)
                elif loop_list:
                    self.results_list.setCurrentRow(self.results_list.count() - 1)
                return True
            elif event.key() == Qt.Key.Key_Right and self.results_list.isVisible():
                current_item = self.results_list.currentItem()
                if current_item and current_item.data(_ROLE_ITEMTYPE) == "app":
                    self._open_app_submenu(current_item)
                    return True
            elif event.key() == Qt.Key.Key_Left and self._submenu_state is not None:
                self._exit_submenu()
                return True
        return super().eventFilter(obj, event)

    # ------------------------------------------------------------------ #
    #  App sub-menu (right arrow key)                                      #
    # ------------------------------------------------------------------ #

    def _open_app_submenu(self, item: QListWidgetItem):
        """Opens the action sub-menu for the selected app."""
        action   = item.data(_ROLE_ACTION)
        exe_path = item.data(_ROLE_EXEPATH)
        app_name = item.text()

        # Lazy .lnk resolution if not already done
        if exe_path is None and isinstance(action, str) and action.endswith(".lnk"):
            exe_path = self._resolve_lnk(action)

        self._submenu_state = {
            "saved_query": self.search_bar.text(),
            "action":      action,
            "exe_path":    exe_path,
            "app_name":    app_name,
        }
        self._show_app_submenu(exe_path, action)

    def _show_app_submenu(self, exe_path: str | None, action: str):
        """Replaces the list with the 3 sub-menu actions."""
        state = self._submenu_state

        def start_as_admin():
            target = exe_path or action
            try:
                ctypes.windll.shell32.ShellExecuteW(None, "runas", target, None, None, 1)
            except Exception as e:
                eprint(f"Start as admin error: {e}")
            self.hide()

        def open_folder():
            target = exe_path or (action if not action.startswith("explorer.exe shell:") else None)
            if not target:
                return
            folder = os.path.dirname(target)
            if os.path.isdir(folder):
                try:
                    subprocess.Popen(["explorer", folder])
                except Exception as e:
                    eprint(f"Open folder error: {e}")
            self.hide()

        def go_back():
            saved = state["saved_query"]
            self._submenu_state = None
            self.search_bar.blockSignals(True)
            self.search_bar.setText(saved)
            self.search_bar.blockSignals(False)
            return "KEEP_OPEN_AND_REFRESH"

        submenu_items = [
            ("▶  Start as admin", start_as_admin, QStyle.StandardPixmap.SP_VistaShield),
            ("   Open folder",    open_folder,    QStyle.StandardPixmap.SP_DirOpenIcon),
            ("←  Back",           go_back,        QStyle.StandardPixmap.SP_ArrowLeft),
        ]

        self.results_list.clear()
        for label, fn, pixmap in submenu_items:
            list_item = QListWidgetItem(label)
            list_item.setData(_ROLE_ACTION,   fn)
            list_item.setData(_ROLE_ITEMTYPE, "submenu_action")
            list_item.setData(_ROLE_EXEPATH,  None)
            list_item.setIcon(self.style().standardIcon(pixmap))
            self.results_list.addItem(list_item)

        self.results_list.show()
        self.results_list.setCurrentRow(0)

    def _exit_submenu(self):
        """Exits the sub-menu and restores the previous search query."""
        if self._submenu_state is None:
            return
        saved_query         = self._submenu_state["saved_query"]
        self._submenu_state = None
        self.search_bar.blockSignals(True)
        self.search_bar.setText(saved_query)
        self.search_bar.blockSignals(False)
        self.update_results_ui(saved_query)

    @staticmethod
    def _resolve_lnk(lnk_path: str) -> str | None:
        """Resolves a .lnk shortcut to its target exe path (requires pywin32)."""
        try:
            import win32com.client
            shell    = win32com.client.Dispatch("WScript.Shell")
            shortcut = shell.CreateShortCut(lnk_path)
            target   = shortcut.Targetpath
            return target if target and os.path.exists(target) else None
        except Exception:
            return None

    def changeEvent(self, event):
        if event.type() == QEvent.Type.ActivationChange and not self.isActiveWindow():
            if self.config.get("HideOnFocusLost", True):
                self.hide()

    def hideEvent(self, event):
        self.focus_timer.stop()
        self._submenu_state = None
        self.clearFocus()

        # Clean AHK RunWait release
        if hasattr(self, 'active_client') and self.active_client:
            try:
                self.active_client.write(b"DONE")
                self.active_client.waitForBytesWritten(500)
                self.active_client.disconnectFromServer()
            except Exception:
                pass
            self.active_client = None

        super().hideEvent(event)
