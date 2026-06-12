"""Per-project session cache for Allow-Session approvals.

Cache file location: <project>/.claude/cctoast-session.json

JSON schema:
{
  "allowed_commands": ["ToolName|command_text..."],
  "expires_at": 1234567890.0
}
"""

from __future__ import annotations

import json
import os
import time

from hooks.config import SETTINGS

__all__ = ["is_allowed", "add_allowed"]

CACHE_RELPATH = ".claude/cctoast-session.json"
MAX_KEY_LENGTH = 200


def _cache_path(cwd: str) -> str:
    return os.path.join(cwd, CACHE_RELPATH)


def _now() -> float:
    return time.time()


def is_allowed(tool: str, command: str, cwd: str) -> bool:
    """Return True if this exact tool+command was session-allowed (and not expired)."""
    path = _cache_path(cwd)
    if not os.path.isfile(path):
        return False
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return False

    expires_at = data.get("expires_at", 0)
    if _now() > expires_at:
        try:
            os.remove(path)
        except OSError:
            pass
        return False

    key = _make_key(tool, command)
    return key in data.get("allowed_commands", [])


def add_allowed(tool: str, command: str, cwd: str) -> None:
    """Record a session allow for this tool+command."""
    path = _cache_path(cwd)
    data: dict = {}
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            if isinstance(loaded, dict):
                data = loaded
        except (json.JSONDecodeError, OSError):
            data = {}

    data.setdefault("allowed_commands", [])
    key = _make_key(tool, command)
    if key not in data["allowed_commands"]:
        data["allowed_commands"].append(key)

    data["expires_at"] = data.get("expires_at", _now() + SETTINGS.SESSION_TTL_MINUTES * 60)

    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _make_key(tool: str, command: str) -> str:
    """Normalise cache key — first MAX_KEY_LENGTH chars of command."""
    return f"{tool}|{command[:MAX_KEY_LENGTH]}"
