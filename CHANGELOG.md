# Changelog

All notable changes to Claude Meter will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

- Codex CLI subscription usage support (v0.2 roadmap) — track `~/.codex/auth.json` alongside Claude

## [0.1.2] — 2026-05-19

### Added
- **Hide for 15 min** snooze option in the right-click menu — temporarily dismiss the ticker, auto-shows after the configured timeout
- **Frosted-glass backdrop** on Windows 11 (Acrylic) — default for that "futuristic glass" look, falls back gracefully on Windows 10
- **Opacity slider** in Settings (30 – 100%) — pick anywhere from fully translucent to fully solid
- **Snooze duration** setting — customize how long "Hide for N min" hides the widget

### Fixed
- Initialization order bug where opacity was applied before the tooltip existed (caught immediately on v0.1.2, fixed in v0.1.3)

## [0.1.1] — 2026-05-16

### Added
- **Right-click menu** on the pinned ticker itself — `Hide widget`, `Refresh now`, `Settings…`, `Quit Claude Meter`
- "Manually hidden" state — once you dismiss the widget, it stays hidden until you bring it back from the tray menu (no more auto-show overrides)

## [0.1.0] — 2026-05-16

Initial public release.

### Added
- Pinned ticker above the Windows taskbar with Session + Weekly progress bars
- System tray icon showing the live percentage, color-coded blue / orange / red
- Rich hover tooltip mirroring `claude.ai/settings/usage` — every quota row (Current session, Weekly · All models, Sonnet only, Opus only, Claude Design), Daily routine runs, plan auto-detection
- Reset countdown in the ticker footer ("resets in 4h 48m · Sat 2:50 AM") and refresh button
- 14-day usage history sparkline
- Toast notifications when crossing 75% / 90% / 95% thresholds
- Auto-detection of installed Claude products (Claude Code, Cowork, Chrome extension)
- Adaptive polling — 7 min normal, 20 min idle, exponential back-off on 429
- Keeps last good data on transient API errors (small amber dot indicates a refresh failed)
- Single .exe distribution via PyInstaller — no installer, no admin
- Auto-detects Claude Code OAuth credentials from `~/.claude/.credentials.json` (Windows + WSL)

[Unreleased]: https://github.com/JackBhanded/claude-meter/compare/v0.1.2...HEAD
[0.1.2]: https://github.com/JackBhanded/claude-meter/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/JackBhanded/claude-meter/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/JackBhanded/claude-meter/releases/tag/v0.1.0
