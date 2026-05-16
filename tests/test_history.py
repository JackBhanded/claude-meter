from datetime import datetime, timedelta, timezone

from claude_usage_widget import history


def test_append_and_load(tmp_path):
    p = tmp_path / "history.json"
    history.append(0.1, 0.2, None, path=p, now=datetime(2026, 5, 14, 10, 0, 0, tzinfo=timezone.utc))
    history.append(0.15, 0.25, 0.05, path=p, now=datetime(2026, 5, 14, 10, 5, 0, tzinfo=timezone.utc))
    history.append(0.3, 0.4, 0.1, path=p, now=datetime(2026, 5, 14, 10, 20, 0, tzinfo=timezone.utc))

    buckets = history.load(p)
    assert len(buckets) == 2  # 10:00 and 10:20 buckets (10:05 collapsed into 10:00)
    # First bucket should have taken the higher utilization (0.15 > 0.1).
    assert buckets[0].u5h == 0.15
    assert buckets[0].u7d == 0.25


def test_trim_after_14_days(tmp_path):
    p = tmp_path / "history.json"
    old = datetime(2026, 5, 1, 0, 0, 0, tzinfo=timezone.utc)
    history.append(0.1, 0.2, None, path=p, now=old)
    new = datetime(2026, 5, 20, 0, 0, 0, tzinfo=timezone.utc)
    history.append(0.3, 0.4, None, path=p, now=new)
    buckets = history.load(p)
    # Only the new bucket survives (old one is > 14 days behind).
    assert len(buckets) == 1
    assert buckets[0].u5h == 0.3


def test_sparkline_series_filters_none():
    buckets = [
        history.Bucket(t="t1", u5h=None),
        history.Bucket(t="t2", u5h=0.1),
        history.Bucket(t="t3", u5h=0.2),
    ]
    series = history.sparkline_series(buckets, "u5h")
    assert series == [0.1, 0.2]
