"""Model provider for validator schemas.

Builds Pydantic models from ``contracts`` *Spec classes by reflecting their
annotations and applying strict scalar types. Behavior is side-effect free and
keeps a small in-process cache keyed by generator name.
"""

from __future__ import annotations

import importlib
from typing import Any, get_args, get_origin, get_type_hints, Union

from pydantic import BaseModel, create_model
from pydantic.config import ConfigDict
from pydantic.types import StrictBool, StrictFloat, StrictInt


class ModelProvider:
    """Construct Pydantic models from contract specs.

    Attributes:
        _contracts_module (module): Imported ``mock_engine.contracts`` module.
        _cache (dict[str, type[BaseModel]]): In-memory model cache keyed by generator name.
    """

    __slots__ = ("_contracts_module", "_cache")

    # TODO(perf): Cache collected spec classes across instances if module is static.

    def __init__(self) -> None:
        """Initialize provider and import the contracts module.

        Returns:
            None: Constructor has side effects only (imports, cache setup).
        """
        self._contracts_module = importlib.import_module("mock_engine.contracts")
        self._cache: dict[str, type[BaseModel]] = {}

    def _collect_specs(self) -> dict[str, type]:
        """Return mapping of spec class names to classes from contracts.

        Returns:
            dict[str, type]: Map of ``<Name>Spec`` → class objects.
        """
        spec_map: dict[str, type] = {}
        # Prefer explicit export list when present
        for export_name in getattr(self._contracts_module, "__all__", []):
            contract_obj = getattr(self._contracts_module, export_name, None)
            if isinstance(contract_obj, type) and export_name.endswith("Spec"):
                spec_map[export_name] = contract_obj
        # Fallback: scan module attributes
        if not spec_map:
            for attr_name in dir(self._contracts_module):
                if not attr_name.endswith("Spec"):
                    continue
                contract_obj = getattr(self._contracts_module, attr_name, None)
                if isinstance(contract_obj, type):
                    spec_map[attr_name] = contract_obj
        return spec_map

    def _infer_spec_name(self, generator_name: str) -> str:
        """Infer spec class name from a generator name.

        Args:
            generator_name (str): Dotted name such as ``"pkg.module.IntGenerator"`` or ``"int"``.

        Returns:
            str: Inferred spec class name (e.g., ``"IntGeneratorSpec"``).
        """
        base = generator_name.split(".")[-1]
        stem = (
            base
            if base.endswith("Generator")
            else f"{base[:1].upper()}{base[1:]}Generator"
        )
        return f"{stem}Spec"

    def _strictify(self, annotation: Any) -> Any:
        """Convert loose scalar annotations to strict Pydantic types.

        ``int`` → :class:`StrictInt`, ``float`` → :class:`StrictFloat`,
        ``bool`` → :class:`StrictBool`. Generic types are processed recursively.

        Args:
            annotation (Any): Original annotation to transform.

        Returns:
            Any: Transformed annotation suitable for Pydantic.
        """
        origin = get_origin(annotation)
        if origin is None:
            if annotation is int:
                return StrictInt
            if annotation is float:
                return StrictFloat
            if annotation is bool:
                return StrictBool
            return annotation

        sub_args = tuple(self._strictify(arg) for arg in get_args(annotation))
        try:
            if origin is Union:
                return Union[sub_args]
            if hasattr(origin, "__getitem__"):
                return origin[sub_args]  # type: ignore[index]
        except Exception:  # noqa: BLE001 (preserve behavior)
            # TODO(errors): Handle typing corner cases (ForwardRef, Annotated) explicitly.
            return annotation
        return annotation

    def get(self, generator_name: str) -> type[BaseModel]:
        """Return (and cache) the model for a given generator name.

        Args:
            generator_name (str): Dotted or simple generator name.

        Returns:
            type[BaseModel]: Generated Pydantic model class.

        Raises:
            KeyError: If the corresponding ``*Spec`` class cannot be found.
        """
        cached = self._cache.get(generator_name)
        if cached is not None:
            return cached

        spec_classes = self._collect_specs()
        spec_class = spec_classes.get(self._infer_spec_name(generator_name))
        if spec_class is None:
            # TODO(errors): Introduce a domain error (e.g., SpecNotFoundError) for clarity.
            raise KeyError(f"Spec not found for '{generator_name}'")

        hints = get_type_hints(spec_class, include_extras=True)
        fields: dict[str, tuple[Any, Any]] = {}
        for field_name, annotation in hints.items():
            strict_annotation = self._strictify(annotation)
            default_value = getattr(spec_class, field_name, ...)
            fields[field_name] = (strict_annotation, default_value)

        model = create_model(
            f"{spec_class.__name__.removesuffix('Spec')}Model",
            __base__=BaseModel,
            **fields,
        )
        model.model_config = ConfigDict(extra="forbid", validate_default=True)
        self._cache[generator_name] = model
        return model
