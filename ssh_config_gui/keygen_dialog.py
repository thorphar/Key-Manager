"""Dialog for generating a new SSH key pair."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
)

from ssh_config_gui.ssh_keys import generate_key_pair


class KeygenDialog(QDialog):
    def __init__(self, parent=None, *, default_name: str = "id_ed25519") -> None:
        super().__init__(parent)
        self.setWindowTitle("Generate SSH key pair")
        self.generated_name: str | None = None

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.name_edit = QLineEdit(default_name)
        self.name_edit.setPlaceholderText("id_ed25519")
        form.addRow("Key file name", self.name_edit)

        self.type_combo = QComboBox()
        self.type_combo.addItems(["ed25519", "rsa"])
        form.addRow("Key type", self.type_combo)

        self.comment_edit = QLineEdit()
        self.comment_edit.setPlaceholderText("you@laptop")
        form.addRow("Comment", self.comment_edit)

        self.passphrase_edit = QLineEdit()
        self.passphrase_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.passphrase_edit.setPlaceholderText("(optional)")
        form.addRow("Passphrase", self.passphrase_edit)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_accept(self) -> None:
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Missing name", "Enter a key file name.")
            return
        try:
            generate_key_pair(
                name,
                key_type=self.type_combo.currentText(),
                comment=self.comment_edit.text().strip(),
                passphrase=self.passphrase_edit.text(),
            )
        except FileExistsError as exc:
            answer = QMessageBox.question(
                self,
                "Key exists",
                f"{exc}\n\nOverwrite?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
            try:
                generate_key_pair(
                    name,
                    key_type=self.type_combo.currentText(),
                    comment=self.comment_edit.text().strip(),
                    passphrase=self.passphrase_edit.text(),
                    force=True,
                )
            except (OSError, ValueError, RuntimeError) as exc2:
                QMessageBox.critical(self, "Could not generate key", str(exc2))
                return
        except (OSError, ValueError, RuntimeError) as exc:
            QMessageBox.critical(self, "Could not generate key", str(exc))
            return

        self.generated_name = name
        self.accept()
