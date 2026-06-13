# cc_states_remind — Permission Toast for Claude Code

A `PreToolUse` hook that shows a Tkinter permission toast at the screen bottom-right before Claude Code executes Bash/Write/Edit.

## Architecture

```
permission_toast.py  ← entrypoint (stdin JSON → exit code)
├── config.py         ← env-var settings (CCTOAST_*)
├── session_cache.py  ← Allow-Session persistence (.claude/cctoast-session.json)
└── toast_window.py   ← Tkinter GUI (dark theme, 3 buttons, draggable)
```

- **No deps beyond Python 3.10+ stdlib** (tkinter). No `package.json`, no CI, no test runner.
- Hook is registered in `.claude/settings.json` — path is absolute; any agent cloning the repo must update it.

## stdin/stdout protocol

Claude Code sends a JSON event on stdin. The hook responds via exit code + optional JSON:

| Exit | stdout JSON                  | Meaning                              |
|------|------------------------------|--------------------------------------|
| `0`  | `{"hookSpecificOutput":{...}}` | **Explicit allow** — suppresses native prompt |
| `0`  | *(empty)*                    | **No opinion** — native prompt still fires |
| `1`  | —                            | Timeout — falls through to native prompt |
| `2`  | —                            | **Veto** — tool blocked              |

**Key gotcha:** To suppress Claude Code's own permission prompt, the hook must return structured JSON on stdout from `exit 0`. Bare `exit 0` (no JSON) does *not* suppress the native prompt.

## Session cache

`Allow Session` decisions persist to `<project-root>/.claude/cctoast-session.json`. Cache is keyed by `ToolName|command[:200]`, auto-expires after `CCTOAST_SESSION_TTL` (default 180 min). The cache file is gitignored.

## Config (env vars)

| Var                   | Default        | Description                        |
|-----------------------|----------------|------------------------------------|
| `CCTOAST_TIMEOUT`     | `30`           | Toast timeout in seconds           |
| `CCTOAST_WATCHED_TOOLS` | `Bash,Write,Edit` | Comma-sep tool names to monitor |
| `CCTOAST_SESSION_TTL` | `180`          | Session cache lifetime in minutes  |
| `CCTOAST_THEME`       | `dark`         | UI theme (only `dark` exists)      |

## Quick commands

```powershell
# Verify imports
python -c "from hooks.config import SETTINGS; from hooks.session_cache import is_allowed, add_allowed; from hooks.toast_window import show_toast; print('ok')"

# Simulate a hook call (Read tool — no toast, exits 0 immediately)
echo '{"tool":"Read","input":"cat file.txt","cwd":"."}' | python hooks/permission_toast.py

# Simulate a hook call (Bash tool — shows toast)
echo '{"tool":"Bash","input":"ls","cwd":"."}' | python hooks/permission_toast.py
```

## Cross-platform notes

- Linux requires `sudo apt install python3-tk`
- Hook stdout uses `sys.stdout.buffer.write()` + forced UTF-8 to avoid cp936/cp1252 encoding issues on Windows pipes
- `sys.path` is adjusted at startup so `from hooks.X import Y` works regardless of how Claude Code invokes the script
