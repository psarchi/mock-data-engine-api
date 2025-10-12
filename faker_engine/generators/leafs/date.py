from __future__ import annotations
from typing import Optional, Union

from datetime import datetime, date, timedelta, timezone
from faker_engine.errors import ContextError, InvalidParameterError
from faker_engine.generators.base import BaseGenerator
from faker_engine.context import GenContext


class DateGenerator(BaseGenerator):
    __slots__ = ("start", "end", "format")
    __aliases__ = ("date",)

    def __init__(self, start: Optional[Union[date, str]] = None,
                 end: Optional[Union[date, str]] = None,
                 format: Optional[str] = None) -> None:
        self.start = start
        self.end = end
        self.format = format or "iso8601"  # iso8601|epoch_ms|epoch_us

    @classmethod
    def from_spec(cls, builder: object,
                  spec: dict[str, object]) -> "DateGenerator":
        return cls(start=spec.get("start"), end=spec.get("end"),
                   format=spec.get("format"))

    def _sanity_check(self, ctx: GenContext) -> None:
        if not isinstance(ctx, GenContext):
            raise ContextError("ctx must be an instance of GenContext")
        if self.format not in ("iso8601", "epoch_ms", "epoch_us"):
            raise InvalidParameterError(
                "format must be iso8601|epoch_ms|epoch_us")

    def _parse_date(self, s: int | float | str | date | None,
                    default: date) -> date:
        if not s:
            return default
        try:
            if len(s) == 10:
                return datetime.fromisoformat(s).date()
            return datetime.fromisoformat(s).date()
        except Exception:
            raise InvalidParameterError("invalid date 'start'/'end'")

    def generate(self, ctx: GenContext) -> int | str:
        self._sanity_check(ctx)
        today = date.today()
        start_d = self._parse_date(self.start,
                                   today.replace(year=today.year - 5))
        end_d = self._parse_date(self.end, today)
        if start_d > end_d:
            raise InvalidParameterError("start must be <= end")
        span = (end_d - start_d).days
        offset = ctx.rng.randint(0, span if span > 0 else 0)
        d = start_d + timedelta(days=offset)
        if self.format == "iso8601":
            return d.isoformat()
        # use UTC-aware midnight for epoch math
        epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
        dt = datetime(d.year, d.month, d.day, tzinfo=timezone.utc)
        delta = dt - epoch
        if self.format == "epoch_ms":
            return int(delta.total_seconds() * 1000)
        return int(delta.total_seconds() * 1_000_000)
