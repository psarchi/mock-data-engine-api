from __future__ import annotations
from typing import Any, Mapping, Sequence
from pydantic import ValidationError as PydanticValidationError
from faker_engine.validator.registry_adapter import RegistryAdapter
from faker_engine.validator.normalizer import SpecNormalizer
from faker_engine.validator.model_provider import ModelProvider
from faker_engine.validator.errors import from_pydantic_errors, ExtraIssue, \
    Issue, IssueCode
from faker_engine.validator.report import Report

JsonPath = tuple[str | int, ...]


class Validator:
    def __init__(self,
                 registry: RegistryAdapter | None = None,
                 normalizer: SpecNormalizer | None = None,
                 models: ModelProvider | None = None,
                 raise_on_fail: bool = False) -> None:
        self.registry = registry or RegistryAdapter()
        self.normalizer = normalizer or SpecNormalizer()
        self.models = models or ModelProvider()
        self.raise_on_fail = raise_on_fail

    # public API
    def validate(self, spec: Any) -> Report:
        normalized = self.normalizer.normalize(spec, path="root")
        issues: list[Issue] = []
        normalized_out: Any = None

        def validate_node(node: Any, path: JsonPath) -> None:
            # Recurse lists
            if isinstance(node, list):
                for index, child in enumerate(node):
                    validate_node(child, path + (index,))
                return
            # Only dicts with a type are generator nodes
            if not isinstance(node, dict) or "type" not in node:
                return

            gen_name = str(node.get("type"))
            try:
                gen_cls, canonical = self.registry.resolve(gen_name)
            except Exception as e:
                issues.append(Issue(code=IssueCode.TYPE, path=path + ("type",),
                                    msg=str(e)))
                return

            model = self.models.get(gen_cls.__name__)

            model_fields = set(getattr(model, "model_fields", {}).keys())
            extras = [k for k in node.keys() if k not in model_fields]
            for k in extras:
                issues.append(ExtraIssue(path=path + (k,),
                                         msg="Extra field not permitted"))

            # Pydantic validation
            try:
                inst = model.model_validate(node)
                # keep normalized representation as the last successfully validated root
                if path == ():
                    nonlocal normalized_out
                    normalized_out = inst.model_dump()
            except PydanticValidationError as ve:
                issues.extend(from_pydantic_errors(ve.errors()))

            cls_name = gen_cls.__name__
            if hasattr(node, "get"):
                if "fields" in node and isinstance(node["fields"], Mapping):
                    for field_name, child_spec in node["fields"].items():
                        validate_node(child_spec,
                                      path + ("fields", field_name))
                # Array-like: single child
                if "child" in node and isinstance(node["child"], (dict, list)):
                    validate_node(node["child"], path + ("child",))
                # Variants / choices
                if "choices" in node and isinstance(node["choices"], Sequence):
                    for idx, child_spec in enumerate(node["choices"]):
                        validate_node(child_spec, path + ("choices", idx))
                # Options mapping (like Select)
                if "options" in node and isinstance(node["options"], Mapping):
                    for opt_name, child_spec in node["options"].items():
                        validate_node(child_spec, path + ("options", opt_name))

        validate_node(normalized, ())

        ok = len(issues) == 0
        report = Report(ok=ok, issues=issues,
                        normalized=(normalized_out if ok else None))
        return report
