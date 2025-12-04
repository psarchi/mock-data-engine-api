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
from mock_engine.registry import Registry


if TYPE_CHECKING:  # avoid import cycles at runtime
    from mock_engine.contracts.types import JsonValue  # noqa : F401

@Registry.register(BaseGenerator)
class ObjectGenerator(BaseGenerator):
    """Generate an object with fields produced by child generators.

    Args:
        fields (dict[str, BaseGenerator] | None): Mapping of field name to child generator.
    """

    __meta__ = {
        "aliases": {"fields": "fields", "properties": "fields"},
        "deprecations": [],
        "rules": [],
    }
    __slots__ = ("_built", "_meta")
    __aliases__ = ("object",)

    def __init__(self, fields: dict[str, BaseGenerator] | None = None) -> None:
        """Initialize with an optional mapping of field generators."""
        self._built: dict[str, BaseGenerator] = fields or {}
        # Field metadata: {field_name: {"required": bool, "default": Any}}
        self._meta: dict[str, dict[str, Any]] = {}

    # TODO(arch): depend on a builder/factory *protocol* instead of a concrete object
    @classmethod
    def from_spec(
            cls,
            builder: Any,
            spec: Mapping[str, object],
    ) -> "ObjectGenerator":
        """Construct an instance from a generator specification.

        The spec must provide field definitions under ``fields`` (preferred) or
        ``properties``. Each field item may be either a nested spec (built as-is),
        or a mapping with an ``of`` key indicating the child generator spec plus
        optional ``required`` and ``default`` hints.

        Args:
            builder (Any): Object exposing ``build(spec: Mapping[str, object]) -> BaseGenerator``.
            spec (Mapping[str, object]): Parsed generator specification.

        Returns:
            ObjectGenerator: Configured instance.

        Raises:
            MissingChildError: No ``fields``/``properties`` block present or empty.
        """
        fields_block = spec.get("fields") or spec.get("properties")
        if not fields_block or not isinstance(fields_block, dict):
            built = {}
            meta = {}
        else:
            built = {}
            meta = {}
            for field_name, field_spec in fields_block.items():
                if isinstance(field_spec, dict) and "of" in field_spec:
                    child_spec = field_spec.get("of")
                    child = builder.build(child_spec)
                    meta[field_name] = {
                        "required": bool(field_spec.get("required")),
                        "default": field_spec.get("default", None),
                    }
                else:
                    child = builder.build(field_spec)
                    meta[field_name] = {"required": False, "default": None}
                built[field_name] = child

        instance = cls(fields=built)
        instance._meta = meta
        return instance

    def _sanity_check(self, ctx: GenContext) -> None:
        """Validate context and that at least one field is configured.

        Args:
            ctx (GenContext): Execution context.

        Raises:
            ContextError: If ``ctx`` is not a ``GenContext``.
            MissingChildError: If no fields are configured.
        """
        if not isinstance(ctx, GenContext):
            raise ContextError("ctx must be an instance of GenContext")
        if not self._built:
            raise MissingChildError("object has no fields")

    def configure(
            self,
            *,
            fields: dict[str, BaseGenerator] | None = None,
            **_: Any,
    ) -> "ObjectGenerator":
        """Update configuration and return ``self``.

        Args:
            fields (dict[str, BaseGenerator] | None): Replacement field map.
            **_ (Any): Ignored extra kwargs for forward-compatibility.

        Returns:
            ObjectGenerator: ``self`` for chaining.
        """
        if fields is not None:
            self._built = fields
        return self
    def _value_checker(self, value, default_value, is_required, field_name):
        """Check and apply defaults/required validation for a field value."""
        if value is None:
            if default_value is not None:
                value = default_value
            elif is_required:
                # TODO(errors): consider a more specific error (e.g., RequiredFieldMissingError)
                raise InvalidParameterError(
                    f"required field '{field_name}' generated None")
        return value
    
    def generate(self, ctx: GenContext) -> dict[str, "JsonValue"]:
        """Produce an object with values from each child generator.

        Args:
            ctx (GenContext): Execution context providing RNG/state.

        Returns:
            dict[str, JsonValue]: Field values; defaults applied when child returns ``None``.

        Raises:
            InvalidParameterError: A required field generated ``None`` and no default was provided.
        """
        self._sanity_check(ctx)
        output: dict[str, Any] = {}
        depends_on = []
        for field_name, child_gen in self._built.items():
            field_meta = self._meta.get(field_name, {})
            is_required = bool(field_meta.get("required"))
            default_value = field_meta.get("default", None)
            depends = getattr(child_gen, "depends_on", None)
            if depends and depends not in output:
                depends_on.append([field_name, child_gen, depends])
                continue
            if depends and depends in output:
                ctx._depends_on = output[depends]
            value = child_gen.generate(ctx)
            value = self._value_checker(value, default_value, is_required, field_name)
            output[field_name] = value

        while depends_on:
            resolved_any = False
            indx = len(depends_on) - 1
            while indx >= 0:
                d_field_name, d_child_gen, d_depends_on = depends_on[indx]
                if d_depends_on in output:
                    value_depends_on = output[d_depends_on]
                    ctx._depends_on = value_depends_on
                    value = d_child_gen.generate(ctx)
                    d_field_meta = self._meta.get(d_field_name, {})
                    d_is_required = bool(d_field_meta.get("required"))
                    d_default_value = d_field_meta.get("default", None)
                    value = self._value_checker(value, d_default_value, d_is_required, d_field_name)
                    output[d_field_name] = value
                    depends_on.pop(indx)
                    resolved_any = True
                indx -= 1

            if not resolved_any:
                unresolved = [item[0] for item in depends_on]
                raise InvalidParameterError(
                    f"Cannot resolve dependencies: {', '.join(unresolved)}") 
           
            
        return output
