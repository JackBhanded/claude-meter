# Changelog

All notable changes to Claude Meter will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

- OpenAI Codex CLI subscription usage support (v0.2 roadmap) — track `~/.codex/auth.json` alongside Claude
- Automatic OAuth token refresh via the `refreshToken` in `~/.claude/.credentials.json` — so the meter survives overnight without requiring you to manually re-run `claude`
- **Browser cookie auth** (v0.2 roadmap) — read `sessionKey` from Chrome/Edge so browser-only and desktop-app-only users don't have to install the Claude Code CLI

## [0.1.4] — 2026-05-20

### Fixed
- **`wsl.exe` no longer flashes a console window** on every refresh. Previously, each poll spawned a brief black window because the subprocess was inheriting parent-less console behaviour from `pythonw.exe`. Now uses `CREATE_NO_WINDOW` on all subprocess calls.
- **Expired OAuth tokens are now visible.** When Anthropic returns 401 (typically overnight when Claude Code hasn't refreshed the token), the widget footer now shows a prominent red **"Session expired — run `claude` to refresh"** message and the warning dot turns red. Previously the widget silently kept showing the stale last-good data with only a subtle amber dot — easy to miss.

### Added
- **Single-instance guard.** Launching Claude Meter when it's already running now bows out quietly instead of opening a second copy — so a stray double-click does nothing.
- **Gradient usage bars (fleet look).** The progress bars now fill with a soft left-to-right gradient for a glassy sheen, matching the rest of the fleet's new look. They still colour by utilization (blue → orange → red).

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

[Unreleased]: https://github.com/JackBhanded/claude-meter/compare/v0.1.4...HEAD
[0.1.4]: https://github.com/JackBhanded/claude-meter/compare/v0.1.3...v0.1.4
[0.1.3]: https://github.com/JackBhanded/claude-meter/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/JackBhanded/claude-meter/compare/v0.1.0...v0.1.2
[0.1.0]: https://github.com/JackBhanded/claude-meter/releases/tag/v0.1.0
