from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from mock_engine.context import GenContext
from mock_engine.errors import ContextError
from mock_engine.generators.base import BaseGenerator
from mock_engine.generators.errors import (
    InvalidParameterError,
    MissingChildError,
)

if TYPE_CHECKING:  # avoid import cycles at runtime
    from mock_engine.contracts.types import JsonValue  # noqa: F401


class MaybeGenerator(BaseGenerator):
    """Generate either ``None`` or the result of a child generator.

    Args:
        child (BaseGenerator | None): Child generator to produce the non-null value.
        p_null (float | None): Probability of returning ``None`` (0.0–1.0).
    """

    __meta__ = {
        "aliases": {"child": "child", "p_null": "p_null"},
        "deprecations": [],
        "rules": [],
    }
    __slots__ = ("child", "p_null")
    __aliases__ = ("maybe",)

    def __init__(
        self,
        child: BaseGenerator | None = None,
        p_null: float | None = None,
    ) -> None:
        """Initialize the generator with optional child and null probability."""
        self.child = child
        self.p_null = 0.1 if p_null is None else p_null

    # TODO(arch): depend on a builder/factory protocol instead of a concrete object
    @classmethod
    def from_spec(
        cls,
        builder: Any,
        spec: Mapping[str, object],
    ) -> "MaybeGenerator":
        """Construct an instance from a generator specification.

        The spec must supply the child under ``of`` (preferred) or ``child``.
        Optional key: ``p_null`` (float in 0.0–1.0).

        Args:
            builder (Any): Object with ``build(spec: Mapping[str, object]) -> BaseGenerator``.
            spec (Mapping[str, object]): Parsed generator specification.

        Returns:
            MaybeGenerator: Configured instance.

        Raises:
            MissingChildError: If neither ``of`` nor ``child`` is present.
        """
        child_spec = spec.get("of") or spec.get("child")
        if not child_spec:
            raise MissingChildError("maybe generator requires 'of' or 'child'")
        child = builder.build(child_spec)
        p_null_value = spec.get("p_null")
        return cls(child=child, p_null=p_null_value)  # type: ignore[arg-type]

    def _sanity_check(self, ctx: GenContext) -> None:
        """Validate context and configuration invariants.

        Args:
            ctx (GenContext): Execution context.

        Raises:
            ContextError: If ``ctx`` is not a ``GenContext``.
            MissingChildError: No child generator has been configured.
            InvalidParameterError: ``p_null`` is outside ``[0.0, 1.0]``.
        """
        if not isinstance(ctx, GenContext):
            raise ContextError("ctx must be an instance of GenContext")
        if self.child is None:
            raise MissingChildError("maybe requires a child generator")
        if self.p_null is None:
            self.p_null = 0.1
        try:
            p = float(self.p_null)
        except (TypeError, ValueError) as exc:
            # TODO(errors): consider a typed error (e.g., InvalidProbabilityError)
            raise InvalidParameterError("p_null must be a float between 0 and 1") from exc
        if not 0.0 <= p <= 1.0:
            raise InvalidParameterError("p_null must be between 0 and 1")

    def configure(
        self,
        child: BaseGenerator | None = None,
        p_null: float | None = None,
        **_: Any,
    ) -> "MaybeGenerator":
        """Update configuration and return ``self``.

        Args:
            child (BaseGenerator | None): Replacement child generator.
            p_null (float | None): New null probability (0.0–1.0).
            **_ (Any): Ignored extra kwargs for forward-compatibility.

        Returns:
            MaybeGenerator: ``self`` for chaining.
        """
        if child is not None:
            self.child = child
        if p_null is not None:
            self.p_null = p_null
        return self

    def generate(self, ctx: GenContext) -> "JsonValue":
        """Return ``None`` with probability ``p_null``, else child value.

        Args:
            ctx (GenContext): Execution context providing RNG/state.

        Returns:
            JsonValue: JSON-compatible value or ``None``.
        """
        self._sanity_check(ctx)
        if ctx.rng.random() < float(self.p_null):  # type: ignore[arg-type]
            return None
        # mypy: self.child is validated in _sanity_check
        return self.child.generate(ctx)  # type: ignore[union-attr]