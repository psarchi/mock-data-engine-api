from datetime import datetime, timezone

from faker_engine.errors import InvalidParameterError
from faker_engine.generators.base import BaseGenerator
from faker_engine.context import GenContext

UTC = timezone.utc

class TimestampGenerator(BaseGenerator):
    __slots__ = ('start', 'end')
    __aliases__ = ('timestamp',)

    def __init__(self, start=None, end=None):
        self.start = start
        self.end = end

    @classmethod
    def from_spec(cls, builder, spec):
        return cls(start=spec.get('start'), end=spec.get('end'))

    def _infer_div(self, n):
        if n >= 1000000000000000:  # micros
            return 1000000.0
        if n >= 1000000000000:     # millis
            return 1000.0
        return 1.0                 # seconds

    def _parse_dt(self, v, default):
        if v is None:
            return default
        if isinstance(v, (int, float)):
            div = self._infer_div(float(v))
            return datetime.fromtimestamp(float(v) / div, tz=UTC)
        if isinstance(v, str):
            try:
                dt = datetime.fromisoformat(v)
            except Exception:
                raise InvalidParameterError('timestamp.start/end must be ISO8601 or numeric epoch')
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=UTC)
            return dt.astimezone(UTC)
        raise InvalidParameterError('timestamp.start/end must be ISO8601 or numeric epoch')

    def generate(self, ctx):
        now = datetime.now(tz=UTC)
        start_dt = self._parse_dt(self.start, now.replace(year=now.year - 1))
        end_dt = self._parse_dt(self.end, now)
        if end_dt < start_dt:
            raise InvalidParameterError('timestamp.end must be >= start')
        span = (end_dt - start_dt).total_seconds()
        pick = ctx.rng.random() * span if span > 0 else 0.0
        dt = start_dt + (end_dt - start_dt) * (pick / span) if span > 0 else start_dt
        return int(round(dt.timestamp() * 1_000_000))
