"""System tray integration — run in the background with quick actions."""

from __future__ import annotations

from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QApplication, QMenu, QMessageBox, QSystemTrayIcon

from ssh_config_gui.config_io import HostEntry
from ssh_config_gui.theme import APP_NAME, make_app_icon
from ssh_config_gui.terminal import open_ssh_in_terminal


class TrayController:
    def __init__(self, window) -> None:
        self.window = window
        self._icon = make_app_icon()
        self._available = QSystemTrayIcon.isSystemTrayAvailable()
        self.tray: QSystemTrayIcon | None = None
        self._menu: QMenu | None = None

        if not self._available:
            return

        self.tray = QSystemTrayIcon(self._icon, window)
        self.tray.setToolTip(APP_NAME)
        self._menu = QMenu()
        self.tray.setContextMenu(self._menu)
        self.tray.activated.connect(self._on_activated)
        self.refresh_menu()
        self.tray.show()

        if not self.window.settings().value("tray_hint_shown"):
            self.tray.showMessage(
                APP_NAME,
                "Running in the system tray. Close hides the window; use Quit to exit.",
                QSystemTrayIcon.MessageIcon.Information,
                4000,
            )
            self.window.settings().setValue("tray_hint_shown", True)

    @property
    def enabled(self) -> bool:
        return self.tray is not None

    def refresh_menu(self) -> None:
        if not self._menu:
            return
        self._menu.clear()

        show_action = QAction("Show window", self._menu)
        show_action.triggered.connect(self.show_window)
        self._menu.addAction(show_action)

        self._menu.addSeparator()
        self._add_ssh_hosts_menu()
        self._menu.addSeparator()

        save_action = QAction("Save all", self._menu)
        save_action.triggered.connect(self.window.save_all)
        self._menu.addAction(save_action)

        self._menu.addSeparator()

        quit_action = QAction("Quit", self._menu)
        quit_action.triggered.connect(self.quit_application)
        self._menu.addAction(quit_action)

    def _add_ssh_hosts_menu(self) -> None:
        ssh_menu = self._menu.addMenu("SSH hosts")
        hosts = self.window.list_ssh_hosts()

        if not hosts:
            empty = ssh_menu.addAction("(No hosts configured)")
            empty.setEnabled(False)
            return

        for host in hosts:
            title = self._host_menu_title(host)
            host_menu = ssh_menu.addMenu(title)

            connect_action = QAction("Connect", host_menu)
            connect_action.triggered.connect(
                lambda checked=False, alias=host.label: self._connect_host(alias)
            )
            host_menu.addAction(connect_action)

            terminal_action = QAction("Open terminal", host_menu)
            terminal_action.triggered.connect(
                lambda checked=False, alias=host.label: self._connect_host(alias)
            )
            host_menu.addAction(terminal_action)

            show_action = QAction("Show in app", host_menu)
            show_action.triggered.connect(
                lambda checked=False, alias=host.label: self.window.show_ssh_host(alias)
            )
            host_menu.addAction(show_action)

    @staticmethod
    def _host_menu_title(host: HostEntry) -> str:
        hostname = host.get("HostName")
        if hostname:
            return f"{host.label}  ({hostname})"
        return host.label

    def _connect_host(self, alias: str) -> None:
        if self.window.ssh_panel.is_dirty:
            answer = QMessageBox.question(
                self.window,
                "Unsaved SSH config",
                "Save SSH config before connecting?\n"
                "The terminal uses the saved config file on disk.",
                QMessageBox.StandardButton.Save
                | QMessageBox.StandardButton.Ignore
                | QMessageBox.StandardButton.Cancel,
            )
            if answer == QMessageBox.StandardButton.Save:
                if self.window.ssh_panel.save() is None:
                    return
            elif answer == QMessageBox.StandardButton.Cancel:
                return

        try:
            open_ssh_in_terminal(alias, self.window.ssh_panel.config_path)
        except (OSError, ValueError, RuntimeError) as exc:
            QMessageBox.critical(self.window, "Could not open terminal", str(exc))

    def show_window(self) -> None:
        self.window.showNormal()
        self.window.raise_()
        self.window.activateWindow()

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self.show_window()

    def handle_close(self, event) -> bool:
        """Return True if the window should hide to tray instead of closing."""
        if not self.enabled:
            return False
        event.ignore()
        self.window.hide()
        self.tray.showMessage(
            APP_NAME,
            "Still running in the system tray.",
            QSystemTrayIcon.MessageIcon.Information,
            2000,
        )
        return True

    def quit_application(self) -> None:
        if not self.window.confirm_quit():
            return
        QApplication.quit()
