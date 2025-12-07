from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Any

from mock_engine.context import GenContext
from mock_engine.errors import ContextError
from mock_engine.generators.base import BaseGenerator
from mock_engine.generators.errors import (
    InvalidParameterError,
    MissingChildError,
)
from mock_engine.generators.utils import _pick_index
from mock_engine.registry import Registry


if TYPE_CHECKING:  # avoid import cycles at runtime
    from mock_engine.contracts.types import JsonValue  # noqa : F401

@Registry.register(BaseGenerator)
class OneOfGenerator(BaseGenerator):
    """Generate a value by choosing one child (uniformly or by weights).

    Args:
        choices (list[BaseGenerator] | None): Built child generators to choose from.
        weights (Sequence[float] | None): Relative weights aligned with ``choices``.
    """

    __meta__ = {"aliases": {"choices": "choices", "of": "choices"},
                "deprecations": [], "rules": []}
    __slots__ = ("choices", "weights")
    __aliases__ = ("one_of",)

    def __init__(
            self,
            choices: list[BaseGenerator] | None = None,
            weights: Sequence[float] | None = None,
    ) -> None:
        """Initialize the generator with optional child list and weights."""
        self.choices: list[BaseGenerator] = choices or []
        self.weights: Sequence[float] | None = weights

    # TODO(arch): depend on a builder/factory protocol instead of a concrete object
    @classmethod
    def from_spec(
            cls,
            builder: Any,
            spec: Mapping[str, object],
    ) -> "OneOfGenerator":
        """Construct an instance from a generator specification.

        The spec must provide a list under ``choices``. Each item must be a
        mapping containing an ``of`` key with the child spec.

        Args:
            builder (Any): Object exposing ``build(spec: Mapping[str, object]) -> BaseGenerator``.
            spec (Mapping[str, object]): Parsed generator specification.

        Returns:
            OneOfGenerator: Configured instance.

        Raises:
            MissingChildError: ``choices`` is missing/empty or a choice lacks ``of``.
        """
        raw = spec.get("choices")
        if not raw or not isinstance(raw, list):
            raise MissingChildError("'choices' (list) is required for one_of")

        built: list[BaseGenerator] = []
        for item in raw:
            child_spec = item.get("of") if isinstance(item, dict) else None
            if child_spec is None:
                raise MissingChildError("each choice must provide 'of'")
            built.append(builder.build(child_spec))

        weights = spec.get("weights")
        return cls(choices=built, weights=weights)  # type: ignore[arg-type]

    def _sanity_check(self, ctx: GenContext) -> None:
        """Validate context and configuration invariants.

        Args:
            ctx (GenContext): Execution context.

        Raises:
            ContextError: If ``ctx`` is not a ``GenContext``.
            MissingChildError: No child generators configured.
            InvalidParameterError: ``weights`` is invalid (type/length/sum).
        """
        if not isinstance(ctx, GenContext):
            raise ContextError("ctx must be an instance of GenContext")
        if not self.choices:
            raise MissingChildError("one_of requires at least one child")

        if self.weights is None:
            return

        if not isinstance(self.weights, (list, tuple)):
            # TODO(errors): consider a typed error (e.g., InvalidWeightsTypeError)
            raise InvalidParameterError(
                "weights must be a list/tuple of numbers")
        if len(self.weights) != len(self.choices):
            raise InvalidParameterError("weights length must match choices")
        try:
            total = float(sum(float(x) for x in self.weights))
        except (TypeError, ValueError) as exc:
            # TODO(errors): consider InvalidWeightsValueError with offending element index
            raise InvalidParameterError("weights must be numeric") from exc
        if total <= 0:
            raise InvalidParameterError("sum(weights) must be > 0")

    def configure(
            self,
            choices: list[BaseGenerator] | None = None,
            weights: Sequence[float] | None = None,
            **_: Any,
    ) -> "OneOfGenerator":
        """Update configuration values in place and return ``self``.

        Args:
            choices (list[BaseGenerator] | None): Replacement child list.
            weights (Sequence[float] | None): Replacement weights aligned with choices.
            **_ (Any): Ignored extra kwargs for forward-compatibility.

        Returns:
            OneOfGenerator: ``self`` for chaining.
        """
        if choices is not None:
            self.choices = choices
        if weights is not None:
            self.weights = weights
        return self

    # TODO: consider moving to utils.py
    def _pick_index(self, rng):
        if not self.weights:
            return rng.randint(0, len(self.choices) - 1)
        # weighted pick without external deps
        total = float(sum(self.weights))
        r = rng.random() * total
        acc = 0.0
        for idx, w in enumerate(self.weights):
            acc += float(w)
            if r <= acc:
                return idx
        return len(self.choices) - 1

    def _generate_impl(self, ctx: GenContext) -> "JsonValue":
        """Produce a value by selecting one child according to weights.

        Args:
            ctx (GenContext): Execution context providing RNG/state.

        Returns:
            JsonValue: JSON-compatible value from the selected child.
        """
        self._sanity_check(ctx)
        index = self._pick_index(ctx.rng)
        return self.choices[index].generate(ctx)
