"""Entry point.

Works both as ``python -m claude_usage_widget`` (development) and as a
frozen .exe produced by PyInstaller. The absolute import is intentional —
PyInstaller invokes this file directly without package context, so a
relative ``from .main import main`` would raise ImportError.
"""
import sys

if __name__ == "__main__":
    from claude_usage_widget.main import main
    sys.exit(main())
