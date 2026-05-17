"""Application bootstrap with theme and optional system tray."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication, QSystemTrayIcon

from ssh_config_gui._version import __version__
from ssh_config_gui.main_window import MainWindow
from ssh_config_gui.theme import APP_NAME, apply_theme, make_app_icon
from ssh_config_gui.tray_app import TrayController


def run_app(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    use_tray = "--no-tray" not in args
    args = [a for a in args if a != "--no-tray"]

    ssh_path = Path(args[0]).expanduser() if len(args) > 0 else None
    aws_config_path = Path(args[1]).expanduser() if len(args) > 1 else None
    aws_credentials_path = Path(args[2]).expanduser() if len(args) > 2 else None

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(__version__)
    app.setOrganizationName("KeyManager")
    app.setWindowIcon(make_app_icon())
    apply_theme(app)

    if use_tray and QSystemTrayIcon.isSystemTrayAvailable():
        app.setQuitOnLastWindowClosed(False)

    window = MainWindow(ssh_path, aws_config_path, aws_credentials_path)
    tray = TrayController(window) if use_tray else None
    window.attach_tray(tray)

    window.show()
    return app.exec()
