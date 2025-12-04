from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from mock_engine.context import GenContext
from mock_engine.errors import ContextError
from mock_engine.generators.base import BaseGenerator
from mock_engine.generators.errors import InvalidParameterError
from mock_engine.registry import Registry


if TYPE_CHECKING:  # import only for typing to avoid cycles
    from mock_engine.types import JsonValue  # noqa: F401


# TODO: move to constants
# TODO(arch): use global timezone config from config/DEPRICATED.yaml
UTC = timezone.utc

@Registry.register(BaseGenerator)
class TimestampGenerator(BaseGenerator):
    """Generate a Unix timestamp (microseconds) within a time window.

    Args:
        start (int | float | str | None): Start moment as ISO8601 string or numeric epoch (sec/ms/us).
        end (int | float | str | None): End moment as ISO8601 string or numeric epoch (sec/ms/us).

    Raises:
        ContextError: If ``ctx`` is not a ``GenContext`` in ``generate``.
        InvalidParameterError: If bounds are invalid or unparsable.
    """

    __meta__ = {
        "aliases": {"end": "end", "start": "start"},
        "deprecations": [],
        "rules": [],
    }
    __slots__ = ("start", "end")
    __aliases__ = ("timestamp",)

    # TODO(defaults): Make the fallback window configurable (currently last 365 days).

    def __init__(
        self,
        start: int | float | str | None = None,
        end: int | float | str | None = None,
    ) -> None:
        """Initialize bounds.

        Args:
            start (int | float | str | None): Start moment as ISO8601 string or epoch.
            end (int | float | str | None): End moment as ISO8601 string or epoch.
        """
        self.start = start
        self.end = end

    @classmethod
    def from_spec(
        cls,
        builder: Any,
        spec: Mapping[str, Any],
    ) -> "TimestampGenerator":
        """Construct from a generator specification mapping.

        Args:
            builder (Any): Unused builder/factory (kept for signature parity).
            spec (Mapping[str, Any]): Mapping possibly containing ``start`` and ``end``.

        Returns:
            TimestampGenerator: Configured instance.
        """
        return cls(start=spec.get("start"), end=spec.get("end"))

    # TODO(move): Move to utils
    def _infer_div(self, value: float) -> float:
        """Infer divisor for numeric epochs (seconds/millis/micros).

        Args:
            value (float): Numeric epoch as provided.

        Returns:
            float: Divisor to convert value to seconds.
        """
        if value >= 1_000_000_000_000_000:  # micros
            return 1_000_000.0
        if value >= 1_000_000_000_000:  # millis
            return 1_000.0
        return 1.0  # seconds

    def _parse_dt(self, value: int | float | str | None, default_dt: datetime) -> datetime:
        """Parse a bound value into a UTC ``datetime``.

        Args:
            value (int | float | str | None): ISO8601 string or epoch value; ``None`` uses ``default_dt``.
            default_dt (datetime): Datetime to use when ``value`` is ``None``.

        Returns:
            datetime: Parsed UTC datetime.

        Raises:
            InvalidParameterError: If the value cannot be parsed.
        """
        if value is None:
            return default_dt
        if isinstance(value, (int, float)):
            divisor = self._infer_div(float(value))
            return datetime.fromtimestamp(float(value) / divisor, tz=UTC)
        if isinstance(value, str):
            try:
                parsed = datetime.fromisoformat(value)
            except ValueError:
                raise InvalidParameterError(
                    "timestamp.start/end must be ISO8601 or numeric epoch"
                )
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=UTC)
            return parsed.astimezone(UTC)
        raise InvalidParameterError("timestamp.start/end must be ISO8601 or numeric epoch")

    def _sanity_check(self, ctx: GenContext) -> None:
        """Validate context and that bounds are parseable.

        Args:
            ctx (GenContext): Active generation context.

        Raises:
            ContextError: If ``ctx`` is not a ``GenContext``.
        """
        if not isinstance(ctx, GenContext):
            raise ContextError("ctx must be an instance of GenContext")
        now = datetime.now(tz=UTC)
        _ = self._parse_dt(self.start, now.replace(year=now.year - 1))
        _ = self._parse_dt(self.end, now)

    def generate(self, ctx: GenContext) -> "JsonValue":
        """Produce a timestamp (microseconds) according to configuration.

        Args:
            ctx (GenContext): Generation context providing RNG via ``ctx.rng``.

        Returns:
            JsonValue: Integer microseconds since Unix epoch.
        """
        self._sanity_check(ctx)
        now = datetime.now(tz=UTC)
        start_dt = self._parse_dt(self.start, now.replace(year=now.year - 1))
        end_dt = self._parse_dt(self.end, now)
        if end_dt < start_dt:
            raise InvalidParameterError("timestamp.end must be >= start")
        span_seconds = (end_dt - start_dt).total_seconds()
        choose_seconds = ctx.rng.random() * span_seconds if span_seconds > 0 else 0.0
        dt = start_dt + (end_dt - start_dt) * (choose_seconds / span_seconds) if span_seconds > 0 else start_dt
        return int(round(dt.timestamp() * 1_000_000))
