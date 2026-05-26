"""Rich hover tooltip — light theme, Claude branded."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontMetrics,
    QPainter,
    QPainterPath,
    QPen,
)
from PySide6.QtWidgets import QWidget

from . import history, products, theme
from .claude_logo import draw_claude_asterisk
from .usage import CountQuota, Overage, Quota, UsageSnapshot
from .win32_glass import try_enable_glass_backdrop


PAD = 18
ROW_HEIGHT = 48
ROW_HEIGHT_COMPACT = 24
HEADER_HEIGHT = 46


class TooltipPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(
            parent,
            Qt.WindowType.ToolTip
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._snapshot: Optional[UsageSnapshot] = None
        self._buckets: list[history.Bucket] = []
        self._products: List[products.DetectedProduct] = []
        self._glass_enabled = False
        self.resize(400, 240)
        # Keep the "resets in Xm" countdowns fresh while the panel sits open —
        # otherwise they'd freeze at the last data poll and read stale.
        from PySide6.QtCore import QTimer
        self._tick = QTimer(self)
        self._tick.setInterval(30000)
        self._tick.timeout.connect(self.update)

    # ------------------------------------------------------------------
    def set_glass_enabled(self, enabled: bool) -> None:
        """Toggle the frosted-glass backdrop request. Applies on next show
        (and immediately if currently visible)."""
        self._glass_enabled = enabled
        if enabled and self.isVisible():
            try_enable_glass_backdrop(int(self.winId()))

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._tick.start()
        if self._glass_enabled:
            try_enable_glass_backdrop(int(self.winId()))

    def hideEvent(self, event) -> None:
        self._tick.stop()
        super().hideEvent(event)

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
        self._resize_for_content()
        self.update()

    def _resize_for_content(self) -> None:
        h = HEADER_HEIGHT
        if self._snapshot and self._snapshot.quotas:
            h += ROW_HEIGHT * len(self._snapshot.quotas)
        else:
            h += 40
        if self._snapshot and self._snapshot.count_quotas:
            h += 20 + ROW_HEIGHT_COMPACT * len(self._snapshot.count_quotas)
        if self._snapshot and self._snapshot.overage is not None:
            h += 8 + ROW_HEIGHT_COMPACT
        if self._products:
            h += 26 + 18 * min(5, len(self._products))
        h += 60   # sparkline + footer
        self.resize(400, max(240, h))

    # ------------------------------------------------------------------
    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        # Card
        r, g, b, a = theme.SURFACE_BG_RGBA
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), 14, 14)
        p.fillPath(path, QColor(r, g, b, a))
        p.setPen(QPen(QColor(theme.BORDER_STRONG), 1))
        p.drawPath(path)

        snap = self._snapshot

        # ---- Header: asterisk + "Claude Meter" + plan name (right) -----
        draw_claude_asterisk(p, PAD + 10, PAD + 12, size=22, color=QColor(theme.BRAND_CORAL))
        p.setPen(QColor(theme.TEXT_PRIMARY))
        title_font = QFont("Segoe UI", 12, QFont.Weight.Bold)
        p.setFont(title_font)
        p.drawText(PAD + 28, PAD + 17, "Claude Meter")
        if snap and snap.plan:
            plan_font = QFont("Segoe UI", 9)
            p.setFont(plan_font)
            p.setPen(QColor(theme.TEXT_SECONDARY))
            fm = QFontMetrics(plan_font)
            p.drawText(self.width() - PAD - fm.horizontalAdvance(snap.plan), PAD + 17, snap.plan)

        # Divider
        p.setPen(QPen(QColor(theme.BORDER), 1))
        p.drawLine(PAD, PAD + 30, self.width() - PAD, PAD + 30)

        y = PAD + 40

        # ---- Body ------------------------------------------------------
        if snap is None:
            p.setPen(QColor(theme.TEXT_SECONDARY))
            p.drawText(PAD, y + 16, "Fetching usage…")
            y += 40
        elif not snap.ok and not snap.quotas:
            p.setPen(QColor(theme.BRAND_CORAL_DARK))
            p.drawText(PAD, y + 16, snap.error or "No data")
            y += 40
        else:
            for q in snap.quotas:
                _draw_quota_row(p, PAD, y, self.width() - 2 * PAD, q)
                y += ROW_HEIGHT
            if snap.count_quotas:
                y += 6
                _section_label(p, PAD, y, "Additional features")
                y += 14
                for cq in snap.count_quotas:
                    _draw_count_row(p, PAD, y, self.width() - 2 * PAD, cq)
                    y += ROW_HEIGHT_COMPACT
            if snap.overage is not None:
                y += 4
                _draw_overage_row(p, PAD, y, self.width() - 2 * PAD, snap.overage)
                y += ROW_HEIGHT_COMPACT

        # ---- Detected products ----------------------------------------
        if self._products:
            y += 10
            _section_label(p, PAD, y, "Detected on this machine")
            y += 14
            p.setFont(QFont("Segoe UI", 9))
            for prod in self._products[:5]:
                p.setPen(QColor(theme.TEXT_PRIMARY))
                p.drawText(PAD + 4, y + 4, "•")
                p.drawText(PAD + 16, y + 4, prod.label)
                y += 16

        # ---- Sparkline ------------------------------------------------
        spark = history.sparkline_series(self._buckets, "u7d", points=96)
        spark_y = self.height() - 38
        if len(spark) > 2:
            _draw_sparkline(p, PAD, spark_y, self.width() - 2 * PAD, 20, spark)

        # ---- Footer ---------------------------------------------------
        if snap and snap.fetched_at:
            age = (datetime.now(tz=timezone.utc) - snap.fetched_at).total_seconds()
            footer = f"Updated {_humanize_age(age)} ago"
        else:
            footer = "Not yet fetched"
        p.setFont(QFont("Segoe UI", 7))
        p.setPen(QColor(theme.TEXT_TERTIARY))
        p.drawText(PAD, self.height() - 10, footer)
        p.end()

    # ------------------------------------------------------------------
    def show_near(self, global_anchor: QPoint) -> None:
        """Place the tooltip so it never visually overlaps the pinned ticker.

        Strategy:
          1. Try ABOVE the anchor (default — clean, conventional).
          2. If that won't fit on the screen, place LEFT of the anchor.
          3. If left won't fit either, place RIGHT.
          4. Final clamp so the tooltip is fully on-screen.
        """
        screen = self.screen()
        avail = screen.availableGeometry() if screen else None

        w = self.width()
        h = self.height()
        # Approximate half-width of the pinned ticker. Tooltip should leave
        # at least this much room around the anchor when placed side-by-side.
        widget_half_w = 120
        gap = 12

        # Strategy 1 — above the widget (the default visual layout)
        x = global_anchor.x() - w // 2
        y = global_anchor.y() - h - 10

        if avail is not None:
            if y < avail.top() + 4:
                # Won't fit above — try to the LEFT of the ticker
                x = global_anchor.x() - widget_half_w - w - gap
                y = global_anchor.y() - h + 30        # bottom-align roughly
                if x < avail.left() + 4:
                    # Won't fit left either — go RIGHT of the ticker
                    x = global_anchor.x() + widget_half_w + gap

            # Final clamp to keep the whole tooltip on-screen
            x = max(avail.left() + 4, min(x, avail.right() - w - 4))
            y = max(avail.top() + 4, min(y, avail.bottom() - h - 4))

        self.move(x, y)
        self.show()


# ---------------------------------------------------------------------------
# Row drawing
# ---------------------------------------------------------------------------

def _section_label(p: QPainter, x: int, y: int, text: str) -> None:
    p.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
    p.setPen(QColor(theme.TEXT_SECONDARY))
    p.drawText(x, y, text.upper())


def _draw_quota_row(p: QPainter, x: int, y: int, w: int, q: Quota) -> None:
    color = theme.util_color(q.utilization)
    p.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
    p.setPen(QColor(theme.TEXT_PRIMARY))
    p.drawText(x, y + 12, q.label)
    pct_text = f"{q.percent:.1f}% used"
    pct_font = QFont("Segoe UI", 9)
    p.setFont(pct_font)
    fm = QFontMetrics(pct_font)
    p.setPen(color)
    p.drawText(x + w - fm.horizontalAdvance(pct_text), y + 12, pct_text)

    bar_y = y + 18
    bar_h = 8
    bg = QPainterPath()
    bg.addRoundedRect(x, bar_y, w, bar_h, bar_h / 2, bar_h / 2)
    p.fillPath(bg, QColor(theme.TRACK))
    u = max(0.0, min(1.0, q.utilization))
    if u > 0:
        fg = QPainterPath()
        fg.addRoundedRect(x, bar_y, max(2, int(w * u)), bar_h, bar_h / 2, bar_h / 2)
        p.fillPath(fg, color)

    p.setFont(QFont("Segoe UI", 7))
    p.setPen(QColor(theme.TEXT_TERTIARY))
    p.drawText(x, y + 40, _format_reset(q.resets_at))


def _draw_count_row(p: QPainter, x: int, y: int, w: int, cq: CountQuota) -> None:
    label_font = QFont("Segoe UI", 9)
    p.setFont(label_font)
    p.setPen(QColor(theme.TEXT_PRIMARY))
    p.drawText(x, y + 12, cq.label)
    text = f"{cq.used} / {cq.limit}"
    fm = QFontMetrics(label_font)
    p.setPen(QColor(theme.TEXT_SECONDARY))
    p.drawText(x + w - fm.horizontalAdvance(text), y + 12, text)
    bar_y = y + 16
    bar_h = 3
    bg = QPainterPath()
    bg.addRoundedRect(x, bar_y, w, bar_h, bar_h / 2, bar_h / 2)
    p.fillPath(bg, QColor(theme.TRACK))
    if cq.utilization > 0:
        fg = QPainterPath()
        fg.addRoundedRect(x, bar_y, max(2, int(w * cq.utilization)), bar_h, bar_h / 2, bar_h / 2)
        p.fillPath(fg, theme.util_color(cq.utilization))


def _draw_overage_row(p: QPainter, x: int, y: int, w: int, ov: Overage) -> None:
    label_font = QFont("Segoe UI", 9)
    p.setFont(label_font)
    p.setPen(QColor(theme.TEXT_PRIMARY))
    p.drawText(x, y + 12, "Extra usage")
    text = f"${ov.current_usd:,.2f} / ${ov.budget_usd:,.2f}"
    fm = QFontMetrics(label_font)
    p.setPen(QColor(theme.TEXT_SECONDARY))
    p.drawText(x + w - fm.horizontalAdvance(text), y + 12, text)
    bar_y = y + 16
    bar_h = 3
    bg = QPainterPath()
    bg.addRoundedRect(x, bar_y, w, bar_h, bar_h / 2, bar_h / 2)
    p.fillPath(bg, QColor(theme.TRACK))
    if ov.utilization > 0:
        fg = QPainterPath()
        fg.addRoundedRect(x, bar_y, max(2, int(w * ov.utilization)), bar_h, bar_h / 2, bar_h / 2)
        p.fillPath(fg, theme.util_color(ov.utilization))


def _draw_sparkline(painter: QPainter, x: int, y: int, w: int, h: int, series: list[float]) -> None:
    if len(series) < 2:
        return
    painter.save()
    pen = QPen(QColor(theme.BRAND_CORAL))
    pen.setWidthF(1.3)
    painter.setPen(pen)
    n = len(series)
    step = w / (n - 1)
    pts = []
    for i, v in enumerate(series):
        vv = max(0.0, min(1.0, v))
        pts.append((x + i * step, y + h - vv * h))
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        painter.drawLine(int(x0), int(y0), int(x1), int(y1))
    painter.restore()


def _format_reset(reset_at) -> str:
    if reset_at is None:
        return "resets — unknown"
    delta = (reset_at - datetime.now(tz=timezone.utc)).total_seconds()
    if delta < 0:
        return f"reset at {reset_at.astimezone().strftime('%H:%M')} (passed)"
    days, rem = divmod(int(delta), 86400)
    hours, rem = divmod(rem, 3600)
    mins = rem // 60
    if days > 0:
        rel = f"{days}d {hours}h"
    elif hours > 0:
        rel = f"{hours}h {mins}m"
    else:
        rel = f"{mins}m"
    local = reset_at.astimezone().strftime("%a %H:%M")
    return f"resets in {rel} · {local}"


def _humanize_age(seconds: float) -> str:
    s = int(seconds)
    if s < 60:
        return f"{s}s"
    if s < 3600:
        return f"{s // 60}m"
    return f"{s // 3600}h"


def _shorten(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return "…" + text[-(max_chars - 1):]
