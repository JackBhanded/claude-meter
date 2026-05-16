"""JSON-parsing tests for the /api/oauth/usage response — no network."""
from __future__ import annotations

from datetime import timezone

from claude_usage_widget.usage import UsageSnapshot, parse_into


# A representative payload modelled on the verified shape from third-party
# implementations. Newer fields (Claude Design, routine runs) are included
# defensively so the parser handles them when the API starts returning them.
FIXTURE = {
    "plan": "Max 5x",
    "five_hour":               {"utilization": 30, "resets_at": "2026-05-14T18:30:00Z"},
    "seven_day":               {"utilization":  7, "resets_at": "2026-05-19T13:30:00Z"},
    "seven_day_sonnet":        {"utilization":  8, "resets_at": "2026-05-19T13:30:00Z"},
    "seven_day_opus":          {"utilization":  0, "resets_at": "2026-05-19T13:30:00Z"},
    "seven_day_claude_design": {"utilization":  0, "resets_at": "2026-05-19T13:30:00Z"},
    "daily_routine_runs":      {"used": 0, "limit": 15, "resets_at": "2026-05-15T00:00:00Z"},
    "extra_usage":             {"current_spending": 3.5, "budget_limit": 50.0},
}


def test_parse_quotas_in_known_order():
    snap = UsageSnapshot()
    parse_into(snap, FIXTURE)
    keys = [q.key for q in snap.quotas]
    # five_hour first, seven_day second, then per-model rows
    assert keys.index("five_hour") < keys.index("seven_day")
    assert "seven_day_sonnet" in keys
    assert "seven_day_opus" in keys
    assert "seven_day_claude_design" in keys


def test_quota_labels_are_friendly():
    snap = UsageSnapshot()
    parse_into(snap, FIXTURE)
    labels = {q.key: q.label for q in snap.quotas}
    assert labels["five_hour"] == "Current session"
    assert labels["seven_day"] == "Weekly · All models"
    assert labels["seven_day_sonnet"] == "Weekly · Sonnet only"
    assert labels["seven_day_claude_design"] == "Weekly · Claude Design"


def test_percentage_normalization():
    """API may return 0-100 percentages OR 0-1 fractions. We normalise to 0-1."""
    snap = UsageSnapshot()
    parse_into(snap, FIXTURE)
    by = {q.key: q for q in snap.quotas}
    # 30% → 0.30
    assert abs(by["five_hour"].utilization - 0.30) < 1e-6
    # 8 → 0.08
    assert abs(by["seven_day_sonnet"].utilization - 0.08) < 1e-6


def test_percentage_normalization_fraction_form():
    """A response that already gives fractional values should pass through."""
    snap = UsageSnapshot()
    parse_into(snap, {"five_hour": {"utilization": 0.42}})
    assert snap.by_key("five_hour").utilization == 0.42


def test_reset_times_are_utc():
    snap = UsageSnapshot()
    parse_into(snap, FIXTURE)
    fh = snap.by_key("five_hour")
    assert fh.resets_at is not None
    assert fh.resets_at.tzinfo == timezone.utc


def test_plan_name_captured():
    snap = UsageSnapshot()
    parse_into(snap, FIXTURE)
    assert snap.plan == "Max 5x"


def test_overage_parsed():
    snap = UsageSnapshot()
    parse_into(snap, FIXTURE)
    assert snap.overage is not None
    assert snap.overage.current_usd == 3.5
    assert snap.overage.budget_usd == 50.0


def test_count_quotas_parsed():
    snap = UsageSnapshot()
    parse_into(snap, FIXTURE)
    keys = {cq.key for cq in snap.count_quotas}
    assert "daily_routine_runs" in keys


def test_unknown_keys_humanized():
    """A new field we've never seen before should still surface."""
    snap = UsageSnapshot()
    parse_into(snap, {"seven_day_something_new": {"utilization": 12, "resets_at": "2026-05-21T00:00:00Z"}})
    q = snap.by_key("seven_day_something_new")
    assert q is not None
    # Auto-humanised, not the raw key.
    assert "seven_day" in q.label.lower() or "something" in q.label.lower()


def test_no_quotas_when_response_unrelated():
    snap = UsageSnapshot()
    parse_into(snap, {"some_unrelated_field": "value"})
    assert snap.quotas == []
    assert snap.overage is None
    assert snap.count_quotas == []
