"""Configuration — read from environment variables with defaults."""

import os


def str_to_list(value: str) -> tuple[str, ...]:
    if not value:
        return ()
    return tuple(v.strip() for v in value.split(",") if v.strip())


def _try_int(value: str | None, default: int) -> int:
    """Convert string to int, returning default on failure."""
    if value is None:
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


class Settings:
    """Immutable settings container populated once at import time."""

    def __init__(self) -> None:
        self.TIMEOUT: int = _try_int(os.environ.get("CCTOAST_TIMEOUT"), 30)
        self.WATCHED_TOOLS: tuple[str, ...] = str_to_list(
            os.environ.get("CCTOAST_WATCHED_TOOLS", "Bash,Write,Edit")
        )
        self.SESSION_TTL_MINUTES: int = _try_int(
            os.environ.get("CCTOAST_SESSION_TTL"), 180
        )
        self.THEME: str = os.environ.get("CCTOAST_THEME", "dark")

    def is_tool_watched(self, tool_name: str) -> bool:
        """Return True if this tool should trigger a toast."""
        return tool_name in self.WATCHED_TOOLS


SETTINGS = Settings()
