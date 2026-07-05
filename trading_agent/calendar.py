from __future__ import annotations

from datetime import date, timedelta


def business_days_between(start: date, end: date) -> int:
    """Count weekdays after start through end.

    This is a lightweight placeholder for an exchange calendar. It ignores
    market holidays, which should be handled by a real calendar before live use.
    """
    if start == end:
        return 0
    if start > end:
        return -business_days_between(end, start)

    days = 0
    current = start + timedelta(days=1)
    while current <= end:
        if current.weekday() < 5:
            days += 1
        current += timedelta(days=1)
    return days

