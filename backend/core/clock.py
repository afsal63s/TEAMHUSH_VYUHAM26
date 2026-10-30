from datetime import datetime, timedelta, timezone


class Clock:
    """One instance per run or demo session. Never a global."""

    def __init__(self, start_time: datetime | None = None):
        # Naive UTC, to match what PyMongo returns by default (tz_aware=False).
        # Mixing naive and aware datetimes raises TypeError on comparison.
        self._now = start_time or datetime.now(timezone.utc).replace(tzinfo=None)

    def now(self) -> datetime:
        return self._now

    def advance(self, days: float = 0, hours: float = 0, minutes: float = 0) -> None:
        self._now += timedelta(days=days, hours=hours, minutes=minutes)