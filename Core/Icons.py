"""
Core/Icons.py — SVG icon loader with theme colour tinting.
"""
import os
import re

from Core.Logging import eprint as _eprint

_ICONS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Assets", "Icons")


def _colorize_svg(svg_text: str, color: str) -> str:
    """Replace fill/currentColor references in SVG with the given colour."""
    svg_text = svg_text.replace("currentColor", color)
    svg_text = re.sub(r'\bfill="(?!none)[^"]*"', f'fill="{color}"', svg_text)
    return svg_text


def load_svg_icon(name: str, color: str = "#FFFFFF", size: int = 24):
    """
    Load Assets/Icons/<name>.svg, tint it with *color*, and return a QIcon.
    Returns an empty QIcon on any failure (missing file, SVG module absent, etc.).
    """
    from PyQt6.QtGui import QIcon
    svg_path = os.path.join(_ICONS_DIR, f"{name}.svg")
    if not os.path.exists(svg_path):
        _eprint(f"Icons: SVG not found: {svg_path}")
        return QIcon()

    try:
        from PyQt6.QtSvg import QSvgRenderer
        from PyQt6.QtCore import QByteArray, Qt
        from PyQt6.QtGui import QPixmap, QPainter

        with open(svg_path, "r", encoding="utf-8") as f:
            svg_text = f.read()

        svg_text = _colorize_svg(svg_text, color)
        renderer = QSvgRenderer(QByteArray(svg_text.encode("utf-8")))
        if not renderer.isValid():
            _eprint(f"Icons: invalid SVG: {svg_path}")
            return QIcon()

        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()

        return QIcon(pixmap)
    except Exception as e:
        _eprint(f"Icons: failed to load '{name}' ({e})")
        return QIcon()
