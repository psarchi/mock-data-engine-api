from __future__ import annotations
from typing import Any, Mapping
from pydantic import ValidationError
from .registry_adapter import RegistryAdapter
from .normalizer import SpecNormalizer
from .model_provider import ModelProvider
from .errors import from_pydantic_errors, ExtraIssue, IssueCode, Issue
from .report import Report


class Validator:
    def __init__(self,
                 registry: RegistryAdapter | None = None,
                 normalizer: SpecNormalizer | None = None,
                 models: ModelProvider | None = None) -> None:
        self.registry = registry or RegistryAdapter()
        self.normalizer = normalizer or SpecNormalizer()
        self.models = models or ModelProvider()

    @staticmethod
    def _apply_aliases(spec: Mapping[str, Any], aliases: Mapping[str, str]) -> \
    dict[str, Any]:
        if not aliases:
            return dict(spec)
        out: dict[str, Any] = {}
        for k, v in spec.items():
            out[aliases.get(k, k)] = v
        return out

    def validate(self, gen_name: str, spec: Mapping[str, Any]) -> Report:
        _ = self.registry.get_class(gen_name)  # raises if unknown
        norm_tree = self.normalizer.normalize(spec)
        aliases = self.registry.get_aliases(gen_name)
        normalized = self._apply_aliases(norm_tree, aliases)
        model = self.models.get(gen_name)
        model_fields = set(getattr(model, 'model_fields', {}).keys())
        extras = [k for k in normalized.keys() if k not in model_fields]
        if extras:
            issues = [ExtraIssue(path=(k,), msg='Extra field not permitted')
                      for k in extras]
            return Report(ok=False, issues=issues, normalized=None)

        try:
            inst = model.model_validate(normalized)
            return Report(ok=True, issues=[], normalized=inst.model_dump())
        except ValidationError as ve:
            issues = from_pydantic_errors(ve.errors())
            return Report(ok=False, issues=issues, normalized=None)
