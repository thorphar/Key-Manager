"""Shared Qt layout helpers."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

FIELD_MIN_HEIGHT = 40
FORM_ROW_GAP = 14


def make_form_label(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("formLabel")
    label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    label.setAutoFillBackground(False)
    label.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred)
    return label


def prepare_field(widget: QWidget, *, min_height: int = FIELD_MIN_HEIGHT) -> QWidget:
    widget.setMinimumHeight(min_height)
    widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    return widget


class LabeledForm:
    """Two-column label + field layout (replaces QFormLayout for consistent spacing)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        self.container = QWidget(parent)
        self.container.setObjectName("formBody")
        self.grid = QGridLayout(self.container)
        self.grid.setContentsMargins(4, 4, 4, 8)
        self.grid.setHorizontalSpacing(18)
        self.grid.setVerticalSpacing(FORM_ROW_GAP)
        self.grid.setColumnStretch(1, 1)
        self._row = 0

    def add_row(self, label_text: str, field: QWidget, *, min_height: int = FIELD_MIN_HEIGHT) -> None:
        label = make_form_label(label_text)
        prepare_field(field, min_height=min_height)
        self.grid.addWidget(label, self._row, 0)
        self.grid.addWidget(field, self._row, 1)
        self._row += 1

    def add_widget_row(self, label_text: str, content: QWidget) -> None:
        label = make_form_label(label_text)
        self.grid.addWidget(label, self._row, 0, Qt.AlignmentFlag.AlignTop)
        self.grid.addWidget(content, self._row, 1)
        self._row += 1

    def add_checkbox_row(self, text: str, checkbox: QWidget) -> None:
        checkbox.setMinimumHeight(32)
        self.grid.addWidget(checkbox, self._row, 0, 1, 2)
        self._row += 1


def content_card_with_form(title: str) -> tuple[QGroupBox, LabeledForm, QScrollArea]:
    group = QGroupBox(title)
    group.setObjectName("contentCard")
    layout = QVBoxLayout(group)
    layout.setContentsMargins(12, 22, 12, 12)

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

    form = LabeledForm()
    scroll.setWidget(form.container)
    layout.addWidget(scroll)
    return group, form, scroll


def action_button_row(*buttons: QPushButton) -> QHBoxLayout:
    row = QHBoxLayout()
    row.setSpacing(10)
    row.setContentsMargins(0, 6, 0, 0)
    for button in buttons:
        button.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        button.setMinimumHeight(38)
        row.addWidget(button)
    row.addStretch()
    return row
