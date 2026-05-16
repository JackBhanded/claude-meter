from datetime import datetime, timedelta, timezone

from claude_usage_widget.notifications import ThresholdNotifier


def test_threshold_fires_once_per_cycle():
    n = ThresholdNotifier([0.75, 0.90, 0.95])
    reset = datetime(2026, 5, 19, tzinfo=timezone.utc)
    # Below all thresholds.
    assert n.check("7d", 0.5, reset) == []
    # Cross 0.75.
    assert n.check("7d", 0.78, reset) == [0.75]
    # Same level, should NOT re-fire.
    assert n.check("7d", 0.79, reset) == []
    # Cross 0.90 & 0.95 together.
    assert n.check("7d", 0.96, reset) == [0.90, 0.95]


def test_new_cycle_resets_state():
    n = ThresholdNotifier([0.75])
    r1 = datetime(2026, 5, 19, tzinfo=timezone.utc)
    r2 = r1 + timedelta(days=7)
    assert n.check("7d", 0.8, r1) == [0.75]
    # Same reset_at, no re-fire.
    assert n.check("7d", 0.8, r1) == []
    # New reset_at → re-fire.
    assert n.check("7d", 0.8, r2) == [0.75]


def test_independent_windows():
    n = ThresholdNotifier([0.5])
    r = datetime(2026, 5, 19, tzinfo=timezone.utc)
    assert n.check("5h", 0.6, r) == [0.5]
    # 7d should fire independently.
    assert n.check("7d", 0.6, r) == [0.5]
