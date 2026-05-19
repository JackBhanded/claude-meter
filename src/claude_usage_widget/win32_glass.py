"""Request the Windows 11 "Acrylic" frosted-glass backdrop on a window.

Used by both the pinned widget and the tooltip so they both get the same
glassy look. Silently no-ops on non-Windows, on Windows 10, or if the API
call fails for any reason — the ``setWindowOpacity`` fallback still
produces a translucent effect everywhere.
"""
from __future__ import annotations

import sys


def try_enable_glass_backdrop(hwnd: int) -> None:
    """Request the Acrylic backdrop. ``hwnd`` is the native Win32 window
    handle (``int(widget.winId())``). Must be called *after* the window is
    visible — handle 0 is silently ignored."""
    if sys.platform != "win32" or not hwnd:
        return
    try:
        import ctypes

        # https://learn.microsoft.com/en-us/windows/win32/api/dwmapi/ne-dwmapi-dwm_systembackdrop_type
        DWMWA_SYSTEMBACKDROP_TYPE = 38
        DWMSBT_TRANSIENTWINDOW = 3   # Acrylic — most "glass" effect

        value = ctypes.c_int(DWMSBT_TRANSIENTWINDOW)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, DWMWA_SYSTEMBACKDROP_TYPE,
            ctypes.byref(value), ctypes.sizeof(value),
        )
    except Exception:
        pass
