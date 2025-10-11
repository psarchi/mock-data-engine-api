from datetime import datetime, timedelta
from faker_engine.errors import ContextError, InvalidParameterError
from faker_engine.generators.base import BaseGenerator
from faker_engine.context import GenContext


class TimestampGenerator(BaseGenerator):
    __slots__ = ("start", "end", "unit")
    __aliases__ = ("timestamp",)

    def __init__(self, start=None, end=None, unit=None):
        self.start = start
        self.end = end
        self.unit = unit or "ms"  # ms|us

    @classmethod
    def from_spec(cls, builder, spec):
        return cls(start=spec.get("start"), end=spec.get("end"),
                   unit=spec.get("unit"))

    def _sanity_check(self, ctx):
        if not isinstance(ctx, GenContext):
            raise ContextError("ctx must be an instance of GenContext")
        if self.unit not in ("ms", "us"):
            raise InvalidParameterError("unit must be ms|us")

    def _parse_dt(self, s, default):
        if not s:
            return default
        try:
            return datetime.fromisoformat(s)
        except Exception:
            raise InvalidParameterError("invalid timestamp 'start'/'end'")

    def generate(self, ctx):
        self._sanity_check(ctx)
        now = datetime.utcnow()
        start_dt = self._parse_dt(self.start, now.replace(year=now.year - 1))
        end_dt = self._parse_dt(self.end, now)
        if start_dt > end_dt:
            raise InvalidParameterError("start must be <= end")
        span = (end_dt - start_dt).total_seconds()
        r = ctx.rng.random()
        dt = start_dt + timedelta(seconds=r * span)
        epoch = datetime(1970, 1, 1)
        delta = dt - epoch
        if self.unit == "ms":
            return int(delta.total_seconds() * 1000)
        return int(delta.total_seconds() * 1_000_000)
