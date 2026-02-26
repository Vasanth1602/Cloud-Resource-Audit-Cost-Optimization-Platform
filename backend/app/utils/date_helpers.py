from __future__ import annotations

from datetime import datetime, timezone


def utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


def format_iso(dt: datetime) -> str:
    return dt.isoformat()


def days_between(start: datetime, end: datetime) -> int:
    return abs((end - start).days)


def month_start_end(year: int, month: int) -> tuple[str, str]:
    import calendar
    last_day = calendar.monthrange(year, month)[1]
    start = f"{year}-{month:02d}-01"
    end = f"{year}-{month:02d}-{last_day:02d}"
    return start, end
