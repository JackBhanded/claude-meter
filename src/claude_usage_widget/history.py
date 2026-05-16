"""Append-only usage history kept on disk for the sparkline.

Layout: one JSON file at ``%APPDATA%\\ClaudeMeter\\history.json``
containing a list of 10-minute buckets, each:

    {"t": "<ISO 8601 UTC>", "u5h": 0.18, "u7d": 0.34, "uopus": 0.05}

Trimmed to the last 14 days on every write.
"""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable, Optional


BUCKET_MINUTES = 10
HISTORY_DAYS = 14


@dataclass
class Bucket:
    t: str               # ISO 8601 UTC
    u5h: Optional[float] = None
    u7d: Optional[float] = None
    uopus: Optional[float] = None


def history_path() -> Path:
    base = os.environ.get("APPDATA")
    if base:
        return Path(base) / "ClaudeMeter" / "history.json"
    # POSIX fallback (mainly for tests).
    return Path.home() / ".claude_meter" / "history.json"


def load(path: Optional[Path] = None) -> list[Bucket]:
    p = path or history_path()
    try:
        if not p.is_file():
            return []
        raw = p.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (OSError, json.JSONDecodeError):
        return []
    out: list[Bucket] = []
    for item in data:
        if not isinstance(item, dict) or "t" not in item:
            continue
        out.append(Bucket(
            t=str(item["t"]),
            u5h=_as_opt_float(item.get("u5h")),
            u7d=_as_opt_float(item.get("u7d")),
            uopus=_as_opt_float(item.get("uopus")),
        ))
    return out


def append(
    u5h: Optional[float],
    u7d: Optional[float],
    uopus: Optional[float],
    *,
    path: Optional[Path] = None,
    now: Optional[datetime] = None,
) -> list[Bucket]:
    """Add the current reading, collapsing into the open 10-minute bucket."""
    now = (now or datetime.now(tz=timezone.utc)).astimezone(timezone.utc)
    bucket_t = _bucket_start(now)
    p = path or history_path()
    p.parent.mkdir(parents=True, exist_ok=True)

    existing = load(p)
    bucket_iso = bucket_t.isoformat().replace("+00:00", "Z")

    # If the most recent bucket is the same as ``bucket_t`` we overwrite it
    # (highest reading wins — utilization is monotonically increasing within
    # a window between resets).
    if existing and existing[-1].t == bucket_iso:
        last = existing[-1]
        last.u5h = _max_opt(last.u5h, u5h)
        last.u7d = _max_opt(last.u7d, u7d)
        last.uopus = _max_opt(last.uopus, uopus)
    else:
        existing.append(Bucket(t=bucket_iso, u5h=u5h, u7d=u7d, uopus=uopus))

    trimmed = _trim(existing, now)
    p.write_text(
        json.dumps([asdict(b) for b in trimmed], separators=(",", ":")),
        encoding="utf-8",
    )
    return trimmed


def sparkline_series(
    buckets: Iterable[Bucket],
    field: str = "u5h",
    points: int = 96,
) -> list[float]:
    """Return the last ``points`` non-None values of the given field."""
    out: list[float] = []
    for b in buckets:
        v = getattr(b, field)
        if v is None:
            continue
        out.append(float(v))
    return out[-points:]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _bucket_start(now: datetime) -> datetime:
    minutes = (now.minute // BUCKET_MINUTES) * BUCKET_MINUTES
    return now.replace(minute=minutes, second=0, microsecond=0)


def _trim(buckets: list[Bucket], now: datetime) -> list[Bucket]:
    cutoff = now - timedelta(days=HISTORY_DAYS)
    cutoff_iso = cutoff.isoformat().replace("+00:00", "Z")
    return [b for b in buckets if b.t >= cutoff_iso]


def _as_opt_float(x) -> Optional[float]:
    if x is None:
        return None
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _max_opt(a: Optional[float], b: Optional[float]) -> Optional[float]:
    if a is None:
        return b
    if b is None:
        return a
    return max(a, b)
