"""SSH config editor panel."""

from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QSplitter,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ssh_config_gui.config_io import HostEntry, SshConfigFile, default_config_path, load_config, save_config
from ssh_config_gui.theme import make_terminal_icon
from ssh_config_gui.ui_helpers import action_button_row, content_card_with_form, prepare_field
from ssh_config_gui.key_swap_dialog import KeySwapDialog
from ssh_config_gui.keygen_dialog import KeygenDialog
from ssh_config_gui.ssh_askpass import prompt_password_gui
from ssh_config_gui.ssh_keys import (
    SshTarget,
    apply_public_key,
    default_ssh_dir,
    find_key_pair,
    list_key_pairs,
)
from ssh_config_gui.terminal import open_ssh_in_terminal


class _HostRowWidget(QWidget):
    """One host row: name label + terminal action."""

    def __init__(
        self,
        panel: "SshConfigPanel",
        row: int,
        host: HostEntry,
        icon,
    ) -> None:
        super().__init__()
        self._panel = panel
        self._row = row
        self._label = QLabel(panel._host_list_label(host))
        self._label.setObjectName("hostRowLabel")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 2, 4, 2)
        layout.setSpacing(6)
        layout.addWidget(self._label, stretch=1)

        terminal_btn = QToolButton()
        terminal_btn.setObjectName("hostTerminalButton")
        terminal_btn.setIcon(icon)
        terminal_btn.setToolTip(f"Open terminal — {host.label}")
        terminal_btn.setAutoRaise(True)
        terminal_btn.clicked.connect(lambda: panel.open_terminal_for_host(host))
        layout.addWidget(terminal_btn)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        child = self.childAt(event.pos())
        if child is None or child == self._label:
            self._panel.host_list.setCurrentRow(self._row)
        super().mousePressEvent(event)

    def update_label(self, host: HostEntry) -> None:
        self._label.setText(self._panel._host_list_label(host))


