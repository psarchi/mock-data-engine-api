from __future__ import annotations

from pprint import pprint
from typing import Mapping, Any

from fastapi import APIRouter, Response
import json

from starlette.responses import JSONResponse

from mock_engine.chaos.access import get_chaos_manager
from mock_engine.config.access import get_config_manager
from mock_engine.context import GenContext
from server.deps import get_generator

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
        return Response(content=bytes(body), status_code=status,
                        headers=headers)

    return Response(content=repr(body), status_code=status, headers=headers)


def wrap_output(body, status: int, headers: dict | None = None):
    if isinstance(body, (bytes, bytearray)):
        b = bytes(body)
        try:
            text = b.decode("utf-8")
        except UnicodeDecodeError:
            text = b.decode("latin-1")
        return JSONResponse({"output": text}, status_code=status,
                            headers=headers or {})

    if isinstance(body, str):
        return JSONResponse({"output": body}, status_code=status,
                            headers=headers or {})

    return JSONResponse({"output": body}, status_code=status,
                        headers=headers or {})


@router.get("/test")
def chaos_test():
    # list of ops
    list_of_ops = ["duplicate_items"]

    # minimal payload
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
    out_resp, _meta = mgr.apply(response=payload, meta_enabled=False,
                                names=list_of_ops)
    body = out_resp.get("body")
    pprint(type(body))
    headers = out_resp.get("headers") or {
        "Content-Type": "application/json; charset=utf-8"}
    return JSONResponse(content=body, status_code=200)


@router.get("/debug")
def chaos_ops():
    """Return the current chaos ops config and registry."""
    cfg = get_config_manager().get_root("chaos")
    mgr = get_chaos_manager(GenContext())
    registry = mgr.registry.items()
    pprint(registry)
    cfg_dict = dict(cfg) if cfg else {}
    cfg_dict.pop("ops_registry", None)
    registry = {k: v.__module__ + "." + v.__name__ for k, v in
                mgr.registry.items()}
    return {"config": cfg_dict, "registry": registry}
