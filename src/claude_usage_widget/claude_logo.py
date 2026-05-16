"""Render the Claude 4-pointed asterisk.

Strategy:
  1. If ``assets/claude_logo.svg`` or ``assets/claude_logo.png`` exists in
     the project root (or alongside the frozen exe), load it via Qt's
     SVG / Pixmap renderer. This lets the user drop in the exact official
     Anthropic asset and have the widget use it verbatim.
  2. Otherwise, fall back to a tuned QPainter rendering — four lens petals
     at 0° / 45° / 90° / 135°, in Claude coral.

Both paths cache the renderer so they don't reload on every paint.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPixmap


def _candidate_dirs() -> list[Path]:
    """Where to look for a user-supplied logo, in priority order."""
    out: list[Path] = []
    # 1. User override location — drop it here once, works for both source
    #    runs and the frozen .exe regardless of where it lives.
    if os.name == "nt":
        appdata = os.environ.get("APPDATA")
        if appdata:
            out.append(Path(appdata) / "ClaudeMeter")
    # 2. Alongside the frozen .exe (e.g. dist\assets\claude_logo.svg).
    if getattr(sys, "frozen", False):
        out.append(Path(sys.executable).parent)
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            out.append(Path(meipass))
    # 3. Project source tree (development).
    here = Path(__file__).resolve()
    for parent in (here.parent, here.parent.parent, here.parent.parent.parent):
        out.append(parent)
    return out


def _find_asset() -> Optional[Path]:
    """Find ANY .svg or .png in assets/ (or alongside the lookup dirs).

    Preference order, lower number = better:
      1. Filename contains "claude" AND "logo"
      2. Filename contains "claude" OR "logo"
      3. Any .svg
      4. Any .png

    Searches under both ``<dir>/assets/`` and ``<dir>/`` for each candidate
    directory. This way it doesn't matter whether the user named their file
    ``claude_logo.svg``, ``anthropic-mark.png``, ``logo.svg``, ``brand.svg``
    or whatever — the widget will pick it up.
    """
    def score(name: str) -> int:
        lower = name.lower()
        has_claude = "claude" in lower
        has_logo = "logo" in lower or "mark" in lower or "icon" in lower
        if has_claude and has_logo:
            return 4
        if has_claude or has_logo:
            return 3
        if lower.endswith(".svg"):
            return 2
        return 1   # .png

    best: Optional[tuple[int, Path]] = None
    for d in _candidate_dirs():
        for sub in ("assets", "."):
            folder = d / sub
            if not folder.is_dir():
                continue
            for ext in ("*.svg", "*.png"):
                for p in folder.glob(ext):
                    if not p.is_file():
                        continue
                    s = score(p.name)
                    # Prefer earlier (higher-priority) candidate_dirs at tie.
                    if best is None or s > best[0]:
                        best = (s, p)
    return best[1] if best else None


# Resolved once on import.
_ASSET: Optional[Path] = _find_asset()
_SVG_RENDERER = None     # lazily constructed, only if SVG asset is used
_PNG_CACHE: Optional[QPixmap] = None


def draw_claude_asterisk(
    painter: QPainter,
    cx: float,
    cy: float,
    size: float,
    color: QColor,
) -> None:
    """Render the asterisk centered at ``(cx, cy)`` to fit a ``size`` square.

    ``color`` is only respected when we fall back to QPainter rendering;
    asset images are drawn with their own embedded colors.
    """
    target = QRectF(cx - size / 2.0, cy - size / 2.0, size, size)

    asset = _ASSET
    if asset is not None:
        if asset.suffix.lower() == ".svg":
            _render_svg(painter, asset, target)
            return
        if asset.suffix.lower() == ".png":
            _render_pixmap(painter, asset, target)
            return

    _render_qpainter(painter, cx, cy, size, color)


# ---------------------------------------------------------------------------
# Asset paths
# ---------------------------------------------------------------------------

def _render_svg(painter: QPainter, path: Path, target: QRectF) -> None:
    global _SVG_RENDERER
    if _SVG_RENDERER is None:
        try:
            from PySide6.QtSvg import QSvgRenderer  # type: ignore
            _SVG_RENDERER = QSvgRenderer(str(path))
        except Exception:
            _SVG_RENDERER = False  # mark as unavailable
    if _SVG_RENDERER and _SVG_RENDERER is not False:
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        _SVG_RENDERER.render(painter, target)
        painter.restore()


def _render_pixmap(painter: QPainter, path: Path, target: QRectF) -> None:
    global _PNG_CACHE
    if _PNG_CACHE is None:
        _PNG_CACHE = QPixmap(str(path))
    if _PNG_CACHE.isNull():
        return
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
    painter.drawPixmap(target, _PNG_CACHE, QRectF(_PNG_CACHE.rect()))
    painter.restore()


# ---------------------------------------------------------------------------
# QPainter fallback — tuned by eye to match the official mark closely.
# Pure quadratic lens petals (sharper tips than cubic), 5.5:1 ratio.
# ---------------------------------------------------------------------------

def _render_qpainter(
    painter: QPainter,
    cx: float,
    cy: float,
    size: float,
    color: QColor,
) -> None:
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.translate(cx, cy)
    painter.setBrush(color)
    painter.setPen(Qt.PenStyle.NoPen)

    long_axis = size / 2.0
    short_axis = size / 5.5

    for angle in (0, 45, 90, 135):
        painter.save()
        painter.rotate(angle)
        path = QPainterPath()
        path.moveTo(-long_axis, 0)
        path.quadTo(0, -short_axis,  long_axis, 0)
        path.quadTo(0,  short_axis, -long_axis, 0)
        painter.drawPath(path)
        painter.restore()

    painter.restore()
