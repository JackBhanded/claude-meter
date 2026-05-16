"""Register / unregister the widget under the per-user Run key.

We use HKCU so no admin elevation is needed. The Run-at-startup feature is
only available when the widget is running as a frozen ``.exe`` (the dev-mode
``python -m`` invocation isn't worth pinning to startup).
"""
from __future__ import annotations

import os
import sys
from typing import Optional

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "ClaudeMeter"


def is_frozen() -> bool:
    return getattr(sys, "frozen", False)


def executable_path() -> Optional[str]:
    """Path to the exe to register, or None if we're running unfrozen."""
    if is_frozen():
        return os.path.abspath(sys.executable)
    return None


def is_enabled() -> bool:
    if os.name != "nt":
        return False
    try:
        import winreg  # type: ignore
    except ImportError:
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            value, _ = winreg.QueryValueEx(key, VALUE_NAME)
        return bool(value)
    except FileNotFoundError:
        return False
    except OSError:
        return False


def enable() -> bool:
    if os.name != "nt":
        return False
    exe = executable_path()
    if not exe:
        return False
    try:
        import winreg  # type: ignore
    except ImportError:
        return False
    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            winreg.SetValueEx(key, VALUE_NAME, 0, winreg.REG_SZ, f'"{exe}"')
        return True
    except OSError:
        return False


def disable() -> bool:
    if os.name != "nt":
        return False
    try:
        import winreg  # type: ignore
    except ImportError:
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, VALUE_NAME)
        return True
    except FileNotFoundError:
        return True
    except OSError:
        return False
