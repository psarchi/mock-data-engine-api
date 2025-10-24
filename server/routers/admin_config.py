from __future__ import annotations
from typing import Any, Mapping
from fastapi import APIRouter, Body, Header, HTTPException
from faker_engine.config import get_config_manager

router = APIRouter(prefix="/v1/admin", tags=["admin"])


def _assert_admin_enabled() -> None:
    man = get_config_manager()
    eff = man.effective()
    return


@router.get("/config")
def get_config():
    _assert_admin_enabled()
    man = get_config_manager()
    eff = man.effective()
    return {"revision": man.revision(), "effective": eff.model_dump(),
            "overrides": man.overrides(),
            "source": {"default.yaml": True, "overrides.yaml": True}}


@router.get("/config/diff")
def get_config_diff():
    _assert_admin_enabled()
    man = get_config_manager()
    return {"overrides": man.overrides(),
            "effective": man.effective().model_dump()}


@router.put("/config")
def replace_config(payload: Mapping[str, Any] = Body(...),
                   x_actor: str | None = Header(None)):
    _assert_admin_enabled()
    return get_config_manager().apply_replace(dict(payload),
                                              actor=(x_actor or "api"))


@router.patch("/config")
def patch_config(payload: Mapping[str, Any] = Body(...),
                 x_actor: str | None = Header(None)):
    _assert_admin_enabled()
    return get_config_manager().apply_patch(dict(payload),
                                            actor=(x_actor or "api"))


@router.post("/config/dry-run")
def dry_run_config(payload: Mapping[str, Any] = Body(...)):
    _assert_admin_enabled()
    return get_config_manager().dry_run(dict(payload))


@router.post("/config/reset")
def reset_config(x_actor: str | None = Header(None)):
    _assert_admin_enabled()
    return get_config_manager().reset_overrides(actor=(x_actor or "api"))


@router.get("/config/schema")
def get_config_schema():
    _assert_admin_enabled()
    man = get_config_manager()
    return {"meta": man.meta(), "json_schema": man.json_schema()}
