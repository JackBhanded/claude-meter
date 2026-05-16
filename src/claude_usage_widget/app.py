"""High-level controller — glues tray, widget, poller, history, notifications.

When a probe comes back as an error (rate-limit / network / auth) we DON'T
wipe the widget; instead we keep the last successful snapshot on screen and
inject the new error into a copy of it so the widget can show a small
"couldn't refresh" indicator while the user still sees their data.
"""
from __future__ import annotations

import dataclasses
import sys
from typing import Optional

from PySide6.QtCore import QObject
from PySide6.QtWidgets import QApplication

from . import history, notifications, products, settings as settings_mod
from .poller import Poller
from .settings_dialog import SettingsDialog
from .tray import UsageTray
from .usage import UsageSnapshot
from .widget import UsageWidget


class WidgetApp(QObject):
    def __init__(self, qt_app: QApplication):
        super().__init__()
        self.qt_app = qt_app
        self.settings = settings_mod.load()
        self.history_buckets = history.load()
        self._last_good: Optional[UsageSnapshot] = None

        self.widget = UsageWidget(self.settings)
        self.tray = UsageTray(
            on_open=self._toggle_widget,
            on_refresh=self._force_refresh,
            on_settings=self._open_settings,
            on_quit=self._quit,
        )
        if not self.tray.isSystemTrayAvailable():
            print("Warning: no system tray on this desktop session.", file=sys.stderr)
        self.tray.show()
        self.widget.show()

        self.products = products.detect_all()
        self.widget.update_data(None, self.history_buckets, self.products)

        self.notifier = notifications.ThresholdNotifier(self.settings.notify_at_thresholds)

        self.poller = Poller(self.settings)
        self.poller.snapshot_ready.connect(self._on_snapshot)
        self.poller.no_credentials.connect(self._on_no_credentials)
        self.poller.start()

        self.widget.refresh_requested.connect(self._force_refresh)
        self.widget.settings_requested.connect(self._open_settings)
        self.widget.quit_requested.connect(self._quit)

    # ------------------------------------------------------------------
    def _on_snapshot(self, snap: UsageSnapshot) -> None:
        if snap.ok and snap.quotas:
            # Fresh good data — replace the cached snapshot and re-render.
            self._last_good = snap
            self._render_full(snap)
            if self.settings.notifications_enabled:
                self._fire_threshold_notifications(snap)
            return

        # Failed refresh. If we have prior good data, keep showing it and
        # surface a subtle "stale" indicator via the merged snapshot.
        if self._last_good is not None:
            merged = dataclasses.replace(
                self._last_good,
                ok=False,
                error=snap.error,
                retry_after_s=snap.retry_after_s,
            )
            # Tray icon still shows the last-good utilization (color-coded),
            # not an error glyph — error detail lives in the hover tooltip.
            tray_u = max(q.utilization for q in self._last_good.quotas)
            self.tray.set_state(
                utilization=tray_u,
                error=False,
                label=self._tray_label(self._last_good),
                tooltip=self._tray_tooltip(
                    self._last_good,
                    note=f"Last refresh failed: {snap.error}",
                ),
            )
            self.widget.update_data(merged, self.history_buckets, self.products)
            return

        # No prior data at all — show the error state on tray + widget.
        self.tray.set_state(
            utilization=0.0,
            error=not snap.ok,
            tooltip=f"Claude Meter — {snap.error or 'no data'}",
        )
        self.widget.update_data(snap, self.history_buckets, self.products)

    # ------------------------------------------------------------------
    def _render_full(self, snap: UsageSnapshot) -> None:
        five = snap.by_key("five_hour")
        seven = snap.by_key("seven_day")
        opus = snap.by_key("seven_day_opus")
        self.history_buckets = history.append(
            u5h=five.utilization if five else None,
            u7d=seven.utilization if seven else None,
            uopus=opus.utilization if opus else None,
        )
        tray_u = max(q.utilization for q in snap.quotas)
        self.tray.set_state(
            utilization=tray_u,
            error=False,
            label=self._tray_label(snap),
            tooltip=self._tray_tooltip(snap),
        )
        self.widget.update_data(snap, self.history_buckets, self.products)

    def _fire_threshold_notifications(self, snap: UsageSnapshot) -> None:
        for q in snap.quotas:
            for t in self.notifier.check(q.key, q.utilization, q.resets_at):
                notifications.fire_toast(
                    f"{q.label} at {int(t * 100)}%",
                    f"You've used {q.percent:.0f}% of your {q.label.lower()} quota.",
                )

    def _on_no_credentials(self) -> None:
        self.tray.set_state(
            utilization=0.0,
            error=True,
            tooltip="No Claude credentials found. Log in with `claude` CLI, or set a key in Settings…",
        )
        synthetic = UsageSnapshot(ok=False, error="No credentials found")
        self.widget.update_data(synthetic, self.history_buckets, self.products)

    # ------------------------------------------------------------------
    def _tray_label(self, snap: UsageSnapshot) -> str:
        primary = snap.by_key("five_hour")
        if primary is None and snap.quotas:
            primary = snap.quotas[0]
        if primary is None:
            return ""
        return f"{int(round(primary.percent))}%"

    def _tray_tooltip(self, snap: UsageSnapshot, note: Optional[str] = None) -> str:
        lines = ["Claude Meter"]
        if snap.plan:
            lines[0] = f"Claude Meter — {snap.plan}"
        for q in snap.quotas:
            lines.append(f"  {q.label}: {q.percent:.1f}%")
        if note:
            lines.append("")
            lines.append(note)
        return "\n".join(lines)

    def _toggle_widget(self) -> None:
        # Tray menu → Show widget. Uses manual_show/hide so the visibility
        # tick respects the user's choice.
        if self.widget.isVisible():
            self.widget.manual_hide()
        else:
            self.widget.manual_show()

    def _force_refresh(self) -> None:
        self.poller.request_refresh()

    def _open_settings(self) -> None:
        dlg = SettingsDialog(self.settings, on_save=self._save_settings)
        dlg.exec()

    def _save_settings(self, new_settings) -> None:
        self.settings = new_settings
        settings_mod.save(new_settings)
        self.notifier = notifications.ThresholdNotifier(self.settings.notify_at_thresholds)
        self.widget.reposition()
        self.poller.request_refresh()

    def _quit(self) -> None:
        self.poller.stop()
        self.qt_app.quit()
