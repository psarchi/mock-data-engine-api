"""Validator core.

Performs structural validation of a spec and maps errors into the engine's
issue types. Behavior keeps backward compatibility with current registry/model
APIs while using golden-file docstrings and typing.
"""
from __future__ import annotations

from collections.abc import Mapping as MappingABC
from typing import Any

from pydantic import ValidationError as PydanticValidationError

from faker_engine.generators.base import BaseGenerator
from faker_engine.validator.errors import (
    ExtraIssue,
    Issue,
    IssueCode,
    RequiredIssue,
    TypeIssue,
    ValidationFailed,
    from_pydantic_errors,
)
from faker_engine.validator.model_provider import ModelProvider
from faker_engine.validator.normalizer import SpecNormalizer
from faker_engine.validator.registry_adapter import RegistryAdapter
from faker_engine.validator.report import Report

JsonPath = tuple[str | int, ...]

# TODO(refactor): too much complexity in this single class; break down
class Validator:
    """Validator that performs structural checks and returns a :class:`Report`.

    Args:
        registry (RegistryAdapter | None): Registry adapter. Defaults to a new instance.
        normalizer (SpecNormalizer | None): Spec normalizer. Defaults to a new instance.
        models (ModelProvider | None): Pydantic model provider. Defaults to a new instance.
    """

    __slots__ = ("registry", "normalizer", "models")

    def __init__(
        self,
        registry: RegistryAdapter | None = None,
        normalizer: SpecNormalizer | None = None,
        models: ModelProvider | None = None,
    ) -> None:
        self.registry = registry or RegistryAdapter()
        self.normalizer = normalizer or SpecNormalizer()
        self.models = models or ModelProvider()

    def validate(
        self,
        spec: MappingABC[str, object],
        *,
        raise_on_fail: bool = False,
        ignore_extras: bool = False,
    ) -> Report:
        """Validate a spec mapping against canonical generator schemas.

        Args:
            spec (Mapping[str, object]): Input spec mapping to validate.
            raise_on_fail (bool): If ``True``, raise :class:`ValidationFailed` when invalid.
            ignore_extras (bool): Drop keys not in the target schema instead of reporting them.

        Returns:
            Report: Validation report with status, issues, and normalized output when OK.
        """
        issues: list[Issue] = []
        try:
            normalized = self.normalizer.normalize(spec, path=("root",))
        except Exception as exc:  # noqa: BLE001 (preserve behavior)
            exc_path = getattr(exc, "path", ("root",))
            if isinstance(exc_path, str):
                exc_path = (exc_path,)
            issues.append(
                Issue(
                    code=IssueCode.TYPE,
                    path=tuple(exc_path),
                    msg=str(exc),
                    detail={"raw": repr(exc)},
                )
            )
            report = Report(ok=False, issues=issues, normalized=None)
            if raise_on_fail:
                raise ValidationFailed(report)
            return report

        if not isinstance(normalized, dict):
            issues.append(
                TypeIssue(
                    path=("root",),
                    msg="Normalized spec must be an object",
                    detail={"received": type(normalized).__name__},
                )
            )
            report = Report(ok=False, issues=issues, normalized=None)
            if raise_on_fail:
                raise ValidationFailed(report)
            return report

        def validate_node(node: MappingABC[str, Any], path: tuple[str, ...]) -> None:
            """Validate a single node (generator config) in the normalized tree.

            Args:
                node (Mapping[str, Any]): Normalized generator configuration.
                path (tuple[str, ...]): Schema location for error reporting.
            """
            current: MappingABC[str, Any] = node
            gen_type = node.get("type")
            if gen_type is None:
                issues.append(RequiredIssue(path=path + ("type",), msg="Field 'type' is required"))
                return

            # Resolve the generator; registry may return an instance *or* (class, canonical).
            try:
                resolved = self.registry.resolve(str(gen_type))
            except Exception as exc:  # noqa: BLE001 (preserve behavior)
                issues.append(
                    TypeIssue(
                        path=path + ("type",),
                        msg=f"Unknown generator type: {gen_type}",
                        detail={"raw": str(exc)},
                    )
                )
                return

            # TODO(compat): Remove tuple fallback once all registries return instances.
            if isinstance(resolved, BaseGenerator):
                gen_cls = resolved.__class__
                canonical = gen_cls.__name__.lower()
            elif isinstance(resolved, type) and issubclass(resolved,
                                                           BaseGenerator):
                # Registry returned a class, not an instance; derive canonical from class name.
                gen_cls = resolved
                canonical = gen_cls.__name__.lower()
            else:
                gen_cls, canonical = resolved  # type: ignore[misc]

            model = self.models.get(gen_cls.__name__)
            model_fields = set(getattr(model, "model_fields", {}).keys())
            allowed_meta = {"type", "required", "of"}  # TODO(policy): centralize meta keys

            # Report or drop extras
            extras = [key for key in node.keys() if key not in model_fields and key not in allowed_meta]
            if ignore_extras and extras:
                current = {key: node[key] for key in node.keys() if key in model_fields}
            else:
                for key in extras:
                    issues.append(
                        ExtraIssue(
                            path=path + (key,),
                            msg=f"Extra field not permitted: {key}",
                            detail={"field": key},
                        )
                    )

            # Pydantic validation
            try:
                model.model_validate(current)
            except PydanticValidationError as pyd_exc:
                issues.extend(from_pydantic_errors(pyd_exc.errors()))
            # TODO (arch): move known child containers either from model or constants or models metadata
            # Recurse into known child containers
            if "fields" in current and isinstance(current["fields"], MappingABC):
                for field_name, child_spec in current["fields"].items():
                    if isinstance(child_spec, MappingABC):
                        validate_node(child_spec, path + ("fields", field_name))
            if "child" in current and isinstance(current["child"], MappingABC):
                validate_node(current["child"], path + ("child",))
            if "items" in current and isinstance(current["items"], MappingABC):
                validate_node(current["items"], path + ("items",))
            if "of" in current and isinstance(current["of"], MappingABC):
                validate_node(current["of"], path + ("of",))
            if "options" in current and isinstance(current["options"], MappingABC):
                for option_name, child_spec in current["options"].items():
                    if isinstance(child_spec, MappingABC):
                        validate_node(child_spec, path + ("options", option_name))

        validate_node(normalized, ("root",))
        ok = not issues
        report = Report(ok=ok, issues=issues, normalized=normalized if ok else None)
        if raise_on_fail and not ok:
            raise ValidationFailed(report)
        return report
