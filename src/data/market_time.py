from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo


NY_TZ = ZoneInfo("America/New_York")


@dataclass(frozen=True)
class MarketSession:
    open_time: time = time(9, 30)
    close_time: time = time(16, 0)

    def is_weekday(self, dt_ny: datetime) -> bool:
        return dt_ny.weekday() < 5  # Mon-Fri

    def is_in_session(self, dt_ny: datetime) -> bool:
        if not self.is_weekday(dt_ny):
            return False
        t = dt_ny.timetz().replace(tzinfo=None)
        return self.open_time <= t <= self.close_time

    def is_before_open(self, dt_ny: datetime) -> bool:
        t = dt_ny.timetz().replace(tzinfo=None)
        return t < self.open_time

    def is_after_close(self, dt_ny: datetime) -> bool:
        t = dt_ny.timetz().replace(tzinfo=None)
        return t > self.close_time


def now_ny() -> datetime:
    return datetime.now(tz=NY_TZ)


def to_ny(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        raise ValueError("Datetime must be timezone-aware")
    return dt.astimezone(NY_TZ)


def ny_date(dt: datetime) -> str:
    return to_ny(dt).date().isoformat()


def ny_time(dt: datetime) -> str:
    return to_ny(dt).time().replace(microsecond=0).isoformat(timespec="seconds")


def floor_to_half_hour(dt_ny: datetime) -> datetime:
    # dt_ny is tz-aware NY time
    minute = 0 if dt_ny.minute < 30 else 30
    return dt_ny.replace(minute=minute, second=0, microsecond=0)


def expected_half_hour_marks(dt_ny: datetime) -> set[time]:
    # 09:30 to 16:00 inclusive
    marks: set[time] = set()
    tcur = datetime.combine(dt_ny.date(), time(9, 30), tzinfo=NY_TZ)
    tend = datetime.combine(dt_ny.date(), time(16, 0), tzinfo=NY_TZ)
    while tcur <= tend:
        marks.add(tcur.time())
        tcur += timedelta(minutes=30)
    return marks
