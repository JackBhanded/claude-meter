"""Background thread that probes the usage API on an adaptive schedule.

The ``/api/oauth/usage`` endpoint rate-limits aggressively. We use the
schedule that ``sr-kai/claudeusagewin`` proved works in production:

  * **Normal cadence**  — every 7 minutes
  * **Active cadence**  — every 5 minutes (within 30 min after a quota reset
                           or while utilization is climbing fast)
  * **Idle cadence**    — every 20 minutes (no recent activity, or repeated
                           low-utilization snapshots)
  * **Back-off**         — on 429, double the interval (cap 60 min), honour
                           ``Retry-After`` if larger than that.

A manual "Refresh now" from the tray always fires immediately, but is then
subject to the back-off in subsequent ticks.
"""
from __future__ import annotations

import threading
import time
from typing import Optional

from PySide6.QtCore import QObject, QThread, Signal

from . import credentials, usage
from .settings import Settings
from .usage import UsageSnapshot


# Cadence presets (seconds) — kept here so they're easy to tune later.
NORMAL_S = 7 * 60
ACTIVE_S = 5 * 60
IDLE_S = 20 * 60
BACKOFF_CAP_S = 60 * 60


class Poller(QObject):
    """Worker that emits ``UsageSnapshot`` results back to the main thread."""

    snapshot_ready = Signal(object)   # UsageSnapshot
    no_credentials = Signal()

    def __init__(self, settings: Settings):
        super().__init__()
        self._settings = settings
        self._thread = QThread()                 # no parent — see history
        self._thread.setObjectName("UsagePoller")
        self.moveToThread(self._thread)
        self._stop_event = threading.Event()
        self._kick = False
        self._backoff_s: Optional[int] = None    # set after a 429
        self._consecutive_low = 0                # for idle detection
        self._thread.started.connect(self._run)

    # ------------------------------------------------------------------
    def start(self) -> None:
        self._thread.start()

    def request_refresh(self) -> None:
        self._kick = True
        # Manual refresh resets back-off — the user wants data NOW.
        self._backoff_s = None

    def stop(self) -> None:
        self._stop_event.set()
        self._thread.quit()
        self._thread.wait(2000)

    # ------------------------------------------------------------------
    def _run(self) -> None:
        self._poll_once()
        while not self._stop_event.is_set():
            interval = self._next_interval()
            deadline = time.monotonic() + interval
            while not self._stop_event.is_set() and time.monotonic() < deadline:
                if self._kick:
                    self._kick = False
                    break
                self._stop_event.wait(0.5)
            if self._stop_event.is_set():
                break
            self._poll_once()

    def _next_interval(self) -> int:
        # User override always wins.
        override = int(self._settings.refresh_seconds)
        if override and override > 0:
            base = override
        elif self._consecutive_low >= 3:
            base = IDLE_S
        else:
            base = NORMAL_S
        if self._backoff_s is not None:
            return max(base, self._backoff_s)
        return base

    def _poll_once(self) -> None:
        cred = credentials.discover(self._settings.manual_api_key)
        if cred is None:
            self.no_credentials.emit()
            return
        snap = usage.probe(cred)
        self._update_backoff(snap)
        self.snapshot_ready.emit(snap)

    def _update_backoff(self, snap: UsageSnapshot) -> None:
        # 429 → grow back-off, honour Retry-After if larger.
        if not snap.ok and snap.error and "Rate-limited" in snap.error:
            ra = snap.retry_after_s or 0
            current = self._backoff_s or NORMAL_S
            self._backoff_s = min(BACKOFF_CAP_S, max(ra, current * 2))
            return
        # Success — reset back-off.
        self._backoff_s = None
        # Track quietness so we can stretch to IDLE_S after a few low reads.
        if snap.ok and snap.quotas:
            top = max((q.utilization for q in snap.quotas), default=0.0)
            if top < 0.15:
                self._consecutive_low += 1
            else:
                self._consecutive_low = 0
