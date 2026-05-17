"""Dialog to swap SSH keys on a remote host (rotate authorized_keys + local config)."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QMessageBox,
    QVBoxLayout,
)

from ssh_config_gui.ssh_keys import KeyPair, SshTarget, list_key_pairs, swap_host_keys


class KeySwapDialog(QDialog):
    def __init__(
        self,
        parent,
        *,
        target: SshTarget,
        current_key: KeyPair | None,
        password_prompt,
    ) -> None:
        super().__init__(parent)
        self.target = target
        self._password_prompt = password_prompt
        self.result_message: str | None = None
        self.new_key: KeyPair | None = None

        self.setWindowTitle("Swap SSH keys")
        layout = QVBoxLayout(self)

        layout.addWidget(
            QLabel(
                f"Rotate keys on <b>{target.label}</b>.<br>"
                "The new key is installed first, then the old key is removed from "
                "<code>authorized_keys</code> so you are not locked out."
            )
        )

        form = QFormLayout()
        self.old_combo = QComboBox()
        self.new_combo = QComboBox()
        self._populate_keys(current_key)
        form.addRow("Current key", self.old_combo)
        form.addRow("New key", self.new_combo)
        layout.addLayout(form)

        self.remove_old = QCheckBox("Remove old public key from server")
        self.remove_old.setChecked(True)
        layout.addWidget(self.remove_old)

        self.verify_new = QCheckBox("Verify login with new key before finishing")
        self.verify_new.setChecked(True)
        layout.addWidget(self.verify_new)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _populate_keys(self, current_key: KeyPair | None) -> None:
        pairs = list_key_pairs()
        self.old_combo.addItem("(none / password login only)", None)
        self.new_combo.addItem("(Select new key…)", None)

        for pair in pairs:
            self.old_combo.addItem(pair.label, pair)
            self.new_combo.addItem(pair.label, pair)

        if current_key:
            idx = self.old_combo.findData(current_key)
            if idx >= 0:
                self.old_combo.setCurrentIndex(idx)

        for i in range(1, self.new_combo.count()):
            candidate = self.new_combo.itemData(i)
            if candidate is not current_key:
                self.new_combo.setCurrentIndex(i)
                break

    def _selected_pair(self, combo: QComboBox) -> KeyPair | None:
        data = combo.currentData()
        return data if isinstance(data, KeyPair) else None

    def _on_accept(self) -> None:
        old_key = self._selected_pair(self.old_combo)
        new_key = self._selected_pair(self.new_combo)
        if new_key is None:
            QMessageBox.warning(self, "Select new key", "Choose the key to switch to.")
            return
        if old_key and old_key.private.resolve() == new_key.private.resolve():
            QMessageBox.warning(self, "Same key", "Pick a different key for the swap.")
            return

        answer = QMessageBox.question(
            self,
            "Confirm key swap",
            f"Swap keys on {self.target.label}?\n\n"
            f"  Current: {old_key.name if old_key else '(none)'}\n"
            f"  New:     {new_key.name}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        try:
            self.result_message = swap_host_keys(
                target=self.target,
                new_key=new_key,
                old_key=old_key,
                login_identity=old_key.private if old_key else None,
                remove_old_from_server=self.remove_old.isChecked(),
                verify_new_key=self.verify_new.isChecked(),
                password_prompt=self._password_prompt,
            )
        except (OSError, ValueError, RuntimeError) as exc:
            QMessageBox.critical(self, "Key swap failed", str(exc))
            return

        self.new_key = new_key
        self.accept()
