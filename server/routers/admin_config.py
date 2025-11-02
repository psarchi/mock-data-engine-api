"""Admin configuration API routes.

Exposes endpoints under ``/v1/admin`` to inspect and modify the running
configuration. Behavior preserved; only docs/typing/names were cleaned to
match the golden style.
"""
from __future__ import annotations

from typing import Any, Mapping

from fastapi import APIRouter, Body, Header

from faker_engine.config import get_config_manager
# TODO(refractor): full refractor of admin endpoints I don't like how it is organized
router = APIRouter(prefix="/v1/admin", tags=["admin"])


def _assert_admin_enabled() -> None:
    """Ensure administrative endpoints are permitted.

    Raises:
        HTTPException: When admin access is disabled. (Not enforced yet.)
    """
    # TODO(auth): Enforce an "admin_enabled"/auth check once config policy is finalized.
    _manager = get_config_manager()
    _ = _manager.effective()  # Touch to ensure config loads; keep behavior unchanged.


@router.get("/config")
def get_config() -> object:
    """Return the current effective configuration and overrides.

    Returns:
        object: A mapping with revision, effective model (``model_dump()``),
            overrides, and source flags.
    """
    _assert_admin_enabled()
    manager = get_config_manager()
    effective = manager.effective()
    return {
        "revision": manager.revision(),
        "effective": effective.model_dump(),
        "overrides": manager.overrides(),
        "source": {"default.yaml": True, "overrides.yaml": True},
    }


@router.get("/config/diff")
def get_config_diff() -> object:
    """Return a diff-style view (overrides + effective model dump).

    Returns:
        object: ``{"overrides": ..., "effective": ...}``.
    """
    _assert_admin_enabled()
    manager = get_config_manager()
    return {"overrides": manager.overrides(), "effective": manager.effective().model_dump()}


@router.put("/config")
def replace_config(
    payload: Mapping[str, object] = Body(...),
    x_actor: str | None = Header(None),
) -> object:
    """Replace the full configuration with ``payload``.

    Args:
        payload (Mapping[str, object]): Incoming configuration payload.
        x_actor (str | None): Optional actor identifier from the ``X-Actor`` header.

    Returns:
        object: Result of applying the replacement.
    """
    _assert_admin_enabled()
    return get_config_manager().apply_replace(dict(payload), actor=x_actor or "api")


@router.patch("/config")
def patch_config(
    payload: Mapping[str, object] = Body(...),
    x_actor: str | None = Header(None),
) -> object:
    """Apply a partial configuration ``payload``.

    Args:
        payload (Mapping[str, object]): Patch document to merge into config.
        x_actor (str | None): Optional actor identifier from the ``X-Actor`` header.

    Returns:
        object: Result of applying the patch.
    """
    _assert_admin_enabled()
    return get_config_manager().apply_patch(dict(payload), actor=x_actor or "api")


@router.post("/config/dry-run")
def dry_run_config(payload: Mapping[str, object] = Body(...)) -> object:
    """Validate a configuration ``payload`` without persisting changes.

    Args:
        payload (Mapping[str, object]): Candidate configuration to validate.

    Returns:
        object: Validation result/report.
    """
    _assert_admin_enabled()
    return get_config_manager().dry_run(dict(payload))


@router.post("/config/reset")
def reset_config(x_actor: str | None = Header(None)) -> object:
    """Reset all overrides to defaults.

    Args:
        x_actor (str | None): Optional actor identifier from the ``X-Actor`` header.

    Returns:
        object: Result of resetting overrides.
    """
    _assert_admin_enabled()
    return get_config_manager().reset_overrides(actor=x_actor or "api")


@router.get("/config/schema")
def get_config_schema() -> object:
    """Return the config schema metadata and JSON Schema.

    Returns:
        object: ``{"meta": ..., "json_schema": ...}``.
    """
    _assert_admin_enabled()
    manager = get_config_manager()
    return {"meta": manager.meta(), "json_schema": manager.json_schema()}
