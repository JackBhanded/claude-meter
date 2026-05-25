"""CLI entry point."""
from __future__ import annotations

import sys

from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication

from .app import WidgetApp


def main() -> int:
    QApplication.setQuitOnLastWindowClosed(False)
    qapp = QApplication(sys.argv)
    qapp.setApplicationName("Claude Meter")
    qapp.setOrganizationName("Jack")

    # Single-instance guard: if Claude Meter is already running, don't open a
    # second copy — just bow out quietly. (So a second double-click does nothing.)
    try:
        from PySide6.QtCore import QSharedMemory
        _lock = QSharedMemory("ClaudeMeterSingleInstance")
        if not _lock.create(1):
            return 0
        qapp._meter_lock = _lock  # keep it alive for the process lifetime
    except Exception:
        pass

    _app = WidgetApp(qapp)  # noqa: F841 — held alive by the event loop
    return qapp.exec()


if __name__ == "__main__":
    sys.exit(main())
