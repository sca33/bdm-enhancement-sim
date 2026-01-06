"""Utility functions for formatting and display."""


def format_silver(silver: int) -> str:
    """Format silver amount with K/M/B/T suffix."""
    if silver >= 1_000_000_000_000:
        return f"{silver / 1_000_000_000_000:.1f}T"
    if silver >= 1_000_000_000:
        return f"{silver / 1_000_000_000:.1f}B"
    if silver >= 1_000_000:
        return f"{silver / 1_000_000:.1f}M"
    if silver >= 1_000:
        return f"{silver / 1_000:.1f}K"
    return str(silver)


def format_time(seconds: int) -> str:
    """Format seconds into human-readable time (hours/minutes/seconds)."""
    if seconds >= 3600:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours}h {minutes}m"
    if seconds >= 60:
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes}m {secs}s"
    return f"{seconds}s"
