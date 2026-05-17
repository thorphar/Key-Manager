"""AWS config / credentials editor panel."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from ssh_config_gui.ui_helpers import content_card_with_form
from ssh_config_gui.aws_config_io import (
    AwsFileKind,
    AwsIniFile,
    AwsProfile,
    default_aws_config_path,
    default_aws_credentials_path,
    known_keys,
    load_aws_ini,
    save_aws_ini,
)

_CONFIG_FIELDS: tuple[tuple[str, str, bool], ...] = (
    ("region", "us-east-1", False),
    ("output", "json", False),
    ("role_arn", "arn:aws:iam::123456789012:role/MyRole", False),
    ("source_profile", "default", False),
    ("mfa_serial", "arn:aws:iam::123456789012:mfa/user", False),
    ("external_id", "", False),
    ("sso_start_url", "https://my-org.awsapps.com/start", False),
    ("sso_region", "us-east-1", False),
    ("sso_account_id", "123456789012", False),
    ("sso_role_name", "MyRole", False),
    ("credential_process", "", False),
)

_CREDENTIALS_FIELDS: tuple[tuple[str, str, bool], ...] = (
    ("aws_access_key_id", "AKIA...", False),
    ("aws_secret_access_key", "", True),
    ("aws_session_token", "", True),
)


class AwsFilePanel(QWidget):
    dirty_changed = Signal(bool)

    def __init__(
        self,
        kind: AwsFileKind,
        file_path: Path | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.kind = kind
        self.file_path = file_path or (
            default_aws_config_path() if kind == "config" else default_aws_credentials_path()
        )
        self.data = AwsIniFile()
        self._loading_form = False
        self._dirty = False
        self._field_defs = _CONFIG_FIELDS if kind == "config" else _CREDENTIALS_FIELDS
        self._known = set(known_keys(kind))

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        path_row = QHBoxLayout()
        path_lbl = QLabel("File")
        path_lbl.setObjectName("pathLabel")
        path_row.addWidget(path_lbl)
        self.path_edit = QLineEdit()
        self.path_edit.setReadOnly(True)
        path_row.addWidget(self.path_edit, stretch=1)
        browse_btn = QPushButton("Open…")
        browse_btn.clicked.connect(self._choose_file)
        path_row.addWidget(browse_btn)
        root.addLayout(path_row)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.addWidget(QLabel("Profiles"))
        self.profile_list = QListWidget()
        self.profile_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.profile_list.currentRowChanged.connect(self._on_profile_selected)
        left_layout.addWidget(self.profile_list)

        btn_row = QHBoxLayout()
        add_btn = QPushButton("Add profile")
        add_btn.clicked.connect(self._add_profile)
        remove_btn = QPushButton("Remove")
        remove_btn.clicked.connect(self._remove_profile)
        btn_row.addWidget(add_btn)
        btn_row.addWidget(remove_btn)
        left_layout.addLayout(btn_row)
        splitter.addWidget(left)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        form_group, form, _scroll = content_card_with_form("Profile settings")

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("my-profile")
        self.name_edit.textChanged.connect(self._on_form_edited)
        form.add_row("Profile name", self.name_edit)

        self._edits: dict[str, QLineEdit] = {}
        for key, placeholder, secret in self._field_defs:
            if key == "output" and self.kind == "config":
                combo = QComboBox()
                combo.setEditable(True)
                combo.addItems(["json", "text", "table", "yaml"])
                combo.currentTextChanged.connect(self._on_form_edited)
                self._edits[key] = combo  # type: ignore[assignment]
                form.add_row(key, combo)
                continue

            edit = QLineEdit()
            edit.setPlaceholderText(placeholder)
            if secret:
                edit.setEchoMode(QLineEdit.EchoMode.Password)
            edit.textChanged.connect(self._on_form_edited)
            self._edits[key] = edit
            form.add_row(key, edit)

        right_layout.addWidget(form_group, stretch=1)

        if self.kind == "credentials":
            hint = QLabel("Secrets are hidden. They are only changed when you type in the field.")
            hint.setObjectName("hintLabel")
            hint.setWordWrap(True)
            right_layout.addWidget(hint)

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
                f"You have unsaved AWS {self.kind} edits. Reload from disk anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return None

        try:
            self.data = load_aws_ini(self.file_path, self.kind)
        except OSError as exc:
            QMessageBox.critical(self, f"Could not load AWS {self.kind}", str(exc))
            return None

        self.path_edit.setText(str(self.file_path))
        self._refresh_profile_list()
        self._set_dirty(False)
        label = "config" if self.kind == "config" else "credentials"
        extra = len(self.data.other_sections)
        extra_msg = f", {extra} other section(s) preserved" if extra else ""
        return f"AWS {label}: loaded {len(self.data.profiles)} profile(s){extra_msg}"

    def save(self) -> str | None:
        if not self._apply_form_to_current_profile(silent=False):
            return None
        try:
            save_aws_ini(self.data, self.file_path, self.kind, backup=True)
        except OSError as exc:
            QMessageBox.critical(self, f"Could not save AWS {self.kind}", str(exc))
            return None
        self._set_dirty(False)
        backup = self.file_path.with_suffix(self.file_path.suffix + ".bak")
        label = "config" if self.kind == "config" else "credentials"
        return f"AWS {label}: saved (backup {backup.name})"

    def save_if_dirty(self) -> bool:
        if not self._dirty:
            return True
        return self.save() is not None

    def _choose_file(self) -> None:
        start = str(self.file_path.parent) if self.file_path.parent.exists() else str(Path.home())
        title = "Open AWS config" if self.kind == "config" else "Open AWS credentials"
        path, _ = QFileDialog.getOpenFileName(
            self,
            title,
            start,
            "AWS files (config credentials);;All files (*)",
        )
        if not path:
            return
        self.file_path = Path(path)
        self.reload()

    def _refresh_profile_list(self) -> None:
        row = self.profile_list.currentRow()
        self.profile_list.blockSignals(True)
        self.profile_list.clear()
        for profile in self.data.profiles:
            subtitle = profile.get("region") if self.kind == "config" else profile.get("aws_access_key_id")
            if subtitle and self.kind == "credentials":
                subtitle = subtitle[:8] + "…" if len(subtitle) > 8 else subtitle
            text = profile.name if not subtitle else f"{profile.name}  —  {subtitle}"
            self.profile_list.addItem(QListWidgetItem(text))
        self.profile_list.blockSignals(False)

        if self.data.profiles:
            pick = row if 0 <= row < len(self.data.profiles) else 0
            self.profile_list.setCurrentRow(pick)
        else:
            self._clear_form()

    def _current_profile(self) -> AwsProfile | None:
        row = self.profile_list.currentRow()
        if row < 0 or row >= len(self.data.profiles):
            return None
        return self.data.profiles[row]

    def _on_profile_selected(self, row: int) -> None:
        if row < 0:
            self._clear_form()
            return
        self._load_form(self.data.profiles[row])

    def _clear_form(self) -> None:
        self._loading_form = True
        self.name_edit.clear()
        for key, widget in self._edits.items():
            if isinstance(widget, QComboBox):
                widget.setCurrentIndex(0)
                widget.setCurrentText("")
            else:
                widget.clear()
        self._loading_form = False

    def _load_form(self, profile: AwsProfile) -> None:
        self._loading_form = True
        self.name_edit.setText(profile.name)
        for key, widget in self._edits.items():
            value = profile.get(key)
            if isinstance(widget, QComboBox):
                widget.setCurrentText(value)
            else:
                widget.setText(value)
        self._loading_form = False

    def _widget_value(self, key: str) -> str:
        widget = self._edits[key]
        if isinstance(widget, QComboBox):
            return widget.currentText().strip()
        return widget.text().strip()

    def _on_form_edited(self) -> None:
        if self._loading_form:
            return
        self._apply_form_to_current_profile(silent=True)
        self._set_dirty(True)

    def _apply_form_to_current_profile(self, *, silent: bool) -> bool:
        profile = self._current_profile()
        if profile is None:
            if not silent:
                QMessageBox.information(self, "No profile selected", "Add or select a profile first.")
            return False

        new_name = self.name_edit.text().strip()
        if not new_name:
            if not silent:
                QMessageBox.warning(self, "Missing profile name", "Profile name is required.")
            return False

        other_names = {p.name for i, p in enumerate(self.data.profiles) if i != self.profile_list.currentRow()}
        if new_name in other_names:
            if not silent:
                QMessageBox.warning(self, "Duplicate profile", f"Profile '{new_name}' already exists.")
            return False

        profile.name = new_name

        for key in self._known:
            profile.set(key, self._widget_value(key))

        row = self.profile_list.currentRow()
        if row >= 0:
            subtitle = profile.get("region") if self.kind == "config" else profile.get("aws_access_key_id")
            if subtitle and self.kind == "credentials":
                subtitle = subtitle[:8] + "…" if len(subtitle) > 8 else subtitle
            text = profile.name if not subtitle else f"{profile.name}  —  {subtitle}"
            self.profile_list.item(row).setText(text)

        return True

    def _add_profile(self) -> None:
        base = "new-profile"
        names = {p.name for p in self.data.profiles}
        candidate = base
        n = 2
        while candidate in names:
            candidate = f"{base}-{n}"
            n += 1

        self.data.profiles.append(AwsProfile(name=candidate))
        self._refresh_profile_list()
        self.profile_list.setCurrentRow(len(self.data.profiles) - 1)
        self.name_edit.setFocus()
        self.name_edit.selectAll()
        self._set_dirty(True)

    def _remove_profile(self) -> None:
        row = self.profile_list.currentRow()
        if row < 0:
            return
        name = self.data.profiles[row].name
        answer = QMessageBox.question(
            self,
            "Remove profile",
            f"Remove profile '{name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        del self.data.profiles[row]
        self._refresh_profile_list()
        self._set_dirty(True)
