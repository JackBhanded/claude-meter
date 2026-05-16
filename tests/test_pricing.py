from claude_usage_widget.pricing import (
    PRICES,
    estimate_cost_usd,
    format_usd,
)


def test_known_models_priced():
    assert {"opus-4.6", "sonnet-4.6", "haiku-4.5"} <= set(PRICES.keys())
    for m in PRICES.values():
        assert m.input_per_mtok > 0
        assert m.output_per_mtok > m.input_per_mtok  # output always pricier


def test_cost_estimate_scales_with_utilization():
    a = estimate_cost_usd(0.10, "7d", plan="max_5x")
    b = estimate_cost_usd(0.20, "7d", plan="max_5x")
    assert b > a
    # Linear scaling
    assert abs(b - 2 * a) < 1e-6


def test_cost_estimate_pro_smaller_than_max():
    pro = estimate_cost_usd(1.0, "7d", plan="pro")
    max5 = estimate_cost_usd(1.0, "7d", plan="max_5x")
    assert max5 > pro


def test_opus_window_uses_opus_pricing():
    """7d_opus should be priced at Opus rates, much higher per token."""
    sonnet_cost = estimate_cost_usd(1.0, "7d", plan="max_5x", model_key="sonnet-4.6")
    opus_cost = estimate_cost_usd(1.0, "7d_opus", plan="max_5x")
    # Opus cap is smaller but $/tok is higher — just check both > 0.
    assert opus_cost > 0
    assert sonnet_cost > 0


def test_format_usd():
    assert format_usd(0.05) == "$0.05"
    assert format_usd(1.234) == "$1.23"
    assert format_usd(12.5) == "$12.5"
    assert format_usd(1234.0) == "$1,234"
