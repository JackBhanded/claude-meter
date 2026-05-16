"""System tray icon — the percentage IS the icon, color-coded.

The icon is a small rounded square in the utilization color with the
percentage painted on top in white. At 16-20 px there isn't room for the
Claude asterisk *and* a readable number, so we prioritise the number — the
asterisk lives in the pinned widget and tooltip instead.
"""
from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import (
    QAction,
    QColor,
    QFont,
    QIcon,
    QPainter,
    QPainterPath,
    QPixmap,
)
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from . import startup, theme


class UsageTray(QSystemTrayIcon):
    def __init__(
        self,
        *,
        on_open: Callable[[], None],
        on_refresh: Callable[[], None],
        on_settings: Callable[[], None],
        on_quit: Callable[[], None],
        parent=None,
    ):
        super().__init__(parent)
        self._on_open = on_open
        self._on_refresh = on_refresh
        self._on_settings = on_settings
        self._on_quit = on_quit
        self._build_menu()
        self.set_state(utilization=0.0, error=False)
        self.setToolTip("Claude Meter — fetching…")
        self.activated.connect(self._on_activated)

    # ------------------------------------------------------------------
    def _build_menu(self) -> None:
        menu = QMenu()

        open_action = QAction("Show widget", menu)
        open_action.triggered.connect(self._on_open)
        menu.addAction(open_action)

        refresh_action = QAction("Refresh now", menu)
        refresh_action.triggered.connect(self._on_refresh)
        menu.addAction(refresh_action)

        menu.addSeparator()

        run_at_startup = QAction("Run at startup", menu)
        run_at_startup.setCheckable(True)
        run_at_startup.setChecked(startup.is_enabled())
        run_at_startup.setEnabled(startup.is_frozen())
        run_at_startup.toggled.connect(self._toggle_startup)
        menu.addAction(run_at_startup)
        self._startup_action = run_at_startup

        settings_action = QAction("Settings…", menu)
        settings_action.triggered.connect(self._on_settings)
        menu.addAction(settings_action)

        menu.addSeparator()

        quit_action = QAction("Quit", menu)
        quit_action.triggered.connect(self._on_quit)
        menu.addAction(quit_action)

        self.setContextMenu(menu)

    def _toggle_startup(self, checked: bool) -> None:
        ok = startup.enable() if checked else startup.disable()
        if not ok:
            self._startup_action.setChecked(startup.is_enabled())

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self._on_open()

    # ------------------------------------------------------------------
    def set_state(
        self,
        utilization: float,
        error: bool = False,
        label: str = "",
        tooltip: Optional[str] = None,
    ) -> None:
        icon = _render_icon(utilization=utilization, error=error)
        self.setIcon(icon)
        if tooltip is not None:
            self.setToolTip(tooltip)


# ---------------------------------------------------------------------------
# Icon rendering
# ---------------------------------------------------------------------------

def _render_icon(utilization: float, error: bool) -> QIcon:
    icon = QIcon()
    for size in (16, 20, 24, 32, 40, 48, 64):
        icon.addPixmap(_render_pixmap(size, utilization, error))
    return icon


def _render_pixmap(size: int, utilization: float, error: bool) -> QPixmap:
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

    if error:
        color = QColor(theme.BRAND_CORAL_DARK)
        text = "!"
    else:
        color = theme.util_color(utilization)
        pct = int(round(utilization * 100))
        text = "99+" if pct >= 100 else str(pct)

    # Filled rounded square in the utilization color.
    path = QPainterPath()
    radius = size * 0.22
    path.addRoundedRect(0, 0, size, size, radius, radius)
    painter.fillPath(path, color)

    # White percentage — always readable on the warm colored backgrounds.
    painter.setPen(QColor("#ffffff"))
    font_size = max(6, int(size * (0.48 if len(text) <= 2 else 0.36)))
    font = QFont("Segoe UI", font_size)
    font.setBold(True)
    painter.setFont(font)
    painter.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter, text)
    painter.end()
    return pix
