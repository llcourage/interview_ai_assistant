"""
UTC timezone utilities
Ensures all datetime operations use UTC to avoid timezone bugs
"""
from datetime import datetime, timezone
from typing import Optional, Union


def utcnow() -> datetime:
    """Get current UTC datetime (replaces datetime.now())"""
    return datetime.now(timezone.utc)


def ensure_utc(dt: Optional[Union[str, datetime]]) -> Optional[datetime]:
    """
    Ensure datetime is UTC aware.
    
    - If None, returns None
    - If string, parses as ISO format (handles 'Z' suffix)
    - If naive datetime, assumes it's UTC and adds timezone
    - If aware datetime, converts to UTC
    
    Args:
        dt: datetime string, datetime object, or None
        
    Returns:
        UTC-aware datetime or None
    """
    if dt is None:
        return None
    
    # Parse string to datetime
    if isinstance(dt, str):
        dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))
    
    # Ensure UTC aware
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    else:
        return dt.astimezone(timezone.utc)

