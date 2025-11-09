from __future__ import annotations
from typing import Any, Dict, Tuple, Type, List

from mock_engine.chaos.ops.base import BaseChaosOp, ApplyResult
from .registry import get_registry

def _get_op_params_dict(config_root, op_name: str) -> dict:
    """Extract parameters for an op from Pydantic models using getattr(...).__dict__.
    Falls back to empty dict if model is present but has no public fields.
    Raises on missing op config node.
    """
    ops_node = getattr(config_root, "ops", None)
    if ops_node is None:
        raise RuntimeError("Chaos config is missing 'ops' node")
    node = getattr(ops_node, op_name, None)
    if node is None:
        raise RuntimeError(f"Chaos config missing ops.{op_name}")
    params = dict(getattr(node, "__dict__", {}) or {})
    for k in list(params.keys()):
        if k.startswith("model_") or k.startswith("__"):
            params.pop(k, None)
    return params





def _normalize_response(response: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "status": int(response.get("status", 200)),
        "headers": dict(response.get("headers", {}) or {}),
        "body": response.get("body"),
    }


def _ops_mapping(chaos_cfg: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    ops_node = getattr(chaos_cfg, "ops", None)
    if isinstance(ops_node, dict):
        # Expect mapping {name: params}
        out = {}
        for n, params in ops_node.items():
            if isinstance(params, dict):
                out[str(n)] = dict(params)
            else:
                out[str(n)] = {}
        return out
    if isinstance(ops_node, list):
        out: Dict[str, Dict[str, Any]] = {}
        for entry in ops_node:
            if isinstance(entry, str):
                out[entry] = {}
            elif isinstance(entry, dict):
                n = entry.get("name")
                if n:
                    out[str(n)] = {k: v for k, v in entry.items() if
                                   k != "name"}
        return out
    return {}


class ChaosManager:
    def __init__(self, *, ctx, config_snapshot: Dict[str, Any],
                 registry: Dict[str, Type[BaseChaosOp]] | None = None) -> None:
        self.ctx = ctx
        # Expect a dict-like snapshot for fast reads.
        self.cfg = config_snapshot or {}
        self.registry = registry or get_registry()
        self._hits: Dict[str, int] = {}

    def _merge(self, resp: Dict[str, Any], res: ApplyResult) -> None:
        # status
        if getattr(res, "status", None) is not None:
            resp["status"] = int(res.status)  # type: ignore[arg-type]
        # headers
        if getattr(res, "headers", None) is not None:
            resp["headers"] = dict(res.headers)  # type: ignore[arg-type]
        else:
            delta = getattr(res, "headers_delta", None)
            if isinstance(delta, dict):
                h = resp.setdefault("headers", {})
                for k, v in delta.items():
                    if v is None:
                        h.pop(k, None)
                    else:
                        h[k] = v
        # body
        if getattr(res, "body", None) is not None:
            resp["body"] = res.body
        if getattr(res, "descriptions", None) is not None:
            resp["body"]["descriptions"] = res.descriptions

    def apply(self, *, response: Dict[str, Any], meta_enabled: bool,
              names: List[str] | None = None,
              schema_name: str | None = None) -> Tuple[
        Dict[str, Any], Dict[str, Any]]:
        chaos = self.cfg

        # simple fast tests for now

        if names is not None:
            for name in names:
                if name not in self.registry:
                    raise Exception(f"Unknown chaos op {name!r}")
                cfg_key = getattr(self.registry[name], "key", None)
                if cfg_key is None:
                    raise Exception(f"Chaos OP missing key for ops.{name}")
                ops_cls = self.registry[name]
                if ops_cls is None:
                    raise Exception(f"Chaos OP class not found for ops.{name}")
                op = ops_cls(enabled=True)
                body = response.get("body")
                result = op.apply(request=None, response=response, body=body,
                                  rng=self.ctx)
                if not isinstance(result, ApplyResult):
                    continue
                self._merge(response, result)

            return response, {}

