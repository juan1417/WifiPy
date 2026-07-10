# AGENTS.md

## Run

```bash
uv run main.py
```

## Install as CLI tool

```bash
uv sync && uv tool install .
wifipy
```

## Structure

- `core/backend.py` — WiFi backend (auto-detects iwctl vs nmcli via `shutil.which`)
- `core/crypto.py` — Fernet encryption + Argon2id KDF
- `core/db.py` — SQLite encrypted password store (WAL + secure_delete, context manager)
- `ui/app.py` — Textual app entry point, modal-based TUI
- `ui/screens.py` — Password/confirm modals (inline CSS, not styles.css)
- `ui/styles.css` — Main app styles only
- `desing/` — Design tokens (colors, layout). Note: directory name is `desing/`, not `design/`
- `main.py` — Entry point, calls `WifiApp().run()`

## Conventions

- Python 3.14 pinned in `.python-version` — do not downgrade.
- Build system: **hatchling** (defined in `pyproject.toml`). Never pip install directly.
- All UI text is in **Spanish**.
- `DatabaseManager` hardcodes master password `"default-session-key"` (`ui/app.py:83`) — not user-provided.
- Auto-refresh interval: 10s (`desing/layouts.py:12`).
- DB stored at `~/.local/share/wifipy/wifi.db` (XDG via platformdirs).
- Backend priority: iwctl first, then nmcli. If neither found, app shows error notification.
- **iwctl emits ANSI color codes** — `_run()` strips them via `_strip_ansi()` or regex breaks.
- No test suite exists. No CI workflows.

## Keyboard shortcuts (vim-style)

| Key | Action |
|-----|--------|
| `j` | Move cursor down |
| `k` | Move cursor up |
| `g` | Go to first network |
| `G` | Go to last network |
| `Enter` | Connect to selected network |
| `d` | Forget selected network |
| `r` | Refresh network list |
| `?` | Show help (keybinds) |
| `q` / `Escape` | Quit |
