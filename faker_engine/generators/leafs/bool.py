"""Boolean generator.

Produces ``True`` with probability ``p_true``; otherwise returns ``False``.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from mock_engine.context import GenContext
from mock_engine.errors import ContextError
from mock_engine.generators.base import BaseGenerator
from mock_engine.generators.errors import InvalidParameterError

if TYPE_CHECKING:  # avoid import cycles at runtime
    from mock_engine.contracts.types import JsonValue  # pragma: no cover


class BoolGenerator(BaseGenerator):
    """Generate boolean values based on a Bernoulli parameter.

    Args:
        p_true (float | None): Probability of returning ``True`` (0.0–1.0).
            Defaults to ``0.5`` when ``None``.
    """

    __meta__ = {"aliases": {"p_true": "p_true"}, "deprecations": [], "rules": []}
    __slots__ = ("p_true",)
    __aliases__ = ("bool",)

    def __init__(self, p_true: float | None = None) -> None:
        """Initialize with an optional probability."""
        self.p_true: float | None = 0.5 if p_true is None else p_true

    # TODO(arch): depend on a builder/factory protocol instead of a concrete object
    @classmethod
    def from_spec(
        cls,
        builder: Any,
        spec: Mapping[str, object],
    ) -> "BoolGenerator":
        """Construct an instance from a generator specification.

        Args:
            builder (Any): Unused; present for a uniform factory interface.
            spec (Mapping[str, object]): Parsed generator specification.

        Returns:
            BoolGenerator: Configured instance.
        """
        return cls(p_true=spec.get("p_true"))

    def _sanity_check(self, ctx: GenContext) -> None:
        """Validate context and configuration invariants.

        Args:
            ctx (GenContext): Execution context.

        Raises:
            ContextError: If ``ctx`` is not a ``GenContext``.
            InvalidParameterError: ``p_true`` is not numeric or outside ``[0.0, 1.0]``.
        """
        if not isinstance(ctx, GenContext):
            raise ContextError("ctx must be an instance of GenContext")
        try:
            p = float(self.p_true if self.p_true is not None else 0.5)
        except (TypeError, ValueError) as exc:
            # TODO(errors): introduce InvalidProbabilityError with offending value
            raise InvalidParameterError("p_true must be a float between 0 and 1") from exc
        if not 0.0 <= p <= 1.0:
            raise InvalidParameterError("p_true must be between 0 and 1")

    def configure(self, p_true: float | None = None, **_: Any) -> "BoolGenerator":
        """Update configuration and return ``self``.

        Args:
            p_true (float | None): New probability for ``True`` (0.0–1.0).
            **_ (Any): Ignored extra kwargs for forward-compatibility.

        Returns:
            BoolGenerator: ``self`` for chaining.
        """
        if p_true is not None:
            self.p_true = p_true
        return self

    def generate(self, ctx: GenContext) -> "JsonValue":
        """Return ``True`` with probability ``p_true``; else ``False``.

        Args:
            ctx (GenContext): Execution context providing RNG/state.

        Returns:
            JsonValue: Boolean value.
        """
        self._sanity_check(ctx)
        p = float(self.p_true if self.p_true is not None else 0.5)
        return ctx.rng.random() < p
