import os
import re
import sys
import ctypes
import subprocess
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLineEdit,
                             QListWidget, QListWidgetItem, QGraphicsDropShadowEffect,
                             QFrame, QFileIconProvider, QStyle, QApplication, QStyledItemDelegate,
                             QStyleOptionViewItem)
from PyQt6.QtCore import Qt, QEvent, QFileInfo, QSize, QTimer, QRect
from PyQt6.QtGui import QCursor, QColor, QIcon, QFont, QPainter, QFontMetrics

from Core.Paths import IS_CLI_MODE
from Core.Search import process_search, save_to_history
from Core.Logging import eprint
from Core.Icons import load_svg_icon

# Custom UserRole constants for list items
_ROLE_ACTION   = Qt.ItemDataRole.UserRole       # callable action or file path
_ROLE_ITEMTYPE = Qt.ItemDataRole.UserRole + 1   # "app" | None
_ROLE_EXEPATH  = Qt.ItemDataRole.UserRole + 2   # resolved exe path (may be None)
_ROLE_SUBTITLE = Qt.ItemDataRole.UserRole + 3   # Second line info (e.g. path)


class ResultItemDelegate(QStyledItemDelegate):
    def __init__(self, parent=None, theme=None):
        super().__init__(parent)
        self.theme = theme or {}

    def _parse_color(self, color_val, default_hex="#0078D4"):
        """Helper to parse list [R,G,B,A] or string 'rgba(R,G,B,A)' into QColor."""
        if isinstance(color_val, list) and len(color_val) >= 3:
            a = color_val[3] if len(color_val) > 3 else 255
            return QColor(color_val[0], color_val[1], color_val[2], a)
        
        if isinstance(color_val, str):
            color_val = color_val.strip()
            if color_val.startswith("rgba"):
                try:
                    m = re.findall(r"(\d+\.?\d*)", color_val)
                    if len(m) >= 4:
                        return QColor(int(m[0]), int(m[1]), int(m[2]), int(float(m[3]) * 255))
                except Exception: pass
            elif color_val.startswith("rgb"):
                try:
                    m = re.findall(r"(\d+)", color_val)
                    if len(m) >= 3:
                        return QColor(int(m[0]), int(m[1]), int(m[2]))
                except Exception: pass
            
            # Try to let QColor handle hex or named colors
            c = QColor(color_val)
            if c.isValid():
                return c
        
        return QColor(default_hex)

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index):
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        r_cfg = self.theme.get("results_list", {})
        
        # Draw background (handles hover/selected)
        if option.state & QStyle.StateFlag.State_Selected:
            bg_color = self._parse_color(r_cfg.get('selected_background', 'rgba(0, 120, 212, 1.0)'))
            painter.fillRect(option.rect, bg_color)
        
        # Get data
        name     = index.data(Qt.ItemDataRole.DisplayRole)
        subtitle = index.data(_ROLE_SUBTITLE)
        icon     = index.data(Qt.ItemDataRole.DecorationRole)

        padding = int(str(r_cfg.get('item_padding', '8px')).replace("px", ""))
        rect = option.rect
        
        # Draw Icon
        icon_size = int(r_cfg.get('icon_size', 24))
        if icon:
            icon_rect = QRect(rect.left() + padding, rect.top() + (rect.height() - icon_size) // 2, icon_size, icon_size)
            icon.paint(painter, icon_rect)
        
        # Text areas
        text_x = rect.left() + padding + icon_size + padding
        available_width = rect.width() - text_x - padding
        
        if option.state & QStyle.StateFlag.State_Selected:
            text_color = self._parse_color(r_cfg.get('selected_text_color', 'white'), 'white')
        else:
            text_color = self._parse_color(r_cfg.get('text_color', '#ddd'), '#ddd')
        
        # Setup Font from theme
        font_family = r_cfg.get("font_family", "Segoe UI")
        theme_size_str = str(r_cfg.get("font_size", "15px")).replace("px", "")
        try: theme_size = int(theme_size_str)
        except Exception: theme_size = 15
        
        base_font = QFont(font_family)
        base_font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        painter.setPen(text_color)
        
        if subtitle:
            # Two-line mode: center using metrics and theme values
            sub_ratio = float(r_cfg.get('subtitle_font_ratio', 1.0))
            line_space = int(r_cfg.get('line_spacing', 0))
            
            # Title Font & Metrics
            title_font = QFont(base_font)
            title_font.setPixelSize(theme_size)
            title_font.setWeight(int(r_cfg.get('font_weight', 400)))
            painter.setFont(title_font)
            fm_title = painter.fontMetrics()
            h_title = fm_title.height()
            
            # Subtitle Font & Metrics
            sub_font = QFont(base_font)
            sub_font.setPixelSize(max(1, int(theme_size * sub_ratio)))
            sub_font.setWeight(int(r_cfg.get('subtitle_font_weight', 400)))
            fm_sub = QFontMetrics(sub_font)
            h_sub = fm_sub.height()
            
            # Total height of the text block
            total_text_h = h_title + line_space + h_sub
            start_y = rect.top() + (rect.height() - total_text_h) // 2
            
            # Draw Title - Height expansion to avoid clipping
            title_rect = QRect(text_x, start_y, available_width, h_title + 10)
            painter.drawText(title_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, name)
            
            # Draw Subtitle
            painter.setFont(sub_font)
            sub_color = QColor(text_color)
            sub_color.setAlpha(int(r_cfg.get('subtitle_opacity', 160)))
            painter.setPen(sub_color)
            
            sub_y = start_y + h_title + line_space
            sub_rect = QRect(text_x, sub_y, available_width, h_sub + 10)
            short_sub = self.shorten_path(subtitle, painter, available_width)
            painter.drawText(sub_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, short_sub)
        else:
            # Single line mode: full theme size
            base_font.setPixelSize(theme_size)
            base_font.setWeight(int(r_cfg.get('font_weight', 400)))
            painter.setFont(base_font)
            title_rect = QRect(text_x, rect.top(), available_width, rect.height())
            painter.drawText(title_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, name)

        painter.restore()

    def sizeHint(self, option, index):
        r      = self.theme.get("results_list", {})
        base_h = int(r.get("height", 36))

        return QSize(option.rect.width(), base_h)

    def shorten_path(self, path, painter, width):
        r"""Intelligent path elision: C:\Users\...\folder"""
        metrics = painter.fontMetrics()
        if metrics.horizontalAdvance(path) <= width:
            return path
        
        # Basic elision if path is not really a path
        if "\\" not in path and "/" not in path:
            return metrics.elidedText(path, Qt.TextElideMode.ElideMiddle, width)

        # Path-aware elision
        parts = path.replace("/", "\\").split("\\")
        if len(parts) < 3:
            return metrics.elidedText(path, Qt.TextElideMode.ElideMiddle, width)
            
        start = parts[0] + "\\" + parts[1]
        end = parts[-1]
        
        # Try to build with ellipsis
        for i in range(2, len(parts) - 1):
             candidate = f"{start}\\...\\{'\\'.join(parts[i:])}"
             if metrics.horizontalAdvance(candidate) <= width:
                 return candidate
        
        return f"{start}\\...\\{end}"


class InputBarUI(QWidget):
    def __init__(self, config, theme, plugins):
        super().__init__()
        self.config  = config
        self.theme   = theme
        self.plugins = plugins
        _icons_cfg = self.theme.get("icons", {})
        self._color_map = {
            "settings": _icons_cfg.get("settings", "#888888"),
            "plugin":   _icons_cfg.get("plugin",   "#00BFFF"),
            "shell":    _icons_cfg.get("shell",    "#888888"),
            "system":   _icons_cfg.get("system",   "#888888"),
        }
        self.icon_provider   = QFileIconProvider()
        self._search_id = 0
        # File/app sub-menu state (right arrow)
        # None = normal mode; dict = {"saved_query", "action", "exe_path", "item_name", "item_type"}
        self._submenu_state = None

        self.focus_timer = QTimer(self)
        self.focus_timer.timeout.connect(self.check_focus)

        self.init_ui()
        QTimer.singleShot(200, self._run_startup)

    def _run_startup(self):
        self.search_bar.setPlaceholderText("Loading...")
        self.show_input_bar()
        QTimer.singleShot(50, self._warmup_and_clear)

    def _warmup_and_clear(self):
        # Full warmup on a visible window so Qt computes real layout/icons
        self.update_results_ui("a")
        self.results_list.hide()
        self.results_list.clear()
        self.search_bar.clear()
        s = self.theme.get("search_bar", {})
        self.search_bar.setPlaceholderText(s.get("placeholder", "Search..."))
        self.search_bar.setFocus(Qt.FocusReason.ActiveWindowFocusReason)

    def check_focus(self):
        """Fallback focus poll — hides the window if it lost focus.
        Acts as a safety net for cases where changeEvent may not fire
        (e.g. certain Qt.WindowType.Tool configurations on Windows)."""
        if not self.isVisible():
            self.focus_timer.stop()
            return
        if not self.isActiveWindow():
            self.hide()

    def init_ui(self):
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
        if self.config.get("AlwaysOnTop", True):
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)

        w_cfg  = self.theme.get("window", {})
        win_w  = int(w_cfg.get("width",  620))
        # win_h is now the search bar height
        self.bar_h = int(w_cfg.get("height", 50))
        self.margin = int(w_cfg.get("margin", 50))
        
        self.setFixedWidth(win_w)
        # Initial height: margin * 2 + padding * 2 + bar_h
        c_cfg = self.theme.get("container", {})
        self.container_padding = int(c_cfg.get("padding", 10))
        self.container_spacing = int(c_cfg.get("spacing", 8))
        
        initial_h = (self.margin * 2) + (self.container_padding * 2) + self.bar_h
        self.setFixedHeight(initial_h)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(self.margin, self.margin, self.margin, self.margin)
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.container = QFrame()
        self.container.setObjectName("Container")
        self.container.setStyleSheet(f"""
            QFrame#Container {{
                background-color: {c_cfg.get('background', 'rgba(46, 46, 46, 0.85)')};
                border: {c_cfg.get('border', 'none')};
                border-radius: {c_cfg.get('border_radius', '0px')};
            }}
        """)

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(int(c_cfg.get("shadow_blur",     25)))
        shadow.setXOffset(  int(c_cfg.get("shadow_x_offset",  0)))
        shadow.setYOffset(  int(c_cfg.get("shadow_y_offset",  5)))
        sc = c_cfg.get("shadow_color", [0, 0, 0, 180])
        shadow.setColor(QColor(sc[0], sc[1], sc[2], sc[3]))
        self.container.setGraphicsEffect(shadow)

        self.inner_layout = QVBoxLayout(self.container)
        self.inner_layout.setContentsMargins(self.container_padding, self.container_padding, self.container_padding, self.container_padding)
        self.inner_layout.setSpacing(self.container_spacing)

        s = self.theme.get("search_bar", {})

        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText(s.get("placeholder", "Search..."))
        self.search_bar.setFixedHeight(self.bar_h)
        self.search_bar.setStyleSheet(f"""
            QLineEdit {{
                background-color: {s.get('background', 'rgba(61, 61, 61, 0.90)')};
                color: {s.get('text_color', 'white')};
                border: {s.get('border', 'none')};
                border-radius: {s.get('border_radius', '4px')};
                padding: {s.get('padding', '12px')};
                font-size: {s.get('font_size', '18px')};
                font-family: {s.get('font_family', 'Segoe UI')};
                font-weight: {s.get('font_weight', 400)};
            }}
        """)
        self.search_bar.textChanged.connect(self.update_results_ui)
        self.inner_layout.addWidget(self.search_bar)

        r  = self.theme.get("results_list", {})
        sb = self.theme.get("scrollbar", {})

        self.results_list = QListWidget()
        self.results_list.setIconSize(QSize(24, 24))
        self.results_list.setSpacing(0)
        self.results_list.setItemDelegate(ResultItemDelegate(self.results_list, self.theme))
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
                padding: 0px;
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
        self.results_list.hide()
        self.inner_layout.addWidget(self.results_list)

        self.main_layout.addWidget(self.container)

        # Install global event filter for keyboard shortcuts
        self.search_bar.installEventFilter(self)
        self.results_list.installEventFilter(self)

        self.hide()

    def update_results_ui(self, text):
        self._search_id += 1
        current_search_id = self._search_id

        if not text.strip():
            self.results_list.hide()
            self.results_list.clear()
            return

        self.results_list.clear()

        result_generator = process_search(text, self.plugins)

        has_items = False
        count = 0

        for res in result_generator:
            if self._search_id != current_search_id:
                return  # Abort if user typed something new

            item = QListWidgetItem(res["name"])
            item.setData(_ROLE_ACTION,   res["action"])
            item.setData(_ROLE_ITEMTYPE, res.get("item_type"))
            item.setData(_ROLE_EXEPATH,  res.get("exe_path"))
            item.setData(_ROLE_SUBTITLE, res.get("subtitle"))

            try:
                icon_path = res.get("icon_path")
                if icon_path and os.path.exists(icon_path):
                    item.setIcon(QIcon(icon_path.replace("\\", "/")))
                elif res.get("icon_type") == "file":
                    exe_val    = res.get("exe_path") or ""
                    action_val = res.get("action", "")
                    file_path  = (
                        exe_val if (exe_val and os.path.exists(exe_val))
                        else (action_val if isinstance(action_val, str) else "")
                    )
                    if file_path and os.path.exists(file_path):
                        item.setIcon(self.icon_provider.icon(QFileInfo(file_path)))
                elif res.get("icon_type") == "app":
                    item.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_TitleBarMenuButton))
                elif res.get("icon_type") == "calc":
                    item.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon))
                elif res.get("icon_type") in ("settings", "plugin", "shell", "system"):
                    _it = res["icon_type"]
                    item.setIcon(load_svg_icon(_it, self._color_map.get(_it, "#888888")))
            except Exception:
                pass

            self.results_list.addItem(item)
            has_items = True
            count += 1

            # Process events periodically to keep UI responsive and allow cancellation
            if count % 3 == 0:
                QApplication.processEvents()

        if has_items and self._search_id == current_search_id:
            # Dynamic height calculation
            r_cfg = self.theme.get("results_list", {})
            max_items = int(r_cfg.get("MaxItemToShow", 8))
            item_h = int(r_cfg.get("height", 36))
            
            # Uniform height for all items
            display_count = min(self.results_list.count(), max_items)
            total_list_h = display_count * item_h

            self.results_list.setFixedHeight(total_list_h)
            
            # Update window height
            new_win_h = (self.margin * 2) + (self.container_padding * 2) + self.bar_h + self.container_spacing + total_list_h
            self.setFixedHeight(new_win_h)
            
            self.results_list.show()
            if self.results_list.currentRow() == -1 and self.results_list.count() > 0:
                self.results_list.setCurrentRow(0)
        elif not has_items and self._search_id == current_search_id:
            self.results_list.hide()
            initial_h = (self.margin * 2) + (self.container_padding * 2) + self.bar_h
            self.setFixedHeight(initial_h)

    def launch_app(self):
        current_item = self.results_list.currentItem()
        if current_item:
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
                item_type = current_item.data(_ROLE_ITEMTYPE) if current_item else None
                if item_type in ("app", "file"):
                    self._open_file_submenu(current_item)
                    return True
            elif event.key() == Qt.Key.Key_Left and self._submenu_state is not None:
                self._exit_submenu()
                return True
        return super().eventFilter(obj, event)

    # ------------------------------------------------------------------ #
    #  File/app sub-menu (right arrow key)                                #
    # ------------------------------------------------------------------ #

    def _open_file_submenu(self, item: QListWidgetItem):
        """Opens the action sub-menu for the selected app or file."""
        action    = item.data(_ROLE_ACTION)
        exe_path  = item.data(_ROLE_EXEPATH)
        item_name = item.text()
        item_type = item.data(_ROLE_ITEMTYPE)

        # Lazy .lnk resolution if not already done
        if exe_path is None and isinstance(action, str) and action.endswith(".lnk"):
            exe_path = self._resolve_lnk(action)

        self._submenu_state = {
            "saved_query": self.search_bar.text(),
            "action":      action,
            "exe_path":    exe_path,
            "item_name":   item_name,
            "item_type":   item_type,
        }
        self._show_file_submenu(exe_path, action)

    def _show_file_submenu(self, exe_path: str | None, action: str):
        """Replaces the list with the file/app action sub-menu."""
        state     = self._submenu_state
        icons_cfg = self.theme.get("icons", {})

        def start_as_admin():
            target = exe_path or action
            try:
                ctypes.windll.shell32.ShellExecuteW(None, "runas", target, None, None, 1)
            except Exception as e:
                eprint(f"Start as admin error: {e}")
            self.hide()

        def open_folder():
            target = exe_path or (action if isinstance(action, str) and not action.startswith("shell:appsFolder") else None)
            if not target:
                return
            # If the target itself is a folder, open it directly
            if os.path.isdir(target):
                folder = target
            else:
                folder = os.path.dirname(target)
            if os.path.isdir(folder):
                try:
                    subprocess.Popen(["explorer", folder])
                except Exception as e:
                    eprint(f"Open folder error: {e}")
            self.hide()

        def copy_file_path():
            target = exe_path or (action if isinstance(action, str) else "")
            if target:
                QApplication.clipboard().setText(target)
            self.hide()

        def go_back():
            saved = state["saved_query"]
            self._submenu_state = None
            self.search_bar.blockSignals(True)
            self.search_bar.setText(saved)
            self.search_bar.blockSignals(False)
            return "KEEP_OPEN_AND_REFRESH"

        # "Start as admin" only for actual executables
        target_path = exe_path or (action if isinstance(action, str) else "")
        is_exe = bool(target_path) and target_path.lower().endswith(".exe")

        submenu_items = []
        if is_exe:
            submenu_items.append((
                "Start as admin", start_as_admin,
                "admin", icons_cfg.get("admin", "#FF8C00"),
            ))
        submenu_items.extend([
            ("Open folder",    open_folder,    "folder",     icons_cfg.get("folder",      "#FFD700")),
            ("Copy file path", copy_file_path, "system",     icons_cfg.get("system",      "#888888")),
            ("Back",           go_back,        "arrow-left", icons_cfg.get("arrow_left",  "#FFFFFF")),
        ])

        self.results_list.clear()
        for label, fn, icon_name, icon_color in submenu_items:
            list_item = QListWidgetItem(f"  {label}")
            list_item.setData(_ROLE_ACTION,   fn)
            list_item.setData(_ROLE_ITEMTYPE, "submenu_action")
            list_item.setData(_ROLE_EXEPATH,  None)
            list_item.setIcon(load_svg_icon(icon_name, icon_color))
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

    def hide(self):
        """Override hide to clear content before the window disappears, preventing DWM flash on next show."""
        self.search_bar.blockSignals(True)
        self.search_bar.clear()
        self.search_bar.blockSignals(False)
        self.results_list.hide()
        self.results_list.clear()
        initial_h = (self.margin * 2) + (self.container_padding * 2) + self.bar_h
        self.setFixedHeight(initial_h)
        self.repaint()
        QApplication.processEvents()
        super().hide()

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
