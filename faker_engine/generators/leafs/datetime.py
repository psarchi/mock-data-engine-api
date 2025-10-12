from __future__ import annotations
from typing import Optional, Union

from datetime import datetime, timedelta, timezone
import re

from faker_engine.errors import InvalidParameterError
from faker_engine.generators.base import BaseGenerator
from faker_engine.context import GenContext

UTC = timezone.utc
ISO_DEFAULT = "%Y-%m-%dT%H:%M:%S%z"


class DateTimeGenerator(BaseGenerator):
    __slots__ = ('start', 'end', 'format', 'time_start', 'time_end', 'tz')
    __aliases__ = ('datetime',)

    def __init__(self,
                 start: Optional[Union[int, float, str, datetime]] = None,
                 end: Optional[Union[int, float, str, datetime]] = None,
                 format: Optional[str] = None,
                 time_start: Optional[str] = None,
                 time_end: Optional[str] = None,
                 tz: Optional[Union[str, timezone]] = None) -> None:
        self.start = start
        self.end = end
        self.format = format or ISO_DEFAULT
        self.time_start = time_start
        self.time_end = time_end
        self.tz = tz

    @classmethod
    def from_spec(cls, builder: object,
                  spec: dict[str, object]) -> "DateTimeGenerator":
        return cls(
            start=spec.get('start'),
            end=spec.get('end'),
            format=spec.get('format'),
            time_start=spec.get('time_start'),
            time_end=spec.get('time_end'),
            tz=spec.get('tz'),
        )

    def _infer_div(self, n: float) -> float:
        # numeric epoch → seconds divisor
        if n >= 1000000000000000:  # micros
            return 1000000.0
        if n >= 1000000000000:  # millis
            return 1000.0
        return 1.0  # seconds

    def _parse_moment(self, v: int | float | str | datetime | None,
                      default: datetime) -> datetime:
        if v is None:
            return default
        if isinstance(v, (int, float)):
            div = self._infer_div(float(v))
            return datetime.fromtimestamp(float(v) / div, tz=UTC)
        if isinstance(v, str):
            try:
                dt = datetime.fromisoformat(v)
            except Exception:
                raise InvalidParameterError(
                    'datetime.start/end must be ISO8601 or numeric epoch')
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=UTC)
            return dt.astimezone(UTC)
        raise InvalidParameterError(
            'datetime.start/end must be ISO8601 or numeric epoch')

    def _parse_time(self, s: str) -> tuple[int, int, int]:
        m = re.fullmatch(r'(\d{2}):(\d{2})(?::(\d{2}))?', s or '')
        if not m:
            raise InvalidParameterError(
                "time_start/time_end must be 'HH:MM' or 'HH:MM:SS'")
        h, mnt, sec = int(m.group(1)), int(m.group(2)), int(m.group(3) or 0)
        if not (0 <= h < 24 and 0 <= mnt < 60 and 0 <= sec < 60):
            raise InvalidParameterError('time_start/time_end out of range')
        return h, mnt, sec

    def _apply_tz(self, dt: datetime) -> datetime:
        if not self.tz:
            return dt
        m = re.fullmatch(r'([+-])(\d{2}):(\d{2})', self.tz)
        if not m:
            raise InvalidParameterError("tz must be like '+04:00' or '-03:30'")
        sign = 1 if m.group(1) == '+' else -1
        hh, mm = int(m.group(2)), int(m.group(3))
        offset = timezone(sign * timedelta(hours=hh, minutes=mm))
        return dt.astimezone(offset)

    def generate(self, ctx: GenContext) -> str:
        now = datetime.now(tz=UTC)
        if self.start is None and self.end is None and (
                self.time_start or self.time_end):
            base = now.replace(hour=0, minute=0, second=0, microsecond=0)
            h1, m1, s1 = self._parse_time(self.time_start or '00:00:00')
            h2, m2, s2 = self._parse_time(self.time_end or '23:59:59')
            start_dt = base.replace(hour=h1, minute=m1, second=s1)
            end_dt = base.replace(hour=h2, minute=m2, second=s2)
        else:
            start_dt = self._parse_moment(self.start,
                                          now - timedelta(days=365))
            end_dt = self._parse_moment(self.end, now)
        if end_dt < start_dt:
            raise InvalidParameterError('datetime.end must be >= start')
        span = (end_dt - start_dt).total_seconds()
        pick = ctx.rng.random() * span if span > 0 else 0.0
        dt = start_dt + timedelta(seconds=pick)
        dt = self._apply_tz(dt)
        try:
            return dt.strftime(self.format)
        except Exception as e:
            raise InvalidParameterError('invalid datetime.format: %s' % e)
