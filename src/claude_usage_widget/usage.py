"""Talk to ``api.anthropic.com/api/oauth/usage`` and parse the JSON it returns.

This is the same data the ``claude.ai/settings/usage`` page displays — plan
name, current session %, weekly per-model breakdowns (All models, Sonnet
only, Opus only, Claude Design, …), overage spend, and daily routine runs.

Auth: ``Authorization: Bearer <accessToken>`` from
``~/.claude/.credentials.json``, plus ``anthropic-beta: oauth-2025-04-20``.

WARNING — this endpoint rate-limits aggressively. Poll **slowly** (default
7 minutes) and back off on 429 responses. See ``poller.py`` for the
scheduling logic.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

import requests

from .credentials import Credential


USAGE_URL = "https://api.anthropic.com/api/oauth/usage"
ANTHROPIC_VERSION = "2023-06-01"
ANTHROPIC_BETA_OAUTH = "oauth-2025-04-20"
USER_AGENT = "claude-code/1.0 (claude-usage-widget)"


# Known top-level keys mapped to friendly labels (shown in tooltip / widget).
# Anything not in this map is shown with an auto-humanised label.
#
# "seven_day_omelette" is the internal Anthropic codename for the Claude
# Design quota (confirmed by inspecting the real /api/oauth/usage response).
# Both keys map to the same user-facing label so we render correctly whether
# Anthropic ships the codename or eventually renames it.
KNOWN_QUOTA_LABELS: dict[str, str] = {
    "five_hour":                 "Current session",
    "seven_day":                 "Weekly · All models",
    "seven_day_sonnet":          "Weekly · Sonnet only",
    "seven_day_opus":            "Weekly · Opus only",
    "seven_day_haiku":           "Weekly · Haiku only",
    "seven_day_claude_design":   "Weekly · Claude Design",
    "seven_day_omelette":        "Weekly · Claude Design",   # internal codename
    "seven_day_skills":          "Weekly · Skills",
    "seven_day_agents":          "Weekly · Agents",
}

# Display order — known keys first, in this order, then any unknown ones.
KNOWN_QUOTA_ORDER = [
    "five_hour",
    "seven_day",
    "seven_day_sonnet",
    "seven_day_opus",
    "seven_day_haiku",
    "seven_day_claude_design",
    "seven_day_omelette",
    "seven_day_skills",
    "seven_day_agents",
]


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Quota:
    """One named quota row (a percentage-based limit)."""
    key: str                          # raw API key e.g. "seven_day_sonnet"
    label: str                        # friendly label e.g. "Weekly · Sonnet only"
    utilization: float                # 0.0 .. 1.0+
    resets_at: Optional[datetime]     # UTC
    raw: dict = field(default_factory=dict)

    @property
    def percent(self) -> float:
        return self.utilization * 100.0


@dataclass(frozen=True)
class CountQuota:
    """A used / limit pair (e.g. daily routine runs 0 / 15)."""
    key: str
    label: str
    used: int
    limit: int
    resets_at: Optional[datetime] = None

    @property
    def utilization(self) -> float:
        return 0.0 if self.limit <= 0 else min(1.0, self.used / self.limit)


@dataclass(frozen=True)
class Overage:
    """Pay-as-you-go extra usage on top of subscription."""
    current_usd: float
    budget_usd: float

    @property
    def utilization(self) -> float:
        return 0.0 if self.budget_usd <= 0 else min(1.0, self.current_usd / self.budget_usd)


@dataclass
class UsageSnapshot:
    """The result of one /api/oauth/usage call."""
    ok: bool = False
    error: Optional[str] = None
    retry_after_s: Optional[int] = None
    fetched_at: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))
    plan: Optional[str] = None        # e.g. "Max 5x" — populated if API exposes it
    quotas: list[Quota] = field(default_factory=list)
    count_quotas: list[CountQuota] = field(default_factory=list)
    overage: Optional[Overage] = None
    raw: dict = field(default_factory=dict)
    credential_source: Optional[str] = None
    credential_kind: Optional[str] = None  # "oauth" | "api_key"

    def by_key(self, key: str) -> Optional[Quota]:
        for q in self.quotas:
            if q.key == key:
                return q
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def probe(credential: Credential, timeout: float = 10.0) -> UsageSnapshot:
    """Fetch the usage payload. Never raises — failures land in ``error``."""
    snap = UsageSnapshot(
        ok=False,
        credential_source=credential.source,
        credential_kind=credential.kind,
    )
    if credential.kind != "oauth":
        snap.error = (
            "This endpoint requires an OAuth token (Claude Code credentials). "
            "Plain API keys can't see the per-model breakdown."
        )
        return snap

    headers = {
        "authorization": f"Bearer {credential.token}",
        "anthropic-version": ANTHROPIC_VERSION,
        "anthropic-beta": ANTHROPIC_BETA_OAUTH,
        "user-agent": USER_AGENT,
        "accept": "application/json",
    }
    try:
        resp = requests.get(USAGE_URL, headers=headers, timeout=timeout)
    except requests.RequestException as exc:
        snap.error = f"Network error: {exc.__class__.__name__}"
        return snap

    # Honour Retry-After even on 4xx so the poller can back off correctly.
    ra = resp.headers.get("retry-after")
    if ra is not None:
        try:
            snap.retry_after_s = int(ra)
        except ValueError:
            snap.retry_after_s = None

    if resp.status_code == 401:
        snap.error = "Auth failed — token may be expired. Re-login with `claude` CLI."
        return snap
    if resp.status_code == 429:
        snap.error = "Rate-limited by Anthropic. Slowing down…"
        return snap
    if not (200 <= resp.status_code < 300):
        snap.error = f"HTTP {resp.status_code}: {_short_body(resp)}"
        return snap

    try:
        body = resp.json()
    except ValueError:
        snap.error = "Response was not JSON"
        return snap

    snap.raw = body if isinstance(body, dict) else {}
    parse_into(snap, snap.raw)
    snap.ok = True
    return snap


# ---------------------------------------------------------------------------
# Parsing — split out so tests can drive it without HTTP
# ---------------------------------------------------------------------------

def parse_into(snap: UsageSnapshot, body: dict) -> None:
    quotas: list[Quota] = []
    seen_keys: set[str] = set()

    # The API has been observed in both shapes: 0–1 fractions AND 0–100
    # percentages. The screenshot Jack showed (and most third-party code)
    # has 0–100 percentages. We pick the scale by scanning the whole
    # response first: if *any* utilization value is greater than 1.5, we
    # treat the whole response as 0–100 percentages. Otherwise we trust
    # them as 0–1 fractions. This avoids mis-reading "1%" as "100%".
    is_percent_scale = _detect_percent_scale(body)
    scale = 0.01 if is_percent_scale else 1.0

    def consider(key: str, value) -> None:
        if not isinstance(value, dict):
            return
        util = _first_numeric(value, ("utilization", "utilization_pct", "used_percentage"))
        if util is None:
            return
        resets = _parse_iso(
            value.get("resets_at") or value.get("reset_at") or value.get("reset")
        )
        quotas.append(Quota(
            key=key,
            label=_label_for(key),
            utilization=float(util) * scale,
            resets_at=resets,
            raw=value,
        ))
        seen_keys.add(key)

    # Ordered known keys first.
    for key in KNOWN_QUOTA_ORDER:
        if key in body:
            consider(key, body[key])

    # Then anything else that walks like a utilization row.
    for key, value in body.items():
        if key in seen_keys or not isinstance(value, dict):
            continue
        # Skip the well-known non-utilization sections we handle below.
        if key in ("extra_usage", "daily_routine_runs", "plan"):
            continue
        consider(key, value)

    snap.quotas = quotas

    # Plan name — best-effort.
    plan_raw = body.get("plan") or body.get("subscription") or body.get("plan_name")
    if isinstance(plan_raw, dict):
        plan_raw = plan_raw.get("name") or plan_raw.get("display_name")
    if isinstance(plan_raw, str):
        snap.plan = plan_raw

    # Overage / extra usage.
    extra = body.get("extra_usage")
    if isinstance(extra, dict):
        cur = _first_numeric(extra, ("current_spending", "current_spend", "spent", "current_usd"))
        bud = _first_numeric(extra, ("budget_limit", "budget", "limit", "budget_usd"))
        if cur is not None and bud is not None:
            snap.overage = Overage(current_usd=float(cur), budget_usd=float(bud))

    # Count-based rows: daily routine runs, anything with used/limit pair.
    count_quotas: list[CountQuota] = []
    for key, value in body.items():
        if not isinstance(value, dict):
            continue
        used = _first_numeric(value, ("used", "count", "consumed"))
        limit = _first_numeric(value, ("limit", "cap", "total"))
        # Only treat as a count if there's a hard integer limit AND no
        # utilization (otherwise we'd double-count the percentage quotas).
        if used is None or limit is None or limit <= 0:
            continue
        if any(k in value for k in ("utilization", "utilization_pct", "used_percentage")):
            continue
        count_quotas.append(CountQuota(
            key=key,
            label=_label_for(key),
            used=int(used),
            limit=int(limit),
            resets_at=_parse_iso(value.get("resets_at") or value.get("reset_at")),
        ))
    snap.count_quotas = count_quotas


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _detect_percent_scale(body: dict) -> bool:
    """Return True if *any* utilization value in the body exceeds 1.5,
    which means the API is using 0–100 percentages rather than 0–1 fractions.

    Conservative — if everything looks <= 1.5 we assume fractions. This
    matters most when the API returns small values like 8 (8%): we need
    at least one bigger row to disambiguate.
    """
    for value in body.values():
        if not isinstance(value, dict):
            continue
        v = _first_numeric(value, ("utilization", "utilization_pct", "used_percentage"))
        if v is not None and v > 1.5:
            return True
    return False


def _label_for(key: str) -> str:
    if key in KNOWN_QUOTA_LABELS:
        return KNOWN_QUOTA_LABELS[key]
    # Humanise: "daily_routine_runs" → "Daily routine runs"
    return key.replace("_", " ").strip().capitalize()


def _parse_iso(text) -> Optional[datetime]:
    if not isinstance(text, str) or not text:
        return None
    t = text.strip()
    if t.endswith("Z"):
        t = t[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(t)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _first_numeric(d: dict, keys: tuple[str, ...]):
    for k in keys:
        if k not in d:
            continue
        v = d[k]
        if isinstance(v, (int, float)):
            return v
        if isinstance(v, str):
            try:
                return float(v)
            except ValueError:
                continue
    return None


def _short_body(resp: requests.Response) -> str:
    try:
        body = resp.json()
        msg = (body.get("error") or {}).get("message") if isinstance(body, dict) else None
        return msg or resp.text[:200]
    except ValueError:
        return resp.text[:200]
