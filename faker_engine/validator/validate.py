from __future__ import annotations
from .types import Report, Issue, Ctx


def validate_spec(spec, ctx) -> Report:
    return Report(errors=[], warnings=[])


def validate_generator(name, data, ctx) -> Report:
    return Report(errors=[], warnings=[])
