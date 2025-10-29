from __future__ import annotations

from typing import Mapping

from mock_engine.constants import ExtrasPolicy  # noqa: F401


# TODO(arch): Consolidate on a single validator entrypoint and remove fallbacks.
# TODO(compat): Keep legacy fallbacks until all callers migrate.
# TODO Unused!
def validate(
    spec: Mapping[str, object],
    *,
    policy: ExtrasPolicy = ExtrasPolicy.FORBID,
    **kwargs: object,
) -> object:
    """Validate input against the configured schema.

    Args:
        spec (Mapping[str, object]): Specification mapping parsed from configuration.
        policy (ExtrasPolicy): Policy for handling extra fields.
        **kwargs (object): Additional keyword arguments forwarded to the validator.

    Returns:
        object: Validation report or result object from the active validator.

    Raises:
        RuntimeError: If no validator entrypoint is available.
    """
    ignore_extras = policy is ExtrasPolicy.ALLOW

    _fn = globals().get("_validate") or globals().get("validate_internal")
    if _fn is not None:
        try:
            return _fn(spec, ignore_extras=ignore_extras, **kwargs)  # type: ignore[misc]
        except TypeError:
            return _fn(spec, **kwargs)  # type: ignore[misc]

    legacy = (
        globals().get("legacy_validate")
        or globals().get("validate_legacy")
        or globals().get("validate")
    )
    if legacy is None:
        raise RuntimeError("No validator entrypoint found")
    try:
        return legacy(spec, ignore_extras=ignore_extras, **kwargs)  # type: ignore[misc]
    except TypeError:
        return legacy(spec, **kwargs)  # type: ignore[misc]
