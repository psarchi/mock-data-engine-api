from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Dict, Mapping

from pydantic import BaseModel

from mock_engine.contracts import (
    ArrayGeneratorSpec,
    MaybeGeneratorSpec,
    ObjectGeneratorSpec,
    ObjectOrNullGeneratorSpec,
    OneOfGeneratorSpec,
    SelectGeneratorSpec,
    StringOrNullGeneratorSpec,
)

if TYPE_CHECKING:  # only for type hints to avoid circular import at runtime
    from .validator import Validator

HandlerFn = Callable[["Validator", str, Mapping[str, Any], str], BaseModel]

_HANDLERS: Dict[str, HandlerFn] = {}


def schema_handler(contract_cls):
    """Decorator registering ``contract_cls`` tokens to ``handler``."""

    def decorator(fn: HandlerFn) -> HandlerFn:
        tokens = {getattr(contract_cls, "type_token", "").strip().lower()}
        for alias in getattr(contract_cls, "type_aliases", set()) or ():
            if isinstance(alias, str):
                tokens.add(alias.strip().lower())
        for token in filter(None, tokens):
            _HANDLERS[token] = fn
        return fn

    return decorator


def get_handlers() -> Dict[str, HandlerFn]:
    """Return the registered schema handlers."""
    return dict(_HANDLERS)


def _child_path(base_path: str, suffix: str) -> str:
    return f"{base_path}{suffix}" if base_path else suffix.lstrip(".")


@schema_handler(ObjectGeneratorSpec)
def handle_object(
        validator: "Validator",
        token: str,
        payload: Mapping[str, Any],
        path: str,
) -> BaseModel:
    fields_raw = validator._coerce_map(payload.get("fields"), f"{path}.fields")
    fields_conv: Dict[str, Any] = {}
    for key, raw in fields_raw.items():
        child_path = _child_path(path, f".{key}")
        fields_conv[key] = validator._read_node(
            validator._ensure_map(raw, child_path), child_path)
    payload = {**payload, "fields": fields_conv}
    return validator._instantiate(token, payload, path)


@schema_handler(ArrayGeneratorSpec)
def handle_array(
        validator: "Validator",
        token: str,
        payload: Mapping[str, Any],
        path: str,
) -> BaseModel:
    data = dict(payload)
    child = data.get("child")
    if child is not None:
        child_path = _child_path(path, "[]")
        data["child"] = validator._read_node(
            validator._ensure_map(child, child_path), child_path)
    min_items = data.get("min_items")
    max_items = data.get("max_items")
    if min_items is not None and max_items is not None:
        try:
            if int(min_items) > int(max_items):
                raise ValueError("min_items > max_items")
        except Exception as exc:
            raise ValueError(f"{path}: {exc}")
    return validator._instantiate(token, data, path)


@schema_handler(OneOfGeneratorSpec)
def handle_one_of(
        validator: "Validator",
        token: str,
        payload: Mapping[str, Any],
        path: str,
) -> BaseModel:
    choices_raw = validator._coerce_list(payload.get("choices"),
                                         f"{path}.choices")
    if not choices_raw:
        raise ValueError(f"{path}.choices: must be non-empty")
    choices_conv = [
        validator._read_node(validator._ensure_map(choice, f"{path}|{idx}"),
                             f"{path}|{idx}")
        for idx, choice in enumerate(choices_raw)
    ]
    data = {**payload, "choices": choices_conv}
    weights = data.get("weights")
    if weights is not None:
        if not isinstance(weights, list):
            raise TypeError(f"{path}.weights: expected list")
        if len(weights) != len(choices_conv):
            raise ValueError(
                f"{path}.weights: length must equal choices length")
        for idx, weight in enumerate(weights):
            if not isinstance(weight, (int, float)):
                raise TypeError(f"{path}.weights[{idx}]: must be number")
            if weight < 0:
                raise ValueError(f"{path}.weights[{idx}]: must be >= 0")
    return validator._instantiate(token, data, path)


@schema_handler(MaybeGeneratorSpec)
def handle_maybe(
        validator: "Validator",
        token: str,
        payload: Mapping[str, Any],
        path: str,
) -> BaseModel:
    data = dict(payload)
    child = data.get("child")
    if child is not None:
        child_path = _child_path(path, ".?")
        data["child"] = validator._read_node(
            validator._ensure_map(child, child_path), child_path)
    p_null = data.get("p_null")
    if p_null is not None:
        if not isinstance(p_null, (int, float)):
            raise TypeError(f"{path}.p_null: must be number between 0 and 1")
        if not (0 <= float(p_null) <= 1):
            raise ValueError(f"{path}.p_null: must be within [0,1]")
    return validator._instantiate(token, data, path)


@schema_handler(SelectGeneratorSpec)
def handle_select(
        validator: "Validator",
        token: str,
        payload: Mapping[str, Any],
        path: str,
) -> BaseModel:
    options_raw = validator._coerce_map(payload.get("options"),
                                        f"{path}.options")
    options_conv: Dict[str, Any] = {}
    for key, raw in options_raw.items():
        child_path = _child_path(path, f".{key}")
        options_conv[key] = validator._read_node(
            validator._ensure_map(raw, child_path), child_path)
    data = {**payload, "options": options_conv}
    return validator._instantiate(token, data, path)


@schema_handler(ObjectOrNullGeneratorSpec)
@schema_handler(StringOrNullGeneratorSpec)
def handle_nullable(
        validator: "Validator",
        token: str,
        payload: Mapping[str, Any],
        path: str,
) -> BaseModel:
    data = dict(payload)
    child = data.get("child")
    if child is not None:
        child_path = _child_path(path, ".?")
        data["child"] = validator._read_node(
            validator._ensure_map(child, child_path), child_path)
    return validator._instantiate(token, data, path)
