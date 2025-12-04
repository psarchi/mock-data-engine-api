from __future__ import annotations

from typing import TYPE_CHECKING, Any, Mapping, Sequence, Self

from mock_engine.context import GenContext
from mock_engine.errors import ContextError
from mock_engine.generators.base import BaseGenerator
from mock_engine.generators.errors import (
    InvalidParameterError,
    MissingChildError,
)

# TODO: Consider moving _pick_index to utils to share with OneOfGenerator
from mock_engine.generators.utils import _pick_index

from mock_engine.registry import Registry


if TYPE_CHECKING:  # avoid import cycles at runtime
    from mock_engine.contracts.types import JsonValue  # noqa : F401

@Registry.register(BaseGenerator)
class EnumGenerator(BaseGenerator):
    """Pick an element from a configured list of values.

    Supports optional numeric weights aligned positionally with ``values``.

    Args:
        values (Sequence[Any] | None): Candidate values to choose from.
        weights (Sequence[float] | None): Relative weights aligned with ``values``; uniform if omitted.

    Raises:
        MissingChildError: When required ``values`` are absent.
        InvalidParameterError: On invalid weight shapes or totals.
    """

    __meta__ = {
        "aliases": {"values": "values", "weights": "weights"},
        "deprecations": [],
        "rules": [],
    }
    __slots__ = ("values", "weights")
    __aliases__ = ("enum",)

    # TODO(validation): Ensure each weight is non-negative and finite (no NaN/inf).

    def __init__(
            self,
            values: Sequence[Any] | None = None,
            weights: Sequence[float] | None = None,
    ) -> None:
        """Initialize with optional values and weights.

        Args:
            values (Sequence[Any] | None): Candidate values; empty list if ``None``.
            weights (Sequence[float] | None): Relative weights; ``None`` means uniform.
        """
        self.values: list[Any] = list(values) if values else []
        self.weights: list[float] | None = list(
            weights) if weights is not None else None

    @classmethod
    def from_spec(
            cls,
            builder: Any,
            spec: Mapping[str, Any],
    ) -> "EnumGenerator":
        """Build an instance from a spec mapping.

        Note: Contract suggests returning the concrete class *type*; preserving
        legacy behavior (instance) to avoid breaking callers.
        # TODO(arch): Revisit to return the class type once callers are updated.

        Args:
            builder (Any): Factory/builder (unused; kept for signature parity).
            spec (Mapping[str, Any]): Mapping possibly containing ``values`` and ``weights``.

        Returns:
            EnumGenerator: Configured instance.
        """
        values = spec.get("values")
        if not values or not isinstance(values, list):
            raise MissingChildError("enum requires 'values' list")
        return cls(values=values, weights=spec.get("weights"))

    def _sanity_check(self, ctx: GenContext) -> None:
        """Validate configuration and context preconditions.

        Args:
            ctx (GenContext): Generation context; must be ``GenContext``.

        Raises:
            ContextError: If ``ctx`` is not a ``GenContext``.
            MissingChildError: If ``values`` is empty.
            InvalidParameterError: If weights are malformed or invalid.
        """
        if not isinstance(ctx, GenContext):
            raise ContextError("ctx must be an instance of GenContext")
        if not self.values:
            raise MissingChildError("enum has no values")
        if self.weights is None:
            return
        if not isinstance(self.weights, (list, tuple)):
            raise InvalidParameterError("weights must be a list")
        if len(self.weights) != len(self.values):
            raise InvalidParameterError("weights length must match values")
        try:
            total = float(sum(self.weights))
        except Exception:  # noqa: BLE001 (kept behavior)
            # TODO(errors): Replace broad exception with a numeric-validation error once defined.
            raise InvalidParameterError("weights must be numeric")
        if total <= 0:
            raise InvalidParameterError("sum(weights) must be > 0")

    def configure(
            self,
            values: Sequence[Any] | None = None,
            weights: Sequence[float] | None = None,
            **_: Any,
    ) -> Self:
        """Apply configuration in-place and return ``self``.

        Unknown kwargs are intentionally ignored to preserve current behavior.

        Args:
            values (Sequence[Any] | None): Optional replacement for ``values``.
            weights (Sequence[float] | None): Optional replacement for ``weights``.
            **_ (Any): Ignored extra arguments.

        Returns:
            Self: ``self`` for fluent chaining.
        """
        if values is not None:
            self.values = list(values)
        if weights is not None:
            self.weights = list(weights)
        return self

    # TODO: Consider moving to utils.py
    #       to share with OneOfGenerator and avoid duplication.
    def _pick_index(self, rng):
        if not self.weights:
            return rng.randint(0, len(self.values) - 1)
        total = float(sum(self.weights))
        r = rng.random() * total
        acc = 0.0
        for idx, w in enumerate(self.weights):
            acc += float(w)
            if r <= acc:
                return idx
        return len(self.values) - 1

    def generate(self, ctx: GenContext) -> "JsonValue":
        """Produce a value according to the configuration.

        Args:
            ctx (GenContext): Generation context providing RNG via ``ctx.rng``.

        Returns:
            JsonValue: One item from ``values`` (weighted if ``weights`` is provided).
        """
        self._sanity_check(ctx)
        index = self._pick_index(ctx.rng)
        return self.values[index]
