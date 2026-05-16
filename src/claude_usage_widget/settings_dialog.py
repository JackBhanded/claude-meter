"""Tiny ``QDialog`` to edit ``Settings``."""
from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QVBoxLayout,
)

from .settings import Settings


PLAN_CHOICES = [
    ("unknown",  "Don't know / unspecified"),
    ("pro",      "Claude Pro"),
    ("max_5x",   "Claude Max (5×)"),
    ("max_20x",  "Claude Max (20×)"),
    ("api_only", "Pay-as-you-go API only"),
]


class SettingsDialog(QDialog):
    def __init__(self, settings: Settings, on_save: Callable[[Settings], None], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Claude Meter — Settings")
        self.setMinimumWidth(380)
        self._settings = settings
        self._on_save = on_save

        root = QVBoxLayout(self)
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.refresh_spin = QSpinBox(self)
        self.refresh_spin.setRange(0, 60 * 60)
        self.refresh_spin.setSuffix(" s")
        self.refresh_spin.setSingleStep(60)
        self.refresh_spin.setSpecialValueText("Auto (adaptive, 5–20 min)")
        self.refresh_spin.setValue(settings.refresh_seconds)
        form.addRow("Refresh interval:", self.refresh_spin)

        self.plan_combo = QComboBox(self)
        for key, label in PLAN_CHOICES:
            self.plan_combo.addItem(label, key)
        idx = next(
            (i for i, (k, _) in enumerate(PLAN_CHOICES) if k == settings.plan), 0
        )
        self.plan_combo.setCurrentIndex(idx)
        form.addRow("Plan (for cost estimate):", self.plan_combo)

        self.api_key_edit = QLineEdit(self)
        self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_edit.setPlaceholderText(
            "(leave empty — uses Claude Code credentials)"
        )
        if settings.manual_api_key:
            self.api_key_edit.setText(settings.manual_api_key)
        form.addRow("Manual API key:", self.api_key_edit)

        self.notify_check = QCheckBox("Show toast when crossing 75% / 90% / 95%", self)
        self.notify_check.setChecked(settings.notifications_enabled)
        form.addRow("Notifications:", self.notify_check)

        self.fullscreen_check = QCheckBox("Hide when an app is fullscreen", self)
        self.fullscreen_check.setChecked(settings.hide_when_fullscreen)
        form.addRow("Auto-hide:", self.fullscreen_check)

        self.offset_right_spin = QSpinBox(self)
        self.offset_right_spin.setRange(0, 1000)
        self.offset_right_spin.setSuffix(" px")
        self.offset_right_spin.setValue(settings.pos_offset_right)
        form.addRow("Offset from system tray:", self.offset_right_spin)

        self.offset_bottom_spin = QSpinBox(self)
        self.offset_bottom_spin.setRange(0, 200)
        self.offset_bottom_spin.setSuffix(" px")
        self.offset_bottom_spin.setValue(settings.pos_offset_bottom)
        form.addRow("Offset from taskbar:", self.offset_bottom_spin)

        root.addLayout(form)

        note = QLabel(
            "Cost estimate is approximate. The Anthropic API doesn't expose "
            "exact token spend — we infer from utilization × plan caps."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color: #7a7e88; font-size: 11px;")
        root.addWidget(note)

        bb = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        bb.accepted.connect(self._save_and_close)
        bb.rejected.connect(self.reject)
        root.addWidget(bb)

    def _save_and_close(self) -> None:
        s = self._settings
        s.refresh_seconds = int(self.refresh_spin.value())
        s.plan = self.plan_combo.currentData()
        text = self.api_key_edit.text().strip()
        s.manual_api_key = text or None
        s.notifications_enabled = self.notify_check.isChecked()
        s.hide_when_fullscreen = self.fullscreen_check.isChecked()
        s.pos_offset_right = int(self.offset_right_spin.value())
        s.pos_offset_bottom = int(self.offset_bottom_spin.value())
        self._on_save(s)
        self.accept()
