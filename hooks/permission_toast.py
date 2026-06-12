#!/usr/bin/env python3
"""Claude Code PreToolUse hook — permission toast for Bash/Write/Edit.

stdin: JSON with {tool, input, cwd, user}
exit 0 → allow
exit 1 → timeout (fallback to Claude's own prompt)
exit 2 → deny
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

    # Only watch specific tools
    if not SETTINGS.is_tool_watched(tool):
        sys.exit(0)

    # Empty command on a watched tool — no useful info for toast
    if not command:
        sys.exit(0)

    # Check session cache
    if command and is_allowed(tool, command, cwd):
        sys.exit(0)

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

    # Exit code: 0 = allow, 1 = timeout (fallback to CLI), 2 = deny
    if choice == "timeout":
        sys.exit(1)
    sys.exit(0 if choice in ("allow_once", "allow_session") else 2)


if __name__ == "__main__":
    main()
