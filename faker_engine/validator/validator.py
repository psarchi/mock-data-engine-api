from __future__ import annotations
from typing import Any, Mapping, Sequence
from pydantic import ValidationError as PydanticValidationError
from faker_engine.validator.registry_adapter import RegistryAdapter
from faker_engine.validator.normalizer import SpecNormalizer
from faker_engine.validator.model_provider import ModelProvider
from faker_engine.validator.errors import from_pydantic_errors, ExtraIssue, \
    Issue, IssueCode, TypeIssue, RequiredIssue
from faker_engine.validator.report import Report
from collections.abc import Mapping

JsonPath = tuple[str | int, ...]


class Validator:
    def __init__(self,
                 registry: RegistryAdapter | None = None,
                 normalizer: SpecNormalizer | None = None,
                 models: ModelProvider | None = None) -> None:
        self.registry = registry or RegistryAdapter()
        self.normalizer = normalizer or SpecNormalizer()
        self.models = models or ModelProvider()

    def validate(self, spec: Any, *, raise_on_fail: bool = False,
                 ignore_extras: bool = False) -> Report:
        issues: list[Issue] = []

        try:
            normalized = self.normalizer.normalize(spec, path="root")
        except Exception as e:
            exc_path = getattr(e, "path", ("root",))
            if isinstance(exc_path, str):
                exc_path = (exc_path,)
            issues.append(
                Issue(code=IssueCode.TYPE, path=tuple(exc_path), msg=str(e),
                      detail={"raw": repr(e)}))
            report = Report(ok=False, issues=issues, normalized=None)
            if raise_on_fail:
                from faker_engine.validator.errors import ValidationFailed
                raise ValidationFailed(report)
            return report

        # Guard
        if not isinstance(normalized, dict):
            issues.append(TypeIssue(path=("root",),
                                    msg="Normalized spec must be an object",
                                    detail={"got": type(normalized).__name__}))
            report = Report(ok=False, issues=issues, normalized=None)
            if raise_on_fail:
                from faker_engine.validator.errors import ValidationFailed
                raise ValidationFailed(report)
            return report

        def validate_node(node: Mapping[str, Any], path: JsonPath) -> None:
            # type presence
            cur: Mapping[str, Any] = node
            gen_type = node.get("type")
            if gen_type is None:
                issues.append(RequiredIssue(path=path + ("type",),
                                            msg="Field 'type' is required"))
                return

            # resolve class (aliases allowed)
            try:
                gen_cls, canonical = self.registry.resolve(str(gen_type))
            except Exception as e:
                issues.append(TypeIssue(path=path + ("type",),
                                        msg=f"Unknown generator type: {gen_type}",
                                        detail={"raw": str(e)}))
                pass
            else:
                model = self.models.get(gen_cls.__name__)

                # extras (forbid) — collect, don't bail
                model_fields = set(getattr(model, "model_fields", {}).keys())
                allowed_meta = {"type", "required", "of"}
                extras = [k for k in node.keys() if
                          k not in model_fields and k not in allowed_meta]
                for k in extras:
                    issues.append(ExtraIssue(path=path + (k,),
                                             msg=f"Extra field not permitted: {k}",
                                             detail={"field": k}))
                cur = node
                if ignore_extras and extras:
                    # drop extras for validation and traversal
                    cur = {k: node[k] for k in node.keys() if
                           k in model_fields}

                # pydantic validation — collect
                try:
                    model.model_validate(cur)
                except PydanticValidationError as ve:
                    issues.extend(from_pydantic_errors(ve.errors()))

            # recurse for common composites
            if "fields" in cur and isinstance(cur["fields"], Mapping):
                for fname, child_spec in cur["fields"].items():
                    if isinstance(child_spec, Mapping):
                        validate_node(child_spec, path + ("fields", fname))
            if "child" in cur and isinstance(cur["child"], Mapping):
                validate_node(cur["child"], path + ("child",))
            if "items" in cur and isinstance(cur["items"], Mapping):
                validate_node(cur["items"], path + ("items",))
            if "of" in cur and isinstance(cur["of"], Mapping):
                validate_node(cur["of"], path + ("of",))
            if "options" in cur and isinstance(cur["options"], Mapping):
                for oname, child_spec in cur["options"].items():
                    if isinstance(child_spec, Mapping):
                        validate_node(child_spec, path + ("options", oname))

        validate_node(normalized, ("root",))

        ok = len(issues) == 0
        report = Report(ok=ok, issues=issues,
                        normalized=(normalized if ok else None))
        if raise_on_fail and not ok:
            from faker_engine.validator.errors import ValidationFailed
            raise ValidationFailed(report)
        return report
