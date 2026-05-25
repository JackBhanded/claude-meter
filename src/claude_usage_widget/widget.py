"""The pinned strip above the taskbar — Claude-team-polished layout.

Vertical stack, three zones with a thin divider between the data and footer:

  ┌─────────────────────────────────────────┐
  │  ✶   Session ·····················  40% │   ← data zone
  │      Weekly  ·····················  18% │
  │  ───────────────────────────────────────│   ← hairline divider
  │  ⏱  1h 35m to reset             ↻       │   ← footer (countdown + refresh)
  └─────────────────────────────────────────┘
"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import List, Optional

from PySide6.QtCore import QEvent, QPoint, QRect, Qt, QTimer, Signal
from PySide6.QtGui import (
    QAction,
    QBrush,
    QColor,
    QContextMenuEvent,
    QFont,
    QFontMetrics,
    QGuiApplication,
    QLinearGradient,
    QMouseEvent,
    QPainter,
    QPainterPath,
    QPen,
)
from PySide6.QtWidgets import QMenu, QWidget

from . import fullscreen, history, icons, products, theme
from .claude_logo import draw_claude_asterisk
from .settings import Settings
from .tooltip import TooltipPanel
from .usage import Quota, UsageSnapshot
from .win32_glass import try_enable_glass_backdrop


# Dimensions tuned for breathing room. The ticker is a premium status pill,
# not a cramped tray-info-blob.
WIDGET_W = 264
WIDGET_H = 84
LOGO_AREA = 34
PADDING_X = 14
PADDING_Y = 11
DATA_ZONE_H = 40
FOOTER_H = WIDGET_H - DATA_ZONE_H - PADDING_Y * 2
REFRESH_ICON_SIZE = 13

COMPACT_PRIMARY_KEY = "five_hour"
COMPACT_SECONDARY_KEY = "seven_day"


REFRESH_COOLDOWN_S = 15
REFRESHING_LABEL_S = 2.0


class UsageWidget(QWidget):
    """Compact pinned strip above the taskbar."""

    clicked = Signal()
    refresh_requested = Signal()
    settings_requested = Signal()
    quit_requested = Signal()

    def __init__(self, settings: Settings, parent=None):
        super().__init__(
            parent,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowDoesNotAcceptFocus,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setMouseTracking(True)
        self.resize(WIDGET_W, WIDGET_H)
        self.setCursor(Qt.CursorShape.ArrowCursor)

        self._settings = settings
        self._snapshot: Optional[UsageSnapshot] = None
        self._buckets: list[history.Bucket] = []
        self._products: List[products.DetectedProduct] = []
        self._error: Optional[str] = None
        self._refresh_hover = False
        self._last_refresh_click: float = 0.0   # monotonic seconds
        self._refresh_pending_until: float = 0.0  # show "Refreshing…" until this time
        # When True, the user dismissed the widget via right-click → Hide. The
        # auto-show visibility tick respects this; only manual_show() clears it.
        self._manually_hidden = False
        # Snooze timer: when the user picks "Hide for 15 min", this fires
        # manual_show() automatically.
        self._snooze_timer: Optional[QTimer] = None

        self._tooltip = TooltipPanel()

        # Apply visual settings (opacity, glass backdrop). Must come AFTER
        # ``_tooltip`` is created because it propagates settings to it.
        self.apply_visual_settings()

        self._tick = QTimer(self)
        self._tick.setInterval(30_000)
        self._tick.timeout.connect(self.update)
        self._tick.start()

        self._visibility_tick = QTimer(self)
        self._visibility_tick.setInterval(1_000)
        self._visibility_tick.timeout.connect(self._update_visibility)
        self._visibility_tick.start()

        screen = self.screen() or QGuiApplication.primaryScreen()
        if screen:
            screen.geometryChanged.connect(lambda *_: self.reposition())
        self.reposition()

    # ------------------------------------------------------------------
    def update_data(
        self,
        snapshot: Optional[UsageSnapshot],
        buckets: list[history.Bucket],
        detected: List[products.DetectedProduct],
    ) -> None:
        self._snapshot = snapshot
        self._buckets = buckets
        self._products = detected
        self._error = snapshot.error if snapshot and not snapshot.ok else None
        # New data arrived — clear "Refreshing…" footer state.
        self._refresh_pending_until = 0.0
        self._tooltip.update_data(snapshot, buckets, detected)
        self.update()

    # ------------------------------------------------------------------
    def reposition(self) -> None:
        screen = self.screen() or QGuiApplication.primaryScreen()
        if not screen:
            return
        avail: QRect = screen.availableGeometry()
        x = avail.right() - self.width() - self._settings.pos_offset_right
        y = avail.bottom() - self.height() - self._settings.pos_offset_bottom
        self.move(max(avail.left(), x), max(avail.top(), y))

    def _update_visibility(self) -> None:
        # If the user explicitly dismissed it, keep it hidden until they
        # bring it back from the tray menu.
        if self._manually_hidden:
            return
        if not self._settings.hide_when_fullscreen:
            if not self.isVisible():
                self.show()
            return
        screen = self.screen() or QGuiApplication.primaryScreen()
        if not screen:
            return
        full = screen.geometry()
        if fullscreen.is_foreground_fullscreen_on(
            full.left(), full.top(), full.right(), full.bottom()
        ):
            if self.isVisible():
                self.hide()
                if self._tooltip.isVisible():
                    self._tooltip.hide()
        else:
            if not self.isVisible():
                self.show()

    # ------------------------------------------------------------------
    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        # Pill background — cream with subtle warm border.
        r, g, b, a = theme.SURFACE_BG_RGBA
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), 12, 12)
        p.fillPath(path, QColor(r, g, b, a))
        p.setPen(QPen(QColor(theme.BORDER), 1))
        p.drawPath(path)

        # Claude asterisk in the left margin, vertically centered on the data zone.
        logo_cy = PADDING_Y + DATA_ZONE_H / 2
        draw_claude_asterisk(p, PADDING_X + LOGO_AREA / 2 - 4, logo_cy,
                             size=24, color=QColor(theme.BRAND_CORAL))

        # ---- Data zone (two bars) -------------------------------------
        bar_x = PADDING_X + LOGO_AREA
        bar_w = self.width() - bar_x - PADDING_X
        bar_h = 6
        row_gap = 6
        top_y = PADDING_Y + 10
        bot_y = top_y + bar_h + row_gap + 10  # +10 for the label-line above each bar

        snap = self._snapshot
        primary = secondary = None
        if snap and snap.quotas:
            primary = snap.by_key(COMPACT_PRIMARY_KEY) or snap.quotas[0]
            secondary = snap.by_key(COMPACT_SECONDARY_KEY)
            if secondary is None and len(snap.quotas) > 1:
                others = [q for q in snap.quotas if q is not primary]
                secondary = max(others, key=lambda q: q.utilization, default=None)

        if self._error and not (snap and snap.quotas):
            _draw_compact_bar(p, bar_x, top_y, bar_w, bar_h, 0.0, error=True)
            _draw_compact_bar(p, bar_x, bot_y, bar_w, bar_h, 0.0, error=True)
            p.setFont(QFont("Segoe UI", 7))
            p.setPen(QColor(theme.BRAND_CORAL_DARK))
            p.drawText(bar_x, self.height() - PADDING_Y - 2, _short_error(self._error))
            p.end()
            return

        _draw_row(p, bar_x, top_y, bar_w, bar_h, primary, "Session")
        _draw_row(p, bar_x, bot_y, bar_w, bar_h, secondary, "Weekly")

        # ---- Divider ---------------------------------------------------
        div_y = PADDING_Y + DATA_ZONE_H + 2
        p.setPen(QPen(QColor(theme.BORDER), 1))
        p.drawLine(PADDING_X, div_y, self.width() - PADDING_X, div_y)

        # ---- Footer: countdown left, refresh button right --------------
        footer_y_center = div_y + (self.height() - div_y - PADDING_Y) / 2
        rx = self.width() - PADDING_X - REFRESH_ICON_SIZE / 2 - 2
        ry = footer_y_center

        refreshing = self._is_refreshing()
        in_cooldown = self._in_cooldown()
        # Stale = we have data but the most recent fetch failed. We rely on
        # the snapshot's ok/error fields; the controller injects last-good
        # data with the error string when a refresh fails.
        has_data = bool(snap and snap.quotas)
        stale = bool(has_data and snap and not snap.ok and snap.error)
        # Auth-expired is a *specific* kind of stale that the user can fix.
        auth_expired = bool(stale and snap and snap.error and "Auth" in snap.error)

        if self._refresh_hover and not refreshing:
            p.setBrush(QColor(theme.BORDER))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(int(rx - 9), int(ry - 9), 18, 18)

        # Refresh icon — dimmer when in cooldown so it visibly "rests".
        icon_color = QColor(theme.TEXT_SECONDARY)
        if in_cooldown and not refreshing:
            icon_color = QColor(theme.TEXT_TERTIARY)
            icon_color.setAlpha(130)
        icons.draw_refresh(
            p, rx, ry, size=REFRESH_ICON_SIZE,
            color=icon_color,
            stroke_w=1.2,
        )

        # Tiny warning dot if the latest refresh failed. Amber for generic
        # transient errors; red for auth-expired (user-actionable).
        if stale:
            warn_x = rx - REFRESH_ICON_SIZE - 6
            p.setBrush(QColor("#DC2626") if auth_expired else QColor("#EA580C"))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(int(warn_x - 3), int(ry - 3), 6, 6)

        # Footer text on the left — prioritise the most informative message.
        if refreshing:
            footer_text = "Refreshing…"
            footer_color = QColor(theme.TEXT_SECONDARY)
            show_clock = False
        elif auth_expired:
            # Specific, user-actionable. Stand out with the red/coral color.
            footer_text = "Session expired — run `claude` to refresh"
            footer_color = QColor("#DC2626")
            show_clock = False
        elif stale:
            footer_text = "Couldn't refresh · showing last update"
            footer_color = QColor(theme.TEXT_SECONDARY)
            show_clock = False
        else:
            footer_text, _imminent = _compute_countdown(snap)
            footer_color = QColor(theme.TEXT_SECONDARY)
            show_clock = True

        p.setFont(QFont("Segoe UI", 8))
        p.setPen(footer_color)
        text_x = PADDING_X + (14 if show_clock else 0)
        if show_clock:
            icons.draw_clock(
                p,
                PADDING_X + 5,
                footer_y_center,
                size=10,
                color=QColor(theme.TEXT_TERTIARY),
                stroke_w=1.1,
            )
        p.drawText(text_x, int(footer_y_center + 3), footer_text)
        p.end()

    # ------------------------------------------------------------------
    def enterEvent(self, _event: QEvent) -> None:
        anchor = self.mapToGlobal(QPoint(self.width() // 2, 0))
        self._tooltip.show_near(anchor)

    def leaveEvent(self, _event: QEvent) -> None:
        if self._refresh_hover:
            self._refresh_hover = False
            self.update()
        QTimer.singleShot(120, self._maybe_hide_tooltip)

    def _maybe_hide_tooltip(self) -> None:
        if self._tooltip.isVisible() and not self._tooltip.underMouse():
            self._tooltip.hide()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        was = self._refresh_hover
        hit = self._refresh_hit(event.position().x(), event.position().y())
        # Cooldown: visually dim and don't show the pointer cursor.
        in_cooldown = self._in_cooldown()
        self._refresh_hover = hit and not in_cooldown
        self.setCursor(
            Qt.CursorShape.PointingHandCursor if self._refresh_hover
            else Qt.CursorShape.ArrowCursor
        )
        if was != self._refresh_hover:
            self.update()

    # ------------------------------------------------------------------
    # Right-click menu — Hide / Refresh / Settings
    # ------------------------------------------------------------------
    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        menu = QMenu(self)

        hide_action = QAction("Hide widget", menu)
        hide_action.triggered.connect(self.manual_hide)
        menu.addAction(hide_action)

        snooze_minutes = max(1, int(self._settings.snooze_minutes))
        snooze_action = QAction(f"Hide for {snooze_minutes} min", menu)
        snooze_action.triggered.connect(lambda: self.manual_snooze(snooze_minutes))
        menu.addAction(snooze_action)

        refresh_action = QAction("Refresh now", menu)
        refresh_action.triggered.connect(self.refresh_requested.emit)
        menu.addAction(refresh_action)

        menu.addSeparator()

        settings_action = QAction("Settings…", menu)
        settings_action.triggered.connect(self.settings_requested.emit)
        menu.addAction(settings_action)

        menu.addSeparator()

        quit_action = QAction("Quit Claude Meter", menu)
        quit_action.triggered.connect(self.quit_requested.emit)
        menu.addAction(quit_action)

        # Hide the tooltip while the menu is open so they don't overlap.
        if self._tooltip.isVisible():
            self._tooltip.hide()

        menu.exec(event.globalPos())

    def manual_hide(self) -> None:
        """User dismissed the widget. Tray icon brings it back."""
        self._manually_hidden = True
        if self._tooltip.isVisible():
            self._tooltip.hide()
        self.hide()

    def manual_show(self) -> None:
        """User re-summoned the widget from the tray."""
        self._manually_hidden = False
        self._cancel_snooze()
        self.show()
        self.reposition()

    def manual_snooze(self, minutes: int) -> None:
        """Hide the widget AND schedule auto-show after ``minutes``."""
        self._manually_hidden = True
        if self._tooltip.isVisible():
            self._tooltip.hide()
        self.hide()
        self._cancel_snooze()
        self._snooze_timer = QTimer(self)
        self._snooze_timer.setSingleShot(True)
        self._snooze_timer.timeout.connect(self.manual_show)
        self._snooze_timer.start(max(1, minutes) * 60 * 1000)

    def _cancel_snooze(self) -> None:
        if self._snooze_timer is not None:
            self._snooze_timer.stop()
            self._snooze_timer.deleteLater()
            self._snooze_timer = None

    def apply_visual_settings(self) -> None:
        """Apply opacity + glass backdrop from current settings. Safe to call
        repeatedly (e.g. after the Settings dialog closes)."""
        opacity = max(0.30, min(1.0, float(self._settings.opacity)))
        self.setWindowOpacity(opacity)
        self._tooltip.setWindowOpacity(opacity)
        self._tooltip.set_glass_enabled(self._settings.enable_glass_backdrop)
        # Apply glass NOW for the pinned widget (only effective if visible).
        if self._settings.enable_glass_backdrop and self.isVisible():
            try_enable_glass_backdrop(int(self.winId()))

    # ------------------------------------------------------------------
    def showEvent(self, event) -> None:
        super().showEvent(event)
        # winId() is reliably valid once the window has been shown.
        if self._settings.enable_glass_backdrop:
            try_enable_glass_backdrop(int(self.winId()))

    # ------------------------------------------------------------------
    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return
        if self._refresh_hit(event.position().x(), event.position().y()):
            if self._in_cooldown():
                # Silently ignore — clicking won't help during cooldown.
                return
            now = time.monotonic()
            self._last_refresh_click = now
            self._refresh_pending_until = now + REFRESHING_LABEL_S
            self.refresh_requested.emit()
            # Schedule a repaint when the "Refreshing…" label should disappear
            # even if no snapshot arrives in time.
            QTimer.singleShot(int(REFRESHING_LABEL_S * 1000) + 50, self.update)
            self.update()
            return
        self.clicked.emit()

    def _in_cooldown(self) -> bool:
        if self._last_refresh_click <= 0:
            return False
        return (time.monotonic() - self._last_refresh_click) < REFRESH_COOLDOWN_S

    def _is_refreshing(self) -> bool:
        return time.monotonic() < self._refresh_pending_until

    def _refresh_hit(self, x: float, y: float) -> bool:
        div_y = PADDING_Y + DATA_ZONE_H + 2
        footer_y_center = div_y + (self.height() - div_y - PADDING_Y) / 2
        rx = self.width() - PADDING_X - REFRESH_ICON_SIZE / 2 - 2
        # 11-px radius hit-target (slightly larger than the visible icon).
        return (x - rx) ** 2 + (y - footer_y_center) ** 2 <= 11 ** 2


# ---------------------------------------------------------------------------
# Drawing helpers
# ---------------------------------------------------------------------------

def _draw_compact_bar(
    p: QPainter, x: int, y: int, w: int, h: int, utilization: float, error: bool = False
) -> None:
    bg = QPainterPath()
    bg.addRoundedRect(x, y, w, h, h / 2, h / 2)
    p.fillPath(bg, QColor(theme.TRACK))
    color = QColor(theme.BRAND_CORAL_DARK) if error else theme.util_color(utilization)
    u = max(0.0, min(1.0, utilization))
    if u > 0:
        fw = max(2, int(w * u))
        fg = QPainterPath()
        fg.addRoundedRect(x, y, fw, h, h / 2, h / 2)
        # Fleet look: a soft left-to-right gradient (lighter -> the status colour)
        # gives the bar a glassy sheen instead of a flat fill.
        grad = QLinearGradient(float(x), float(y), float(x + fw), float(y))
        grad.setColorAt(0.0, color.lighter(132))
        grad.setColorAt(1.0, color)
        p.fillPath(fg, QBrush(grad))


def _draw_row(
    p: QPainter,
    bar_x: int,
    bar_y: int,
    bar_w: int,
    bar_h: int,
    quota: Optional[Quota],
    short_label: str,
) -> None:
    label_font = QFont("Segoe UI", 8, QFont.Weight.DemiBold)
    pct_font = QFont("Segoe UI", 8)
    p.setFont(label_font)
    p.setPen(QColor(theme.TEXT_PRIMARY))
    p.drawText(bar_x, bar_y - 2, short_label)
    if quota is None:
        _draw_compact_bar(p, bar_x, bar_y, bar_w, bar_h, 0.0)
        p.setFont(pct_font)
        fm = QFontMetrics(pct_font)
        p.setPen(QColor(theme.TEXT_TERTIARY))
        p.drawText(bar_x + bar_w - fm.horizontalAdvance("—"), bar_y - 2, "—")
        return
    _draw_compact_bar(p, bar_x, bar_y, bar_w, bar_h, quota.utilization)
    pct_text = f"{int(round(quota.percent))}%"
    p.setFont(pct_font)
    fm = QFontMetrics(pct_font)
    p.setPen(theme.util_color(quota.utilization))
    p.drawText(bar_x + bar_w - fm.horizontalAdvance(pct_text), bar_y - 2, pct_text)


def _compute_countdown(snap: Optional[UsageSnapshot]) -> tuple[str, Optional[Quota]]:
    """Return (display text, the quota row whose reset is most imminent).

    Format: "resets in 4h 48m · Sat 02:50 AM"
    """
    if snap is None or not snap.quotas:
        return ("—", None)
    candidates = [q for q in snap.quotas if q.resets_at is not None]
    if not candidates:
        return ("—", None)
    imminent = min(candidates, key=lambda q: q.resets_at)  # type: ignore[arg-type]
    delta = (imminent.resets_at - datetime.now(tz=timezone.utc)).total_seconds()  # type: ignore[operator]
    if delta < 0:
        return ("resetting…", imminent)
    days, rem = divmod(int(delta), 86400)
    hours, rem = divmod(rem, 3600)
    mins = rem // 60
    if days > 0:
        rel = f"{days}d {hours}h"
    elif hours > 0:
        rel = f"{hours}h {mins}m"
    else:
        rel = f"{mins}m"
    local = imminent.resets_at.astimezone().strftime("%a %I:%M %p").lstrip("0")  # type: ignore[union-attr]
    return (f"resets in {rel} · {local}", imminent)


def _short_error(err: str) -> str:
    if "Rate-limited" in err:
        return "API rate-limited"
    if "Auth" in err:
        return "Auth — re-login"
    if "Network" in err:
        return "Network error"
    return err[:18]
