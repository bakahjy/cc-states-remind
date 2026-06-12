# Permission Toast for Claude Code

A `PreToolUse` hook that shows a GUI confirmation toast at the screen bottom-right before Claude Code executes Bash, Write, or Edit operations.

## Installation

1. Clone or copy this directory to your machine.
2. Add the hook config to your Claude Code settings (see below).

## Configuration

### `.claude/settings.json`

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "python \"<ABSOLUTE_PATH>/hooks/permission_toast.py\""
          }
        ]
      }
    ]
  }
}
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CCTOAST_TIMEOUT` | `30` | Toast timeout in seconds (auto-deny) |
| `CCTOAST_WATCHED_TOOLS` | `Bash,Write,Edit` | Comma-separated tool names to monitor |
| `CCTOAST_SESSION_TTL` | `180` | Session allow cache lifetime in minutes |
| `CCTOAST_THEME` | `dark` | UI theme (currently only `dark`) |

## How It Works

1. Claude Code is about to call a tool (Bash, Write, or Edit).
2. The `PreToolUse` hook invokes `permission_toast.py`.
3. If the exact tool+command was previously "Session Allowed", the hook outputs JSON `{permissionDecision: "allow"}` and exits 0 — **this suppresses the native permission prompt**.
4. Otherwise, a Tkinter window appears at the **screen bottom-right**.
5. User picks:
   - **Allow Once** — hook outputs JSON `{permissionDecision: "allow"}` → **no native prompt**
   - **Allow Session** — same + saves to session cache → **no native prompt**
   - **Reject** — hook outputs JSON `{permissionDecision: "deny"}` → tool blocked
   - *Timeout* (30s) — `exit 1` → falls through to Claude Code's own terminal prompt (y/n)

### ⚠️ Key Insight: Why Toast + CLI Prompt?

The old version used only bare exit codes:

| Exit code | What Claude Code does |
|-----------|-----------------------|
| `exit 0` (no stdout JSON) | "Hook has no opinion" → **native permission prompt still fires** |
| `exit 2` | Veto — tool blocked |

To **suppress** the native permission prompt, the hook must return structured JSON on stdout:

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow",
    "permissionDecisionReason": "User approved Bash"
  }
}
```

This is what the current version does — Allow Once / Allow Session now truly prevent the CLI from re-asking.

## Requirements

- Python 3.10+
- tkinter (built-in on Windows/macOS; `apt install python3-tk` on Linux)

## Platform Support

| Platform | Status |
|----------|--------|
| Windows  | ✅ Tested |
| Linux    | ✅ (requires `python3-tk`) |
| macOS    | ✅ |
