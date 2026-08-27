"""Common domain primitives and helpers."""
from datetime import datetime, timezone


def current_utc_timestamp() -> str:
    """Helper to generate standard ISO 8601 UTC timestamp."""
    return datetime.now(timezone.utc).isoformat()
