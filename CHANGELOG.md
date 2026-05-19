# Changelog

All notable changes to Claude Meter will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

- OpenAI Codex CLI subscription usage support (v0.2 roadmap) — track `~/.codex/auth.json` alongside Claude

## [0.1.3] — 2026-05-19

### Fixed
- **Tooltip no longer overlaps the pinned ticker** when it's too tall to fit above the widget — it now repositions to the left (or right) of the ticker instead of being clipped against the top of the screen
- Documented the Windows SmartScreen first-launch workaround in the README

## [0.1.2] — 2026-05-19

First feature drop after the initial release. Adds a right-click menu, a snooze option, and a glassy-by-default look.

### Added
- **Right-click menu on the pinned ticker** — `Hide widget`, `Hide for 15 min`, `Refresh now`, `Settings…`, `Quit Claude Meter`
- **"Hide for 15 min" snooze** — temporarily dismiss the widget; auto-shows after the configured timeout (range 1 – 240 min, set in Settings)
- **Frosted-glass backdrop** on Windows 11 (Acrylic) — for a "futuristic glass" feel; gracefully falls back to a slight window opacity on Windows 10
- **Opacity slider** in Settings (30 – 100%) — go from very translucent to fully solid
- **Snooze duration** setting — control how long "Hide for N min" hides the widget
- "Manually hidden" state — the visibility tick now respects a user dismissal instead of auto-showing a second later

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

[Unreleased]: https://github.com/JackBhanded/claude-meter/compare/v0.1.3...HEAD
[0.1.3]: https://github.com/JackBhanded/claude-meter/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/JackBhanded/claude-meter/compare/v0.1.0...v0.1.2
[0.1.0]: https://github.com/JackBhanded/claude-meter/releases/tag/v0.1.0
