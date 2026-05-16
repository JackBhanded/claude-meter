"""Detect if a *truly fullscreen* app is occupying the widget's screen.

The naive check — "foreground window covers the whole screen" — also fires
for maximized normal windows (Chrome, VS Code, etc.) because maximized
windows fill the work area. That's not what we want; the widget should
only hide for actual fullscreen takeover (games, video, presentations).

Distinguishing rule (Windows): a fullscreen window has **no caption /
title-bar**. The `WS_CAPTION` style bit (0x00C00000) is absent. Maximized
normal windows keep their caption. So:

    foreground covers the screen   AND   no WS_CAPTION   ⇒  fullscreen
"""
from __future__ import annotations

import sys

try:
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes  # type: ignore
    else:
        ctypes = None  # type: ignore
        wintypes = None  # type: ignore
except ImportError:  # pragma: no cover
    ctypes = None  # type: ignore
    wintypes = None  # type: ignore


# https://learn.microsoft.com/en-us/windows/win32/winmsg/window-styles
GWL_STYLE = -16
WS_CAPTION = 0x00C00000
WS_BORDER = 0x00800000


def is_foreground_fullscreen_on(rect_l: int, rect_t: int, rect_r: int, rect_b: int) -> bool:
    """Return True only when a real fullscreen app covers the given rect."""
    if sys.platform != "win32" or ctypes is None:
        return False
    try:
        user32 = ctypes.windll.user32  # type: ignore
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return False
        if hwnd in (user32.GetShellWindow(), user32.GetDesktopWindow()):
            return False

        rect = wintypes.RECT()  # type: ignore
        if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            return False

        # The window must cover (≈) the whole monitor rectangle.
        slop = 4
        covers = (
            rect.left <= rect_l + slop
            and rect.top <= rect_t + slop
            and rect.right >= rect_r - slop
            and rect.bottom >= rect_b - slop
        )
        if not covers:
            return False

        # And it must NOT have a title bar — only true fullscreen apps drop
        # the WS_CAPTION style. GetWindowLongW is fine for style bits.
        try:
            style = user32.GetWindowLongW(hwnd, GWL_STYLE)
        except OSError:
            return False
        has_caption = bool(style & WS_CAPTION)
        return not has_caption
    except Exception:
        return False
