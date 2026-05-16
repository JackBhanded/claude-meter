"""Programmatically-rendered icon glyphs (refresh, info, …) used in the UI.

Drawing with QPainter keeps the icons crisp at any DPI and avoids shipping
binary assets. Each function takes the painter, a center point, a size in
pixels, and a color.
"""
from __future__ import annotations

import math

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen


def draw_refresh(
    painter: QPainter,
    cx: float,
    cy: float,
    size: float,
    color: QColor,
    stroke_w: float = 1.4,
) -> None:
    """A clockwise circular arrow — the universal "refresh" glyph.

    The arc goes about 270° (3/4 of a circle) ending with a small arrow head.
    """
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    pen = QPen(color)
    pen.setWidthF(stroke_w)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)

    r = size / 2.0
    # Qt's drawArc takes 1/16ths of a degree. We span ~290° starting from a
    # spot in the upper-right so the arrow head sits at the top-right.
    start_deg = 60      # angle measured CCW from 3-o'clock
    span_deg = -300     # negative = clockwise sweep
    painter.drawArc(
        int(cx - r), int(cy - r), int(size), int(size),
        start_deg * 16, span_deg * 16,
    )

    # Arrow head at the end of the arc.
    end_rad = math.radians(start_deg + span_deg)
    ex = cx + r * math.cos(end_rad)
    ey = cy - r * math.sin(end_rad)
    # Tangent direction (clockwise sweep) — perpendicular to radial.
    tx = math.sin(end_rad)
    ty = math.cos(end_rad)
    # Inward normal (toward center).
    nx = -math.cos(end_rad)
    ny = math.sin(end_rad)

    head = size * 0.32
    p1x = ex + tx * head * 0.5 + nx * head * 0.5
    p1y = ey - ty * head * 0.5 + ny * head * 0.5
    p2x = ex - tx * head * 0.5 + nx * head * 0.5
    p2y = ey + ty * head * 0.5 + ny * head * 0.5

    path = QPainterPath()
    path.moveTo(ex, ey)
    path.lineTo(p1x, p1y)
    path.lineTo(p2x, p2y)
    path.closeSubpath()
    painter.fillPath(path, color)
    painter.restore()


def draw_clock(
    painter: QPainter,
    cx: float,
    cy: float,
    size: float,
    color: QColor,
    stroke_w: float = 1.3,
) -> None:
    """A minimal clock face (circle + hour/minute hands at 10:10)."""
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    pen = QPen(color)
    pen.setWidthF(stroke_w)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    r = size / 2.0
    painter.drawEllipse(int(cx - r), int(cy - r), int(size), int(size))
    # Minute hand to 12 (straight up).
    painter.drawLine(int(cx), int(cy), int(cx), int(cy - r * 0.7))
    # Hour hand to 4 (down-right).
    painter.drawLine(int(cx), int(cy), int(cx + r * 0.55), int(cy + r * 0.30))
    painter.restore()
