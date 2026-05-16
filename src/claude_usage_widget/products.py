"""Local detection of installed Anthropic / Claude products.

The Anthropic API does NOT split usage by which client (Claude Code, Claude
desktop, Claude in Chrome, Cowork, …) made the request — they all roll into
one account quota. So we can't show per-product usage; what we *can* show is
which products are present on the machine, as informational context.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DetectedProduct:
    key: str
    label: str
    location: str
    detail: str = ""


def detect_all() -> list[DetectedProduct]:
    out: list[DetectedProduct] = []
    out.extend(_detect_claude_code())
    out.extend(_detect_claude_desktop())
    out.extend(_detect_cowork())
    out.extend(_detect_codex_cli())
    out.extend(_detect_chrome_extensions())
    return out


# ---------------------------------------------------------------------------

def _detect_claude_code() -> list[DetectedProduct]:
    found: list[DetectedProduct] = []
    home = os.environ.get("USERPROFILE")
    if home:
        creds = Path(home) / ".claude" / ".credentials.json"
        if creds.is_file():
            found.append(DetectedProduct(
                key="claude-code-win",
                label="Claude Code (Windows)",
                location=str(creds.parent),
                detail="OAuth credentials present",
            ))
    # WSL discovery happens via credentials.py; products.py just notes that
    # if WSL credentials existed, the tooltip will say so via the Sources line.
    return found


def _detect_claude_desktop() -> list[DetectedProduct]:
    """Claude desktop app — installed under ``%LOCALAPPDATA%\\Programs\\Claude\\``."""
    local = os.environ.get("LOCALAPPDATA")
    if not local:
        return []
    install = Path(local) / "Programs" / "Claude"
    if not install.exists():
        return []
    exe = install / "claude.exe"
    return [DetectedProduct(
        key="claude-desktop",
        label="Claude desktop app",
        location=str(install),
        detail="found" if exe.exists() else "install dir found",
    )]


def _detect_cowork() -> list[DetectedProduct]:
    appdata = os.environ.get("APPDATA")
    if not appdata:
        return []
    cowork = Path(appdata) / "Claude" / "local-agent-mode-sessions"
    if not cowork.exists():
        return []
    return [DetectedProduct(
        key="cowork",
        label="Cowork (Claude desktop)",
        location=str(cowork.parent),
        detail="session data present",
    )]


def _detect_codex_cli() -> list[DetectedProduct]:
    home = os.environ.get("USERPROFILE")
    if not home:
        return []
    auth = Path(home) / ".codex" / "auth.json"
    if not auth.is_file():
        return []
    return [DetectedProduct(
        key="codex-cli",
        label="OpenAI Codex CLI",
        location=str(auth.parent),
        detail="(not a Claude product — usage tracked separately)",
    )]


def _detect_chrome_extensions() -> list[DetectedProduct]:
    """Best-effort: look for the Claude Chrome extension dir."""
    local = os.environ.get("LOCALAPPDATA")
    if not local:
        return []
    chrome_ext = Path(local) / "Google" / "Chrome" / "User Data" / "Default" / "Extensions"
    if not chrome_ext.exists():
        return []
    # We don't know the extension ID stably; this is an informational hint only.
    return [DetectedProduct(
        key="chrome",
        label="Chrome (extensions dir)",
        location=str(chrome_ext),
        detail="Claude-in-Chrome may be installed; usage shares the same quota",
    )]
