"""Color palette — light mode, Claude brand.

Sourced from the public claude.ai visual identity: warm cream surfaces, the
signature coral (#D97757) for brand accents, deep warm gray text. Status
colors are tuned to the same warm temperature so the green/amber/red ramp
doesn't clash with the cream surrounding it.
"""
from __future__ import annotations

from PySide6.QtGui import QColor


# Brand
BRAND_CORAL = "#D97757"        # the Claude mark color
BRAND_CORAL_LIGHT = "#E8A98E"
BRAND_CORAL_DARK = "#B85838"

# Surfaces
SURFACE_BG = "#FAF9F5"         # claude.ai background
SURFACE_BG_RGBA = (250, 249, 245, 248)  # for always-on-top translucent panels
SURFACE_PANEL = "#F5F4EE"
SURFACE_WHITE = "#FFFFFF"

# Borders
BORDER = "#E5E2DA"
BORDER_STRONG = "#C9C5BC"

# Text
TEXT_PRIMARY = "#1F1F1F"       # near-black, warm
TEXT_SECONDARY = "#5C5A56"     # warm dark gray
TEXT_TERTIARY = "#8A8780"      # warm mid gray
TEXT_DIM = "#A29F98"           # for hint / footnote text

# Track/bar background (the "unfilled" portion of progress bars)
TRACK = "#ECE9E1"


def util_color(utilization: float) -> QColor:
    """Status ramp — three crisp tiers, matching the claude.ai usage page.

      0–49%   blue    — informational, no concern
      50–79%  orange  — getting warm
      80%+    red     — actually concerning
    """
    u = max(0.0, min(1.0, utilization))
    if u < 0.50:
        return QColor("#2563EB")   # blue (claude.ai usage-page blue)
    if u < 0.80:
        return QColor("#EA580C")   # orange
    return QColor("#DC2626")       # red


def util_color_hex(utilization: float) -> str:
    return util_color(utilization).name()


def is_dark_mode() -> bool:
    """Detect Windows dark/light mode. We DON'T respond to this in v0.1 —
    the widget is always in light/Claude mode — but the helper is here for
    future use."""
    try:
        import winreg  # type: ignore

        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
        ) as key:
            value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        return value == 0
    except Exception:
        return False
