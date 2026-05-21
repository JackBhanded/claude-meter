# CLAUDE.md — Claude Meter

Context for any Claude (or human) picking up this repo. Keep it current.

## What this is

A live Windows taskbar widget showing your Claude usage — per-model breakdown,
percentages, and reset countdowns — so you can see how much quota is left without
leaving the editor. Python + PySide6, shipped as a single `.exe`.

## How it gets the data

`GET https://api.anthropic.com/api/oauth/usage` with `Authorization: Bearer <token>`
and header `anthropic-beta: oauth-2025-04-20`. The token is the
`claudeAiOauth.accessToken` from `~/.claude/.credentials.json`. The JSON returns
per-quota rows (`five_hour`, `seven_day`, `seven_day_sonnet`, `seven_day_opus`,
`seven_day_omelette` = the Claude Design codename). The endpoint rate-limits hard,
so polling is adaptive with backoff.

## UI

PySide6 widget, light "Claude brew" theme, the real Claude logo rendered
programmatically, progress bars coloured blue → orange (>50%) → red (>80%), reset
countdowns, refresh control, system tray icon + settings, threshold toast
notifications. Runs windowless via a silent launcher; packaged with PyInstaller.

## Hard-won gotchas

- **PyInstaller relative-import crash** — use absolute imports
  (`from claude_usage_widget.main import main`), not `from .main import main`.
- **QThread parenting** — `moveToThread` needs a QThread with no parent.
- **Tooltip overlap** — reposition beside the widget when it can't fit above.
- **Fullscreen detection** — hide the widget when another app is fullscreen.
- **`wsl.exe`/subprocess console flash** — launch with `CREATE_NO_WINDOW`.
- **Morning stale data** — the widget showed yesterday's data and refresh hung;
  handled by re-probing and a visible "auth expired / not refreshed" icon state.

## Build & ship

PyInstaller → single `.exe`; GitHub Actions builds it on a version tag. SmartScreen
warns on the unsigned exe (More info → Run anyway); documented in the README.

## Roadmap

v0.2: browser cookie auth (sessionKey from Chrome/Edge), Codex usage support.
Later: multi-account cycling, Linux tray build, CSV export of the 14-day history.
**v0.3 idea:** log usage over time and add a rich history dashboard (trends per
model, burn rate, time-of-day heatmaps, projections).

## Part of the fleet

- **Claude Meter** — you are here.
- [Claude Lifeboat](https://github.com/JackBhanded/claude-lifeboat) — backup & restore for Claude data.
- [Claude Lifejacket](https://github.com/JackBhanded/claude-lifejacket) — keep every session aware of your projects.

_Maintainer's working-style/personal context is kept in private notes, not in this public file._
