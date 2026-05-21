"""Credential discovery.

Looks for an OAuth access token written by Claude Code CLI (preferred) and
falls back to a manually-entered API key in settings or the ANTHROPIC_API_KEY
environment variable.

Order of preference (first hit wins):
    1. ``%USERPROFILE%\\.claude\\.credentials.json`` (Windows-native Claude Code)
    2. ``\\\\wsl$\\<distro>\\home\\<user>\\.claude\\.credentials.json``
       (the WSL distros, queried via wsl.exe)
    3. ``settings.json`` -> ``manual_api_key`` (set by the Settings dialog)
    4. ``ANTHROPIC_API_KEY`` environment variable
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional


# Windows: prevent wsl.exe (or any other subprocess) from flashing a black
# console window when invoked from pythonw.exe / a frozen no-console exe.
_SUBPROCESS_FLAGS = (
    subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
)


@dataclass(frozen=True)
class Credential:
    """A resolved credential ready to authenticate against ``api.anthropic.com``."""

    kind: str               # "oauth" | "api_key"
    token: str              # bearer token or sk-ant-api... key
    source: str             # human-readable description for the tooltip
    expires_at_ms: Optional[int] = None  # only set for OAuth

    @property
    def is_expired(self) -> bool:
        if self.expires_at_ms is None:
            return False
        # 30 s leeway — refresh handled by the Claude Code CLI itself, but if
        # we somehow read a token within seconds of expiry treat it as stale.
        return (self.expires_at_ms / 1000.0) <= (time.time() + 30)


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------

def discover(manual_api_key: Optional[str] = None) -> Optional[Credential]:
    """Return the best credential available, or ``None`` if nothing found."""
    for cred in _iter_candidates(manual_api_key):
        if not cred.is_expired:
            return cred
    # Even an expired OAuth token is better than no info — the call will 401
    # and the UI will tell the user to re-login.
    for cred in _iter_candidates(manual_api_key):
        return cred
    return None


def _iter_candidates(manual_api_key: Optional[str]) -> Iterable[Credential]:
    """Yield credential candidates in priority order."""
    cred = _try_windows_claude_code()
    if cred:
        yield cred

    for cred in _try_wsl_claude_code():
        yield cred

    if manual_api_key:
        yield Credential(kind="api_key", token=manual_api_key, source="Settings (manual)")

    env_key = os.environ.get("ANTHROPIC_API_KEY")
    if env_key:
        yield Credential(kind="api_key", token=env_key, source="$ANTHROPIC_API_KEY")


# ---------------------------------------------------------------------------
# Windows-side discovery
# ---------------------------------------------------------------------------

def _try_windows_claude_code() -> Optional[Credential]:
    home = os.environ.get("USERPROFILE")
    if not home:
        return None
    path = Path(home) / ".claude" / ".credentials.json"
    return _parse_claude_credentials_file(path, source=f"Windows: {path}")


def _parse_claude_credentials_file(path: Path, source: str) -> Optional[Credential]:
    try:
        if not path.is_file():
            return None
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (OSError, json.JSONDecodeError):
        return None

    oauth = data.get("claudeAiOauth") or {}
    access = oauth.get("accessToken")
    if not access:
        return None
    return Credential(
        kind="oauth",
        token=access,
        source=source,
        expires_at_ms=oauth.get("expiresAt"),
    )


# ---------------------------------------------------------------------------
# WSL-side discovery
# ---------------------------------------------------------------------------

def _try_wsl_claude_code() -> Iterable[Credential]:
    """If WSL is installed, ``cat`` the credentials file via ``wsl.exe``."""
    if os.name != "nt":
        return  # only meaningful on Windows
    wsl_exe = _find_wsl_exe()
    if not wsl_exe:
        return

    for distro in _list_wsl_distros(wsl_exe):
        contents = _wsl_read(wsl_exe, distro, "~/.claude/.credentials.json")
        if not contents:
            continue
        try:
            data = json.loads(contents)
        except json.JSONDecodeError:
            continue
        oauth = data.get("claudeAiOauth") or {}
        access = oauth.get("accessToken")
        if not access:
            continue
        yield Credential(
            kind="oauth",
            token=access,
            source=f"WSL {distro}: ~/.claude/.credentials.json",
            expires_at_ms=oauth.get("expiresAt"),
        )


def _find_wsl_exe() -> Optional[str]:
    # %SystemRoot%\System32\wsl.exe is the canonical location.
    sysroot = os.environ.get("SystemRoot") or r"C:\Windows"
    candidate = Path(sysroot) / "System32" / "wsl.exe"
    return str(candidate) if candidate.exists() else None


def _list_wsl_distros(wsl_exe: str) -> list[str]:
    try:
        # ``wsl -l -q`` lists installed distros, one per line, in UTF-16LE.
        out = subprocess.run(
            [wsl_exe, "-l", "-q"],
            capture_output=True,
            timeout=5,
            check=False,
            creationflags=_SUBPROCESS_FLAGS,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    raw = out.stdout
    text = _decode_wsl_output(raw)
    return [line.strip() for line in text.splitlines() if line.strip()]


def _wsl_read(wsl_exe: str, distro: str, posix_path: str) -> Optional[str]:
    try:
        out = subprocess.run(
            [wsl_exe, "-d", distro, "--", "cat", posix_path],
            capture_output=True,
            timeout=5,
            check=False,
            creationflags=_SUBPROCESS_FLAGS,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    return _decode_wsl_output(out.stdout)


def _decode_wsl_output(raw: bytes) -> str:
    """``wsl.exe`` emits UTF-16LE on some Windows builds and UTF-8 on others."""
    if not raw:
        return ""
    # UTF-16LE BOM detection
    if raw[:2] == b"\xff\xfe":
        return raw[2:].decode("utf-16-le", errors="replace")
    # Heuristic: lots of NUL bytes between ascii bytes => UTF-16LE
    if raw.count(b"\x00") > len(raw) // 3:
        return raw.decode("utf-16-le", errors="replace")
    return raw.decode("utf-8", errors="replace")
