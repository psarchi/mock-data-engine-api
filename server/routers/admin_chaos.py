from __future__ import annotations

from typing import Mapping, Any

from fastapi import APIRouter, Response

from starlette.responses import JSONResponse

from mock_engine.chaos.access import get_chaos_manager
from mock_engine.config.access import get_config_manager
from mock_engine.context import GenContext
from server.deps import get_generator
from server.auth import RequireAuth

router = APIRouter(prefix="/v1/admin/chaos", tags=["admin-chaos"])


def _coerce_headers(h: Mapping[str, Any] | None) -> dict[str, str]:
    if not h:
        return {}
    return {str(k): "" if v is None else str(v) for k, v in h.items()}


def build_chaos_response(out_resp: dict) -> Response:
    status = int(out_resp.get("status", 200))
    headers = _coerce_headers(out_resp.get("headers"))

    body = out_resp.get("body", b"")

    if isinstance(body, (dict, list)):
        return JSONResponse(content=body, status_code=status, headers=headers)

    if isinstance(body, str):
        return Response(content=body, status_code=status, headers=headers)

    if isinstance(body, (bytes, bytearray)):
        return Response(content=bytes(body), status_code=status, headers=headers)

    return Response(content=repr(body), status_code=status, headers=headers)


def wrap_output(body, status: int, headers: dict | None = None):
    if isinstance(body, (bytes, bytearray)):
        b = bytes(body)
        try:
            text = b.decode("utf-8")
        except UnicodeDecodeError:
            text = b.decode("latin-1")
        return JSONResponse({"output": text}, status_code=status, headers=headers or {})

    if isinstance(body, str):
        return JSONResponse({"output": body}, status_code=status, headers=headers or {})

    return JSONResponse({"output": body}, status_code=status, headers=headers or {})


@router.get("/test")
def chaos_test(_token: RequireAuth = None):
    list_of_ops = ["duplicate_items"]
    items = []
    name = "ga4"
    gen = get_generator(name)
    ctx = GenContext()
    for _ in range(1):
        rec = gen.generate(ctx)
        items.append(rec)
    payload = {"body": {"items": items, "count": len(items)}}
    _ = get_config_manager().get_root("chaos")

    mgr = get_chaos_manager(ctx)
    out_resp, _meta = mgr.apply(response=payload, meta_enabled=False, names=list_of_ops)
    body = out_resp.get("body")
    headers = out_resp.get("headers") or {
        "Content-Type": "application/json; charset=utf-8"
    }
    return JSONResponse(content=body, status_code=200)


@router.get("/debug")
def chaos_ops(_token: RequireAuth = None):
    """Return the current chaos ops config and registry."""
    from mock_engine.config.access import ensure_config_fresh

    ensure_config_fresh()
    cfg = get_config_manager().get_root("chaos")
    mgr = get_chaos_manager(GenContext())
    registry = mgr.registry.items()
    cfg_dict = dict(cfg) if cfg else {}
    cfg_dict.pop("ops_registry", None)
    registry = {k: v.__module__ + "." + v.__name__ for k, v in mgr.registry.items()}
    return {"config": cfg_dict, "registry": registry}


@router.post("/clear-drift")
def clear_drift_layers(_token: RequireAuth = None):
    """Clear all drift layers for testing."""
    from mock_engine.chaos.drift import get_drift_coordinator

    coordinator = get_drift_coordinator()
    coordinator._schemas.clear()  # Clear all schema drift states
    return {"status": "ok", "message": "All drift layers cleared"}


@router.post("/reload-config")
def reload_chaos_config(_token: RequireAuth = None):
    """Reload chaos config and reset chaos manager."""
    from mock_engine.config.access import reload_config
    from mock_engine.chaos import access as chaos_access

    # Reload config from disk
    reload_config()

    # Reset chaos manager singleton
    chaos_access._manager = None

    return {"status": "ok", "message": "Chaos config reloaded and manager reset"}


@router.get("/drift-state")
def get_drift_state(_token: RequireAuth = None):
    """Return current drift layer state for all schemas."""
    from mock_engine.chaos.drift import get_drift_coordinator

    coordinator = get_drift_coordinator()

    result = {}
    for schema_name, state in coordinator._schemas.items():
        result[schema_name] = {
            "layering_enabled": state.layering_enabled,
            "current_revision": state.current_revision,
            "cooldown_active": state.cooldown_active,
            "layers": [
                {
                    "strategy": layer.strategy,
                    "index": layer.index,
                    "revision": layer.revision,
                    "hits": layer.hits,
                    "max_hits": layer.max_hits,
                    "approvals": layer.approvals,
                    "request_quota": layer.request_quota,
                    "exhausted": layer.exhausted(),
                    "modifications": layer.modifications,
                }
                for layer in state.layers
            ],
        }
    return result
