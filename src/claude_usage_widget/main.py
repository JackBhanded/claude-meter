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

    _app = WidgetApp(qapp)  # noqa: F841 — held alive by the event loop
    return qapp.exec()


if __name__ == "__main__":
    sys.exit(main())
