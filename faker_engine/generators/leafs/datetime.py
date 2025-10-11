from datetime import datetime, timedelta
from faker_engine.errors import ContextError, InvalidParameterError
from faker_engine.generators.base import BaseGenerator
from faker_engine.context import GenContext


class DateTimeGenerator(BaseGenerator):
    __slots__ = ("start", "end", "format")
    __aliases__ = ("datetime",)

    def __init__(self, start=None, end=None, format=None):
        self.start = start
        self.end = end
        self.format = format or "iso8601"  # iso8601|epoch_ms|epoch_us

    @classmethod
    def from_spec(cls, builder, spec):
        return cls(start=spec.get("start"), end=spec.get("end"),
                   format=spec.get("format"))

    def _sanity_check(self, ctx):
        if not isinstance(ctx, GenContext):
            raise ContextError("ctx must be an instance of GenContext")
        if self.format not in ("iso8601", "epoch_ms", "epoch_us"):
            raise InvalidParameterError(
                "format must be iso8601|epoch_ms|epoch_us")

    def _parse_dt(self, s, default):
        if not s:
            return default
        try:
            return datetime.fromisoformat(s)
        except Exception:
            raise InvalidParameterError("invalid datetime 'start'/'end'")

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
        if self.format == "iso8601":
            # seconds precision for stable diffs
            return dt.replace(microsecond=0).isoformat()
        epoch = datetime(1970, 1, 1)
        delta = dt - epoch
        if self.format == "epoch_ms":
            return int(delta.total_seconds() * 1000)
        return int(delta.total_seconds() * 1_000_000)
