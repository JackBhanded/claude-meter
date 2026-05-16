"""Threshold toast notifications.

We track which thresholds have already fired *for the current reset cycle*,
so the user only gets one toast per window per cycle. The state is reset when
the window's ``reset_at`` advances.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class _CycleState:
    reset_at: Optional[datetime] = None
    fired: set[float] = field(default_factory=set)


class ThresholdNotifier:
    """Computes which threshold notifications should fire now.

    Pure logic — the actual ``ToastNotificationManager`` call happens in
    ``fire_toast`` so tests can drive ``check`` without a Windows runtime.
    """

    def __init__(self, thresholds: list[float]):
        self.thresholds = sorted(set(thresholds))
        self._state: dict[str, _CycleState] = {}

    def check(self, window: str, utilization: float, reset_at: Optional[datetime]) -> list[float]:
        """Return the list of thresholds that fired *this call*."""
        state = self._state.setdefault(window, _CycleState())
        # New cycle ⇒ wipe the fired set.
        if reset_at is not None and state.reset_at != reset_at:
            state.reset_at = reset_at
            state.fired = set()
        fired_now: list[float] = []
        for t in self.thresholds:
            if utilization >= t and t not in state.fired:
                state.fired.add(t)
                fired_now.append(t)
        return fired_now


def fire_toast(title: str, body: str) -> None:
    """Best-effort Windows toast. Silently no-ops if unsupported."""
    try:
        from win11toast import toast  # type: ignore

        toast(title, body, duration="short")
        return
    except Exception:
        pass
    try:
        # Older Win10 fallback.
        from win10toast import ToastNotifier  # type: ignore

        ToastNotifier().show_toast(title, body, duration=5, threaded=True)
        return
    except Exception:
        pass
    # If neither toast lib is installed, fall back to a console print so
    # at least dev-mode users see something.
    print(f"[notification] {title}: {body}")
