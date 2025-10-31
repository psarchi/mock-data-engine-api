"""Spec normalizer entrypoint.

Resolves the framework's builder and delegates to its internal ``_normalize``
implementation. Behavior preserved; public API is intentionally not enforced
here to avoid breaking callers.
"""
from __future__ import annotations

from typing import Any, Mapping

from faker_engine.core.registry import GeneratorRegistry
from faker_engine.spec_builder import SpecBuilder


class SpecNormalizer:
    """Normalize a spec mapping using the active framework builder.

    The builder is resolved from ``faker_engine.api`` and validated for type
    safety. Normalization is delegated to its private ``_normalize`` method to
    preserve existing behavior.

    Raises:
        RuntimeError: If the builder cannot be resolved or has an unexpected type.
    """

    # TODO(arch): Prefer dependency injection (accept builder in __init__) to avoid
    #             importing globals from ``faker_engine.api``.

    def __init__(self) -> None:
        """Initialize by resolving the framework builder.

        Returns:
            None: Constructor performs resolution/validation only.
        """
        try:
            from faker_engine import api as _api
        except Exception as exc:  # noqa: BLE001 (preserve behavior)
            raise RuntimeError("validator.normalizer: api module not available") from exc

        builder = getattr(_api, "_builder", None)
        if not isinstance(builder, SpecBuilder):
            raise RuntimeError("validator.normalizer: _builder must be SpecBuilder(registry)")
        if not isinstance(getattr(builder, "registry", None), GeneratorRegistry):
            raise RuntimeError(
                "validator.normalizer: builder.registry must be GeneratorRegistry"
            )
        self._builder = builder

    def normalize(
        self,
        spec: Mapping[str, object],
        path: tuple[str, ...] | str | None = "root",
    ) -> Any:
        """Normalize a spec mapping.

        Args:
            spec (Mapping[str, object]): Specification mapping parsed from configuration.
            path (tuple[str, ...] | str | None): Schema location for error reporting.

        Returns:
            Any: Normalized representation as produced by the builder.

        Raises:
            RuntimeError: If the builder does not provide a callable ``_normalize``.
        """
        normalize_fn = getattr(self._builder, "_normalize", None)
        if not callable(normalize_fn):
            raise RuntimeError("validator.normalizer: SpecBuilder._normalize is not callable")
        return normalize_fn(spec, path=path)  # type: ignore[misc]
