"""Boolean generator.

Produces ``True`` with probability ``p_true``; otherwise returns ``False``.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, List

from mock_engine.context import GenContext
from mock_engine.errors import ContextError
from mock_engine.generators.base import BaseGenerator
from mock_engine.generators.errors import InvalidParameterError
from mock_engine.registry import Registry


if TYPE_CHECKING:  # avoid import cycles at runtime
    from mock_engine.contracts.types import JsonValue  # noqa : F401


@Registry.register(BaseGenerator)
class BoolGenerator(BaseGenerator):
    """Generate boolean values based on a Bernoulli parameter.

    Args:
        p_true (float | None): Probability of returning ``True`` (0.0–1.0).
            Defaults to ``0.5`` when ``None``.
    """

    __meta__ = {
        "aliases": {
            "p_true": "p_true",
            "bound_to": "bound_to",
            "linked_to": "bound_to",
            "bound_to_schema": "bound_to_schema",
            "bound_to_revision": "bound_to_revision",
            "pool": "pool",
            "depends_on_pool": "depends_on_pool",
        },
        "deprecations": [],
        "rules": [],
    }
    __slots__ = ("p_true", "bound_to", "bound_to_schema", "bound_to_revision", "pool", "depends_on_pool")
    __aliases__ = ("bool",)

    def __init__(
        self,
        p_true: float | None = None,
        bound_to: str | None = None,
        bound_to_schema: str | None = None,
        bound_to_revision: int | None = None,
        pool: List[str] | None = None,
        depends_on_pool: str | None = None,
    ) -> None:
        """Initialize with an optional probability."""
        self.p_true: float | None = 0.5 if p_true is None else p_true
        self.bound_to = bound_to
        self.bound_to_schema = bound_to_schema
        self.bound_to_revision = bound_to_revision
        self.pool = pool
        self.depends_on_pool = depends_on_pool

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
        return cls(
            p_true=spec.get("p_true"),
            bound_to=spec.get("bound_to") or spec.get("linked_to"),
            bound_to_schema=spec.get("bound_to_schema"),
            bound_to_revision=spec.get("bound_to_revision"),
            pool=spec.get("pool"),
            depends_on_pool=spec.get("depends_on_pool"),
        )

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
            raise InvalidParameterError(
                "p_true must be a float between 0 and 1"
            ) from exc
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

    def _generate_impl(self, ctx: GenContext) -> "JsonValue":
        """Return ``True`` with probability ``p_true``; else ``False``.

        Args:
            ctx (GenContext): Execution context providing RNG/state.

        Returns:
            JsonValue: Boolean value.
        """
        self._sanity_check(ctx)
        p = float(self.p_true if self.p_true is not None else 0.5)
        return ctx.rng.random() < p
