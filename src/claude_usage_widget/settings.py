"""Persisted user settings stored as JSON in %APPDATA%."""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class Settings:
    # Polling. 0 = let the poller pick adaptively (5/7/20 min). Set to a
    # positive number to force a fixed interval.
    refresh_seconds: int = 0
    # Manual override credential (if user doesn't have Claude Code installed)
    manual_api_key: Optional[str] = None
    # Plan declaration (used for cost approximation)
    plan: str = "unknown"  # "pro" | "max_5x" | "max_20x" | "api_only" | "unknown"
    # Notifications
    notify_at_thresholds: list[float] = field(default_factory=lambda: [0.75, 0.90, 0.95])
    notifications_enabled: bool = True
    # UI behaviour
    # Off by default — only triggers for true fullscreen (no title bar),
    # not for maximized normal windows. Opt-in via Settings.
    hide_when_fullscreen: bool = False
    theme: str = "auto"  # "auto" | "light" | "dark"
    # Position offset from bottom-right of primary screen (pixels)
    pos_offset_right: int = 220
    pos_offset_bottom: int = 6
    # Glass / opacity
    opacity: float = 0.92                  # whole-window opacity (0.5 = very translucent, 1.0 = solid)
    enable_glass_backdrop: bool = True     # request Win11 Acrylic backdrop (graceful fallback)
    # Snooze duration in minutes for the right-click "Hide for N min" action.
    snooze_minutes: int = 15


def settings_path() -> Path:
    base = os.environ.get("APPDATA")
    if base:
        return Path(base) / "ClaudeMeter" / "settings.json"
    return Path.home() / ".claude_meter" / "settings.json"


def load() -> Settings:
    p = settings_path()
    try:
        raw = p.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (OSError, json.JSONDecodeError):
        return Settings()
    s = Settings()
    for k, v in data.items():
        if hasattr(s, k):
            setattr(s, k, v)
    return s


def save(s: Settings) -> None:
    p = settings_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(asdict(s), indent=2), encoding="utf-8")
