from __future__ import annotations
from typing import Any, Mapping
from pydantic import ValidationError
from faker_engine.validator.registry_adapter import RegistryAdapter
from faker_engine.validator.normalizer import SpecNormalizer
from faker_engine.validator.model_provider import ModelProvider
from faker_engine.validator.errors import from_pydantic_errors, ExtraIssue, IssueCode, Issue, TypeIssue, RequiredIssue
from faker_engine.validator.report import Report

class Validator:
    def __init__(self,
                 registry: RegistryAdapter | None = None,
                 normalizer: SpecNormalizer | None = None,
                 models: ModelProvider | None = None) -> None:
        self.registry = registry or RegistryAdapter()
        self.normalizer = normalizer or SpecNormalizer()
        self.models = models or ModelProvider()

    def validate(self, spec: Any) -> Report:
        issues: list[Issue] = []

        try:
            normalized = self.normalizer.normalize(spec, path="root")
        except Exception as e:
            exc_path = getattr(e, "path", ("root",))
            if isinstance(exc_path, str):
                exc_path = (exc_path,)
            issues.append(Issue(code=IssueCode.TYPE, path=tuple(exc_path), msg=str(e), detail={"raw": repr(e)}))
            return Report(ok=False, issues=issues, normalized=None)

        if not isinstance(normalized, dict):
            issues.append(TypeIssue(path=("root",), msg="Normalized spec must be an object", detail={"got": type(normalized).__name__}))
            return Report(ok=False, issues=issues, normalized=None)

        gen_type = normalized.get("type")
        if gen_type is None:
            issues.append(RequiredIssue(path=("type",), msg="Field 'type' is required"))
            return Report(ok=False, issues=issues, normalized=None)

        try:
            self.registry.get_class(str(gen_type))
        except Exception as e:
            issues.append(TypeIssue(path=("type",), msg=f"Unknown generator type: {gen_type}", detail={"raw": str(e)}))
            return Report(ok=False, issues=issues, normalized=None)

        model = self.models.model_for(str(gen_type))

        model_fields = set(getattr(model, 'model_fields', {}).keys())
        extras = [k for k in normalized.keys() if k not in model_fields]
        if extras:
            issues.extend(ExtraIssue(path=(k,), msg='Extra field not permitted') for k in extras)
            return Report(ok=False, issues=issues, normalized=None)

        try:
            inst = model.model_validate(normalized)
            return Report(ok=True, issues=[], normalized=inst.model_dump())
        except ValidationError as ve:
            issues.extend(from_pydantic_errors(ve.errors()))
            return Report(ok=False, issues=issues, normalized=None)
