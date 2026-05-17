"""Main window with sidebar navigation and system tray support."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from ssh_config_gui.aws_panel import AwsFilePanel
from ssh_config_gui.config_io import HostEntry
from ssh_config_gui.ssh_panel import SshConfigPanel
from ssh_config_gui._version import __version__
from ssh_config_gui.theme import APP_NAME, APP_TAGLINE
from ssh_config_gui.tray_app import TrayController

_NAV = (
    ("SSH Hosts", "Manage SSH config, keys, and connections"),
    ("AWS Config", "Profiles, regions, and SSO in ~/.aws/config"),
    ("AWS Credentials", "Access keys in ~/.aws/credentials"),
)


class MainWindow(QMainWindow):
    def __init__(
        self,
        ssh_config_path: Path | None = None,
        aws_config_path: Path | None = None,
        aws_credentials_path: Path | None = None,
    ) -> None:
        super().__init__()
        self._tray: TrayController | None = None
        self._settings = QSettings()

        self.setWindowTitle(self._window_title())
        self.resize(1024, 680)
        self.setMinimumSize(860, 520)

        central = QWidget()
        self.setCentralWidget(central)
        shell = QHBoxLayout(central)
        shell.setContentsMargins(0, 0, 0, 0)
        shell.setSpacing(0)

        # —— Sidebar ——
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(220)
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(16, 20, 16, 16)
        side_layout.setSpacing(4)

        title = QLabel(APP_NAME)
        title.setObjectName("sidebarTitle")
        subtitle = QLabel(APP_TAGLINE)
        subtitle.setObjectName("sidebarSubtitle")
        subtitle.setWordWrap(True)
        side_layout.addWidget(title)
        side_layout.addWidget(subtitle)
        side_layout.addSpacing(16)

        self.nav_list = QListWidget()
        self.nav_list.setObjectName("navList")
        for label, _desc in _NAV:
            item = QListWidgetItem(label)
            self.nav_list.addItem(item)
        self.nav_list.setCurrentRow(0)
        self.nav_list.currentRowChanged.connect(self._on_nav_changed)
        side_layout.addWidget(self.nav_list, stretch=1)
        shell.addWidget(sidebar)

        # —— Main column ——
        main_col = QWidget()
        main_layout = QVBoxLayout(main_col)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        header = QWidget()
        header.setObjectName("headerBar")
        header.setFixedHeight(64)
        header_row = QHBoxLayout(header)
        header_row.setContentsMargins(24, 0, 24, 0)

        header_text = QVBoxLayout()
        header_text.setSpacing(2)
        self.header_title = QLabel(_NAV[0][0])
        self.header_title.setObjectName("headerTitle")
        self.header_subtitle = QLabel(_NAV[0][1])
        self.header_subtitle.setObjectName("headerSubtitle")
        header_text.addWidget(self.header_title)
        header_text.addWidget(self.header_subtitle)
        header_row.addLayout(header_text, stretch=1)

        self.unsaved_badge = QLabel("Unsaved changes")
        self.unsaved_badge.setObjectName("unsavedBadge")
        self.unsaved_badge.hide()
        header_row.addWidget(self.unsaved_badge)

        save_all_btn = QPushButton("Save all")
        save_all_btn.setObjectName("primaryButton")
        save_all_btn.clicked.connect(self.save_all)
        header_row.addWidget(save_all_btn)
        main_layout.addWidget(header)

        content_host = QWidget()
        content_host.setObjectName("contentHost")
        content_layout = QVBoxLayout(content_host)
        content_layout.setContentsMargins(20, 16, 20, 16)

        self.stack = QStackedWidget()
        self.ssh_panel = SshConfigPanel(ssh_config_path)
        self.aws_config_panel = AwsFilePanel("config", aws_config_path)
        self.aws_credentials_panel = AwsFilePanel("credentials", aws_credentials_path)
        self.stack.addWidget(self.ssh_panel)
        self.stack.addWidget(self.aws_config_panel)
        self.stack.addWidget(self.aws_credentials_panel)
        content_layout.addWidget(self.stack)
        main_layout.addWidget(content_host, stretch=1)

        shell.addWidget(main_col, stretch=1)

        self.ssh_panel.dirty_changed.connect(self._update_chrome)
        self.aws_config_panel.dirty_changed.connect(self._update_chrome)
        self.aws_credentials_panel.dirty_changed.connect(self._update_chrome)
        self.ssh_panel.hosts_changed.connect(self.refresh_tray_menu)

        self.setStatusBar(QStatusBar())
        self._update_chrome()

    def settings(self) -> QSettings:
        return self._settings

    def attach_tray(self, tray: TrayController | None) -> None:
        self._tray = tray
        if tray:
            self.refresh_tray_menu()

    def refresh_tray_menu(self) -> None:
        if self._tray and self._tray.enabled:
            self._tray.refresh_menu()

    def list_ssh_hosts(self) -> list[HostEntry]:
        return list(self.ssh_panel.config.hosts)

    def show_ssh_host(self, alias: str) -> None:
        self.show_window()
        self.nav_list.setCurrentRow(0)
        self.stack.setCurrentIndex(0)
        for row, host in enumerate(self.ssh_panel.config.hosts):
            if alias in host.names:
                self.ssh_panel.host_list.setCurrentRow(row)
                return

    def _on_nav_changed(self, row: int) -> None:
        if row < 0 or row >= len(_NAV):
            return
        self.stack.setCurrentIndex(row)
        label, desc = _NAV[row]
        self.header_title.setText(label)
        self.header_subtitle.setText(desc)

    def _any_dirty(self) -> bool:
        return (
            self.ssh_panel.is_dirty
            or self.aws_config_panel.is_dirty
            or self.aws_credentials_panel.is_dirty
        )

    def _window_title(self, *, dirty: bool | None = None) -> str:
        if dirty is None:
            dirty = self._any_dirty()
        title = f"{APP_NAME} {__version__}"
        if dirty:
            title += " *"
        return title

    def _update_chrome(self, *_args: object) -> None:
        dirty = self._any_dirty()
        self.setWindowTitle(self._window_title(dirty=dirty))
        self.unsaved_badge.setVisible(dirty)

    def save_all(self) -> bool:
        ok = True
        for panel in (self.ssh_panel, self.aws_config_panel, self.aws_credentials_panel):
            if panel.is_dirty and panel.save() is None:
                ok = False
        if ok and self._any_dirty():
            ok = False
        if ok:
            self.statusBar().showMessage("All changes saved", 4000)
        return ok

    def open_ssh_terminal(self) -> None:
        self.nav_list.setCurrentRow(0)
        self.stack.setCurrentIndex(0)
        self.ssh_panel.open_terminal_for_selection()

    def confirm_quit(self) -> bool:
        if not self._any_dirty():
            return True
        answer = QMessageBox.question(
            self,
            "Unsaved changes",
            "Save changes before quitting?",
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
        )
        if answer == QMessageBox.StandardButton.Save:
            return self.save_all()
        if answer == QMessageBox.StandardButton.Cancel:
            return False
        return True

    def closeEvent(self, event) -> None:  # noqa: N802
        if self._tray and self._tray.enabled and self._tray.handle_close(event):
            return
        if not self.confirm_quit():
            event.ignore()
            return
        event.accept()