class SshConfigPanel(QWidget):
    dirty_changed = Signal(bool)
    hosts_changed = Signal()

    def __init__(self, config_path: Path | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.config_path = config_path or default_config_path()
        self.config = SshConfigFile()
        self._loading_form = False
        self._dirty = False

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        path_row = QHBoxLayout()
        path_lbl = QLabel("Config file")
        path_lbl.setObjectName("pathLabel")
        path_row.addWidget(path_lbl)
        self.path_edit = QLineEdit()
        self.path_edit.setReadOnly(True)
        path_row.addWidget(self.path_edit, stretch=1)
        browse_config_btn = QPushButton("Open…")
        browse_config_btn.clicked.connect(self._choose_config_file)
        path_row.addWidget(browse_config_btn)
        root.addLayout(path_row)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.addWidget(QLabel("Hosts"))
        self.host_list = QListWidget()
        self.host_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.host_list.currentRowChanged.connect(self._on_host_selected)
        left_layout.addWidget(self.host_list)

        host_btn_row = QHBoxLayout()
        add_btn = QPushButton("Add host")
        add_btn.clicked.connect(self._add_host)
        remove_btn = QPushButton("Remove")
        remove_btn.clicked.connect(self._remove_host)
        host_btn_row.addWidget(add_btn)
        host_btn_row.addWidget(remove_btn)
        left_layout.addLayout(host_btn_row)

        self._terminal_icon = make_terminal_icon()
        splitter.addWidget(left)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        form_group, form, _scroll = content_card_with_form("Host settings")

        self.alias_edit = QLineEdit()
        self.alias_edit.setPlaceholderText("my-server  (space-separated for multiple aliases)")
        self.alias_edit.textChanged.connect(self._on_form_edited)
        form.add_row("Host alias", self.alias_edit)

        self.hostname_edit = QLineEdit()
        self.hostname_edit.setPlaceholderText("192.168.1.10 or example.com")
        self.hostname_edit.textChanged.connect(self._on_form_edited)
        form.add_row("HostName", self.hostname_edit)

        self.user_edit = QLineEdit()
        self.user_edit.setPlaceholderText("ubuntu")
        self.user_edit.textChanged.connect(self._on_form_edited)
        form.add_row("User", self.user_edit)

        self.port_spin = QSpinBox()
        self.port_spin.setRange(0, 65535)
        self.port_spin.setSpecialValueText("(default)")
        self.port_spin.valueChanged.connect(self._on_form_edited)
        form.add_row("Port", self.port_spin)

        key_field = QWidget()
        key_field_layout = QVBoxLayout(key_field)
        key_field_layout.setContentsMargins(0, 0, 0, 0)
        key_field_layout.setSpacing(12)
        self.key_combo = QComboBox()
        self.key_combo.setMinimumWidth(200)
        self.key_combo.currentIndexChanged.connect(self._on_key_combo_changed)
        key_field_layout.addWidget(self.key_combo)
        gen_key_btn = QPushButton("Generate…")
        gen_key_btn.clicked.connect(self._generate_key)
        apply_key_btn = QPushButton("Copy to host")
        apply_key_btn.setToolTip("Install the selected public key in the remote authorized_keys file")
        apply_key_btn.clicked.connect(self._apply_key_to_host)
        swap_key_btn = QPushButton("Swap keys…")
        swap_key_btn.setToolTip(
            "Install a new key on the server, remove the old one from authorized_keys, "
            "and update this host's IdentityFile"
        )
        swap_key_btn.clicked.connect(self._swap_keys)
        key_field_layout.addLayout(action_button_row(gen_key_btn, apply_key_btn, swap_key_btn))
        form.add_widget_row("Key pair", key_field)

        identity_field = QWidget()
        identity_row = QHBoxLayout(identity_field)
        identity_row.setContentsMargins(0, 0, 0, 0)
        identity_row.setSpacing(8)
        self.identity_edit = QLineEdit()
        self.identity_edit.setPlaceholderText(r"C:\Users\you\.ssh\id_ed25519")
        self.identity_edit.textChanged.connect(self._on_identity_edited)
        prepare_field(self.identity_edit)
        identity_row.addWidget(self.identity_edit, stretch=1)
        browse_key_btn = QPushButton("Browse…")
        browse_key_btn.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        browse_key_btn.setMinimumHeight(38)
        browse_key_btn.clicked.connect(self._browse_identity_file)
        identity_row.addWidget(browse_key_btn)
        form.add_widget_row("IdentityFile", identity_field)

        self.identities_only = QCheckBox("Use only this key (IdentitiesOnly yes)")
        self.identities_only.stateChanged.connect(self._on_form_edited)
        form.add_checkbox_row("", self.identities_only)

        self.proxy_edit = QLineEdit()
        self.proxy_edit.setPlaceholderText("bastion or user@bastion")
        self.proxy_edit.textChanged.connect(self._on_form_edited)
        form.add_row("ProxyJump", self.proxy_edit)

        self.forward_agent = QCheckBox("ForwardAgent yes")
        self.forward_agent.stateChanged.connect(self._on_form_edited)
        form.add_checkbox_row("", self.forward_agent)

        right_layout.addWidget(form_group, stretch=1)
        splitter.addWidget(right)
        splitter.setStretchFactor(1, 1)
        root.addWidget(splitter, stretch=1)

        action_row = QHBoxLayout()
        reload_btn = QPushButton("Reload")
        reload_btn.setObjectName("ghostButton")
        reload_btn.clicked.connect(self.reload)
        save_btn = QPushButton("Save")
        save_btn.setObjectName("primaryButton")
        save_btn.setDefault(True)
        save_btn.clicked.connect(self.save)
        action_row.addStretch()
        action_row.addWidget(reload_btn)
        action_row.addWidget(save_btn)
        root.addLayout(action_row)

        self._refresh_key_combo()
        self.reload()

    @property
    def is_dirty(self) -> bool:
        return self._dirty

    def _set_dirty(self, dirty: bool) -> None:
        if self._dirty != dirty:
            self._dirty = dirty
            self.dirty_changed.emit(dirty)

    def reload(self) -> str | None:
        if self._dirty:
            answer = QMessageBox.question(
                self,
                "Discard changes?",
                "You have unsaved SSH edits. Reload from disk anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return None

        try:
            self.config = load_config(self.config_path)
        except OSError as exc:
            QMessageBox.critical(self, "Could not load SSH config", str(exc))
            return None

        self.path_edit.setText(str(self.config_path))
        self._refresh_host_list()
        self._set_dirty(False)
        self.hosts_changed.emit()
        return f"SSH: loaded {len(self.config.hosts)} host(s)"

    def save(self) -> str | None:
        if not self._apply_form_to_current_host(silent=False):
            return None
        try:
            save_config(self.config, self.config_path, backup=True)
        except OSError as exc:
            QMessageBox.critical(self, "Could not save SSH config", str(exc))
            return None
        self._set_dirty(False)
        self.hosts_changed.emit()
        backup = self.config_path.with_suffix(self.config_path.suffix + ".bak")
        return f"SSH: saved (backup {backup.name})"

    def save_if_dirty(self) -> bool:
        if not self._dirty:
            return True
        result = self.save()
        return result is not None

    def _choose_config_file(self) -> None:
        start = str(self.config_path.parent) if self.config_path.parent.exists() else str(Path.home())
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open SSH config",
            start,
            "SSH config (config);;All files (*)",
        )
        if not path:
            return
        self.config_path = Path(path)
        self.reload()

    def _browse_identity_file(self) -> None:
        ssh_dir = default_ssh_dir()
        start = self.identity_edit.text().strip() or str(ssh_dir)
        if start.startswith("~"):
            start = os.path.expanduser(start)
        start_dir = str(Path(start).parent) if Path(start).parent.exists() else str(ssh_dir)

        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select private key",
            start_dir,
            "SSH keys (id_* *key*);;All files (*)",
        )
        if path:
            self.identity_edit.setText(path)
            self._sync_key_combo_to_identity()

    def _refresh_key_combo(self) -> None:
        current = self.identity_edit.text().strip()
        self.key_combo.blockSignals(True)
        self.key_combo.clear()
        self.key_combo.addItem("(Select a key…)", "")
        for pair in list_key_pairs():
            self.key_combo.addItem(pair.label, str(pair.private))
        self.key_combo.blockSignals(False)
        if current:
            self._sync_key_combo_to_identity()

    def _sync_key_combo_to_identity(self) -> None:
        identity = self.identity_edit.text().strip()
        self.key_combo.blockSignals(True)
        if not identity:
            self.key_combo.setCurrentIndex(0)
        else:
            expanded = os.path.expanduser(identity)
            index = self.key_combo.findData(expanded)
            if index < 0:
                index = self.key_combo.findData(str(Path(expanded)))
            self.key_combo.setCurrentIndex(index if index >= 0 else 0)
        self.key_combo.blockSignals(False)

    def _on_key_combo_changed(self, index: int) -> None:
        if self._loading_form or index <= 0:
            return
        path = self.key_combo.itemData(index)
        if path:
            self._loading_form = True
            self.identity_edit.setText(path)
            self._loading_form = False
            self._on_form_edited()

    def _on_identity_edited(self) -> None:
        if self._loading_form:
            return
        self._sync_key_combo_to_identity()
        self._on_form_edited()

    def _selected_key_pair(self):
        index = self.key_combo.currentIndex()
        if index <= 0:
            identity = self.identity_edit.text().strip()
            if not identity:
                return None
            return find_key_pair(identity)
        path = self.key_combo.itemData(index)
        return find_key_pair(path) if path else None

    def _generate_key(self) -> None:
        dialog = KeygenDialog(self)
        if dialog.exec() != KeygenDialog.DialogCode.Accepted or not dialog.generated_name:
            return
        self._refresh_key_combo()
        private = default_ssh_dir() / dialog.generated_name
        self._loading_form = True
        self.identity_edit.setText(str(private))
        self._loading_form = False
        self._sync_key_combo_to_identity()
        self._on_form_edited()
        QMessageBox.information(
            self,
            "Key generated",
            f"Created:\n  {private}\n  {private}.pub",
        )

    def _apply_key_to_host(self) -> None:
        if not self._apply_form_to_current_host(silent=False):
            return

        pair = self._selected_key_pair()
        if pair is None:
            QMessageBox.warning(
                self,
                "No key selected",
                "Select a key pair from the dropdown or choose a private key file with a .pub sibling.",
            )
            return

        host = self._current_host()
        if host is None:
            return

        hostname = host.get("HostName")
        user = host.get("User")
        if not hostname or not user:
            QMessageBox.warning(
                self,
                "Missing connection details",
                "Set HostName and User for this host before copying a key.",
            )
            return

        port = self.port_spin.value()
        proxy = host.get("ProxyJump")

        answer = QMessageBox.question(
            self,
            "Copy public key to host",
            f"Install {pair.public.name} on {user}@{hostname}?\n\n"
            "If key login is not set up yet, you will be asked for the remote password.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        try:
            message = apply_public_key(
                pair.public,
                hostname=hostname,
                user=user,
                port=port if port > 0 else None,
                login_identity=pair.private,
                proxy_jump=proxy or None,
                password_prompt=lambda target: prompt_password_gui(self, target),
            )
        except (OSError, ValueError, RuntimeError) as exc:
            QMessageBox.critical(self, "Could not copy key", str(exc))
            return

        self.identity_edit.setText(str(pair.private))
        host.set("IdentityFile", str(pair.private))
        self._set_dirty(True)
        QMessageBox.information(self, "Key installed", message)

    def _swap_keys(self) -> None:
        if not self._apply_form_to_current_host(silent=False):
            return

        host = self._current_host()
        if host is None:
            QMessageBox.information(self, "No host selected", "Select a host first.")
            return

        hostname = host.get("HostName")
        user = host.get("User")
        if not hostname or not user:
            QMessageBox.warning(
                self,
                "Missing connection details",
                "Set HostName and User before swapping keys.",
            )
            return

        port = self.port_spin.value()
        target = SshTarget(
            hostname=hostname,
            user=user,
            port=port if port > 0 else None,
            proxy_jump=host.get("ProxyJump") or None,
        )
        current_key = self._selected_key_pair()

        dialog = KeySwapDialog(
            self,
            target=target,
            current_key=current_key,
            password_prompt=lambda t: prompt_password_gui(self, t),
        )
        if dialog.exec() != KeySwapDialog.DialogCode.Accepted or dialog.new_key is None:
            return

        self.identity_edit.setText(str(dialog.new_key.private))
        host.set("IdentityFile", str(dialog.new_key.private))
        if not self.identities_only.isChecked():
            self.identities_only.setChecked(True)
            host.set("IdentitiesOnly", "yes")
        self._sync_key_combo_to_identity()
        self._set_dirty(True)
        QMessageBox.information(self, "Keys swapped", dialog.result_message or "Done.")

    def open_terminal_for_selection(self) -> None:
        host = self._current_host()
        if host is None or not host.names:
            QMessageBox.information(self, "No host selected", "Select a host to connect to.")
            return
        self.open_terminal_for_host(host)

    def open_terminal_for_host(self, host: HostEntry) -> None:
        if not self._apply_form_to_current_host(silent=True):
            return

        if self._dirty:
            answer = QMessageBox.question(
                self,
                "Unsaved SSH config",
                "Save SSH config before opening the terminal?\n"
                "The terminal uses the saved config file on disk.",
                QMessageBox.StandardButton.Save
                | QMessageBox.StandardButton.Ignore
                | QMessageBox.StandardButton.Cancel,
            )
            if answer == QMessageBox.StandardButton.Save:
                if self.save() is None:
                    return
            elif answer == QMessageBox.StandardButton.Cancel:
                return

        alias = host.names[0]
        try:
            open_ssh_in_terminal(alias, self.config_path)
        except (OSError, ValueError, RuntimeError) as exc:
            QMessageBox.critical(self, "Could not open terminal", str(exc))

    def _host_list_label(self, host: HostEntry) -> str:
        subtitle = host.get("HostName")
        return host.label if not subtitle else f"{host.label}  —  {subtitle}"

    def _refresh_host_list(self) -> None:
        row = self.host_list.currentRow()
        self.host_list.blockSignals(True)
        self.host_list.clear()
        for index, host in enumerate(self.config.hosts):
            item = QListWidgetItem()
            row_widget = _HostRowWidget(self, index, host, self._terminal_icon)
            item.setSizeHint(row_widget.sizeHint())
            self.host_list.addItem(item)
            self.host_list.setItemWidget(item, row_widget)
        self.host_list.blockSignals(False)

        if self.config.hosts:
            pick = row if 0 <= row < len(self.config.hosts) else 0
            self.host_list.setCurrentRow(pick)
        else:
            self._clear_form()

    def _current_host(self) -> HostEntry | None:
        row = self.host_list.currentRow()
        if row < 0 or row >= len(self.config.hosts):
            return None
        return self.config.hosts[row]

    def _on_host_selected(self, row: int) -> None:
        if row < 0:
            self._clear_form()
            return
        self._load_form(self.config.hosts[row])

    def _clear_form(self) -> None:
        self._loading_form = True
        self.alias_edit.clear()
        self.hostname_edit.clear()
        self.user_edit.clear()
        self.port_spin.setValue(0)
        self.identity_edit.clear()
        self._sync_key_combo_to_identity()
        self.identities_only.setChecked(False)
        self.proxy_edit.clear()
        self.forward_agent.setChecked(False)
        self._loading_form = False

    def _load_form(self, host: HostEntry) -> None:
        self._loading_form = True
        self.alias_edit.setText(" ".join(host.names))
        self.hostname_edit.setText(host.get("HostName"))
        self.user_edit.setText(host.get("User"))
        port = host.get("Port")
        self.port_spin.setValue(int(port) if port.isdigit() else 0)
        identity = host.get("IdentityFile")
        self.identity_edit.setText(os.path.expanduser(identity) if identity else "")
        self._sync_key_combo_to_identity()
        self.identities_only.setChecked(host.get("IdentitiesOnly").lower() == "yes")
        self.proxy_edit.setText(host.get("ProxyJump"))
        self.forward_agent.setChecked(host.get("ForwardAgent").lower() == "yes")
        self._loading_form = False

    def _on_form_edited(self) -> None:
        if self._loading_form:
            return
        self._apply_form_to_current_host(silent=True)
        self._set_dirty(True)

    def _apply_form_to_current_host(self, *, silent: bool) -> bool:
        host = self._current_host()
        if host is None:
            if not silent:
                QMessageBox.information(self, "No host selected", "Add or select a host first.")
            return False

        alias = self.alias_edit.text().strip()
        names = [part for part in alias.split() if part]
        if not names:
            if not silent:
                QMessageBox.warning(self, "Missing alias", "Host alias is required (the name you ssh to).")
            return False

        host.names = names
        host.set("HostName", self.hostname_edit.text())
        host.set("User", self.user_edit.text())

        port = self.port_spin.value()
        host.set("Port", str(port) if port > 0 else "")

        identity = self.identity_edit.text().strip()
        host.set("IdentityFile", identity)

        if self.identities_only.isChecked():
            host.set("IdentitiesOnly", "yes")
        else:
            host.set("IdentitiesOnly", "")

        host.set("ProxyJump", self.proxy_edit.text())

        if self.forward_agent.isChecked():
            host.set("ForwardAgent", "yes")
        else:
            host.set("ForwardAgent", "")

        row = self.host_list.currentRow()
        if row >= 0:
            item = self.host_list.item(row)
            if item is not None:
                widget = self.host_list.itemWidget(item)
                if isinstance(widget, _HostRowWidget):
                    widget.update_label(host)

        return True

    def _add_host(self) -> None:
        base = "new-host"
        names = {h.names[0] for h in self.config.hosts if h.names}
        candidate = base
        n = 2
        while candidate in names:
            candidate = f"{base}-{n}"
            n += 1

        entry = HostEntry(names=[candidate], options={"HostName": [""]})
        self.config.hosts.append(entry)
        self._refresh_host_list()
        self.host_list.setCurrentRow(len(self.config.hosts) - 1)
        self.alias_edit.setFocus()
        self.alias_edit.selectAll()
        self._set_dirty(True)
        self.hosts_changed.emit()

    def _remove_host(self) -> None:
        row = self.host_list.currentRow()
        if row < 0:
            return
        name = self.config.hosts[row].label
        answer = QMessageBox.question(
            self,
            "Remove host",
            f"Remove host block '{name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        del self.config.hosts[row]
        self._refresh_host_list()
        self._set_dirty(True)
        self.hosts_changed.emit()
