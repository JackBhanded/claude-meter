"""Cost estimation.

The Anthropic API doesn't return *dollar* usage — only utilization fractions
against opaque rolling-window caps. We estimate cost by:

  1. Approximating the rolling-window token cap for the user's plan.
  2. Multiplying ``utilization * cap_tokens`` to get an estimated token spend.
  3. Multiplying by a blended price (we don't know which model was used) —
     defaulting to the Sonnet price as the most common workhorse.

This is a **rough** number. The tooltip labels it "approx" and explains the
assumption. Better numbers would require Anthropic to expose token counters
directly.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


PlanName = Literal["pro", "max_5x", "max_20x", "api_only", "unknown"]


@dataclass(frozen=True)
class ModelPrice:
    name: str
    input_per_mtok: float   # USD per million input tokens
    output_per_mtok: float  # USD per million output tokens

    def blended_per_mtok(self, output_ratio: float = 0.25) -> float:
        """Cost of one million tokens at a given output-share."""
        return (
            self.input_per_mtok * (1 - output_ratio)
            + self.output_per_mtok * output_ratio
        )


# Per-million-token public pricing, USD, May 2026.
# Sources: platform.claude.com/docs/en/about-claude/pricing
PRICES: dict[str, ModelPrice] = {
    "opus-4.6":   ModelPrice("Claude Opus 4.6",   5.0,  25.0),
    "sonnet-4.6": ModelPrice("Claude Sonnet 4.6", 3.0,  15.0),
    "haiku-4.5":  ModelPrice("Claude Haiku 4.5",  1.0,   5.0),
}

# Approximate rolling-window TOKEN caps by plan. These are not published by
# Anthropic; community reverse-engineered values circa late 2025 / early 2026.
# We treat these as ballpark and clearly label the estimate as "approx".
# Numbers stored as (5h tokens, 7d tokens, 7d Opus tokens).
PLAN_CAPS: dict[PlanName, tuple[int, int, int]] = {
    # Pro: ~45 messages / 5h ≈ ~225k tokens / 5h ; weekly ~ 7M ; no Opus access.
    "pro":      (   225_000,  7_000_000,           0),
    # Max 5x: 5h ~1.125M, weekly ~35M, weekly Opus ~5M.
    "max_5x":   ( 1_125_000, 35_000_000,   5_000_000),
    # Max 20x: 5h ~4.5M, weekly ~140M, weekly Opus ~20M.
    "max_20x":  ( 4_500_000,140_000_000,  20_000_000),
    "api_only": (         0,          0,           0),
    "unknown":  ( 1_125_000, 35_000_000,   5_000_000),  # assume Max 5x baseline
}


def estimate_cost_usd(
    utilization: float,
    window: str,
    plan: PlanName = "unknown",
    model_key: str = "sonnet-4.6",
    output_ratio: float = 0.25,
) -> float:
    """Estimate dollar cost of the consumed portion of a rolling window."""
    caps_5h, caps_7d, caps_opus = PLAN_CAPS.get(plan, PLAN_CAPS["unknown"])
    if window == "5h":
        tokens = utilization * caps_5h
    elif window == "7d":
        tokens = utilization * caps_7d
    elif window == "7d_opus":
        tokens = utilization * caps_opus
        model_key = "opus-4.6"
    else:
        return 0.0
    price = PRICES.get(model_key, PRICES["sonnet-4.6"])
    return (tokens / 1_000_000.0) * price.blended_per_mtok(output_ratio)


def format_usd(amount: float) -> str:
    if amount >= 1000:
        return f"${amount:,.0f}"
    if amount >= 10:
        return f"${amount:,.1f}"
    if amount >= 1:
        return f"${amount:,.2f}"
    return f"${amount:.2f}"
