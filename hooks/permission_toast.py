#!/usr/bin/env python3
"""Claude Code PreToolUse hook — permission toast for Bash/Write/Edit.

stdin: JSON with {tool, input, cwd, user}
exit 0 with JSON on stdout → explicit allow/deny (suppresses native prompt)
exit 2 → veto (blocks tool call, stderr shown to Claude)

On timeout → exit 1 → Claude falls through to its own permission prompt.

Key insight: exit 0 WITHOUT JSON means "no opinion" — native prompt still fires.
To suppress it, output structured JSON with permissionDecision.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Ensure the parent of hooks/ is on sys.path so that "from hooks.X import Y"
# works both when run as `python hooks/permission_toast.py` and when invoked
# by Claude Code's hook runner (which adds the hooks dir to sys.path).
_HOOKS_PARENT = str(Path(__file__).resolve().parent.parent)
if _HOOKS_PARENT not in sys.path:
    sys.path.insert(0, _HOOKS_PARENT)

from hooks.config import SETTINGS
from hooks.session_cache import add_allowed, is_allowed
from hooks.toast_window import show_toast


def _exit_with_decision(
    decision: str,
    reason: str = "",
) -> None:
    """Print structured JSON to stdout and exit 0.

    Claude Code reads the JSON and uses permissionDecision to decide
    whether to suppress the native permission prompt.
    """
    payload = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,
            "permissionDecisionReason": reason,
        },
    }
    print(json.dumps(payload))
    sys.exit(0)


def main() -> None:
    # Read stdin JSON
    raw = sys.stdin.read().strip()
    if not raw:
        # No input → no-op allow
        sys.exit(0)
    try:
        event = json.loads(raw)
    except json.JSONDecodeError:
        sys.exit(0)

    tool: str = event.get("tool_name", event.get("tool", ""))
    tool_input = event.get("tool_input", {})
    # Bash passes command as tool_input.command; other tools may vary
    command: str = ""
    if isinstance(tool_input, dict):
        command = tool_input.get("command", tool_input.get("file_path", ""))
    elif isinstance(tool_input, str):
        command = tool_input
    cwd: str = event.get("cwd", "")

    # Only watch specific tools — unwatched tools get no opinion
    if not SETTINGS.is_tool_watched(tool):
        sys.exit(0)

    # Empty command on a watched tool — no useful info for toast
    if not command:
        sys.exit(0)

    # Check session cache — auto-allow if cached
    if command and is_allowed(tool, command, cwd):
        _exit_with_decision("allow", f"Session-cached approval for {tool}")

    # Show toast
    choice = show_toast(
        tool=tool,
        command=command,
        cwd=cwd,
        timeout_seconds=SETTINGS.TIMEOUT,
    )

    # Record session allow
    if choice == "allow_session" and command:
        add_allowed(tool, command, cwd)

    # Map choice to permission decision
    if choice == "timeout":
        # Timeout: no explicit decision → fall back to Claude's own prompt
        sys.exit(1)
    elif choice in ("allow_once", "allow_session"):
        _exit_with_decision("allow", f"User approved {tool}")
    else:
        _exit_with_decision("deny", f"User rejected {tool}")


if __name__ == "__main__":
    main()
