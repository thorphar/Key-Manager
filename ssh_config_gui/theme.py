"""Application theme and branding."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPainterPath, QPalette, QPixmap
from PySide6.QtWidgets import QApplication

APP_NAME = "Key Manager"
APP_TAGLINE = "SSH & AWS profiles"

COLORS = {
    "bg": "#F4F6F8",
    "surface": "#FFFFFF",
    "sidebar": "#FFFFFF",
    "border": "#E2E8F0",
    "text": "#0F172A",
    "muted": "#64748B",
    "accent": "#2563EB",
    "accent_hover": "#1D4ED8",
    "accent_soft": "#EFF6FF",
    "danger": "#DC2626",
    "success": "#16A34A",
}


def make_terminal_icon(size: int = 20) -> QIcon:
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    margin = max(2, size // 6)
    body = QPainterPath()
    body.addRoundedRect(margin, margin, size - margin * 2, size - margin * 2, 3, 3)
    painter.fillPath(body, QColor(COLORS["muted"]))

    painter.setPen(QColor("#FFFFFF"))
    font = QFont("Consolas", max(7, size // 3))
    font.setWeight(QFont.Weight.Bold)
    painter.setFont(font)
    painter.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter, ">_")
    painter.end()
    return QIcon(pix)


def make_app_icon(size: int = 64) -> QIcon:
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    path = QPainterPath()
    path.addRoundedRect(4, 4, size - 8, size - 8, size * 0.22, size * 0.22)
    painter.fillPath(path, QColor(COLORS["accent"]))

    painter.setPen(QColor("#FFFFFF"))
    font = QFont("Segoe UI", int(size * 0.42))
    font.setWeight(QFont.Weight.DemiBold)
    painter.setFont(font)
    painter.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter, "C")
    painter.end()
    return QIcon(pix)


def _apply_palette(app: QApplication) -> None:
    c = COLORS
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(c["bg"]))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(c["text"]))
    palette.setColor(QPalette.ColorRole.Base, QColor(c["surface"]))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#F8FAFC"))
    palette.setColor(QPalette.ColorRole.Text, QColor(c["text"]))
    palette.setColor(QPalette.ColorRole.Button, QColor(c["surface"]))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(c["text"]))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(c["accent"]))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#FFFFFF"))
    app.setPalette(palette)


def apply_theme(app: QApplication) -> None:
    app.setStyle("Fusion")
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    _apply_palette(app)

    c = COLORS
    # Do NOT set background on QWidget globally — it paints child widgets and
    # causes white/gray blocks behind text inside fields and labels.
    app.setStyleSheet(
        f"""
        QMainWindow {{
            background-color: {c['bg']};
            color: {c['text']};
        }}

        QLabel {{
            background: transparent;
            color: {c['text']};
            border: none;
        }}

        #sidebar {{
            background-color: {c['sidebar']};
            border-right: 1px solid {c['border']};
        }}

        #sidebarTitle {{
            font-size: 15px;
            font-weight: 600;
            padding: 4px 0;
        }}

        #sidebarSubtitle {{
            color: {c['muted']};
            font-size: 11px;
        }}

        QListWidget#navList {{
            background: transparent;
            border: none;
            outline: none;
            padding: 8px 6px;
        }}

        QListWidget#navList::item {{
            color: {c['muted']};
            border-radius: 8px;
            padding: 12px 14px;
            margin: 2px 0;
        }}

        QListWidget#navList::item:selected {{
            background-color: {c['accent_soft']};
            color: {c['accent']};
            font-weight: 600;
        }}

        QListWidget#navList::item:hover:!selected {{
            background-color: #F1F5F9;
            color: {c['text']};
        }}

        #headerBar {{
            background-color: {c['surface']};
            border-bottom: 1px solid {c['border']};
        }}

        #headerTitle {{
            font-size: 18px;
            font-weight: 600;
        }}

        #headerSubtitle {{
            font-size: 12px;
            color: {c['muted']};
        }}

        #unsavedBadge {{
            color: {c['danger']};
            font-size: 12px;
            font-weight: 600;
            padding: 4px 10px;
            background: #FEF2F2;
            border-radius: 12px;
        }}

        #contentHost {{
            background-color: {c['bg']};
        }}

        QGroupBox#contentCard {{
            background-color: {c['surface']};
            border: 1px solid {c['border']};
            border-radius: 10px;
            margin-top: 10px;
            padding: 20px 16px 16px 16px;
            font-weight: 600;
        }}

        QGroupBox#contentCard::title {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 0 4px;
            color: {c['text']};
        }}

        #formBody {{
            background: transparent;
        }}

        QLabel#formLabel {{
            background: transparent;
            color: {c['muted']};
            padding: 0 12px 0 0;
            min-width: 120px;
        }}

        QScrollArea {{
            background: transparent;
            border: none;
        }}

        QLineEdit, QSpinBox, QComboBox {{
            background-color: {c['surface']};
            color: {c['text']};
            border: 1px solid {c['border']};
            border-radius: 8px;
            padding: 8px 12px;
            min-height: 22px;
            selection-background-color: {c['accent']};
            selection-color: white;
        }}

        QListWidget {{
            background-color: {c['surface']};
            border: 1px solid {c['border']};
            border-radius: 10px;
            padding: 4px;
            outline: none;
        }}

        QListWidget::item {{
            border-radius: 6px;
            padding: 8px 10px;
        }}

        QListWidget::item:selected {{
            background-color: {c['accent_soft']};
            color: {c['text']};
        }}

        QPushButton {{
            background-color: {c['surface']};
            border: 1px solid {c['border']};
            border-radius: 8px;
            padding: 10px 16px;
            color: {c['text']};
        }}

        QPushButton:hover {{
            background-color: #F8FAFC;
            border-color: #CBD5E1;
        }}

        QPushButton:pressed {{
            background-color: #F1F5F9;
        }}

        QPushButton#primaryButton {{
            background-color: {c['accent']};
            border: 1px solid {c['accent']};
            color: white;
            font-weight: 600;
            padding: 10px 18px;
        }}

        QPushButton#primaryButton:hover {{
            background-color: {c['accent_hover']};
            border-color: {c['accent_hover']};
        }}

        QPushButton#ghostButton {{
            background: transparent;
            border: 1px solid transparent;
            color: {c['muted']};
        }}

        QPushButton#ghostButton:hover {{
            background: #F1F5F9;
            color: {c['text']};
        }}

        QToolButton#hostTerminalButton {{
            background: transparent;
            border: none;
            border-radius: 6px;
            padding: 4px;
            min-width: 28px;
            min-height: 28px;
        }}

        QToolButton#hostTerminalButton:hover {{
            background: {c['accent_soft']};
        }}

        QCheckBox {{
            background: transparent;
            spacing: 8px;
            padding: 8px 0;
            margin-bottom: 6px;
        }}

        QCheckBox::indicator {{
            width: 18px;
            height: 18px;
            border-radius: 4px;
            border: 1px solid {c['border']};
            background: {c['surface']};
        }}

        QCheckBox::indicator:checked {{
            background: {c['accent']};
            border-color: {c['accent']};
        }}

        QStatusBar {{
            background: {c['surface']};
            border-top: 1px solid {c['border']};
            color: {c['muted']};
            font-size: 12px;
        }}

        QSplitter::handle {{
            background: {c['border']};
            width: 1px;
        }}

        QLabel#pathLabel, QLabel#hintLabel {{
            color: {c['muted']};
            font-size: 12px;
        }}

        QToolTip {{
            background: {c['text']};
            color: white;
            border: none;
            padding: 6px 8px;
            border-radius: 6px;
        }}
        """
    )
