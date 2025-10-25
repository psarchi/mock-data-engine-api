from __future__ import annotations
from typing import Any, Callable, Dict, List, Optional, Tuple
import random
from starlette.types import ASGIApp, Receive, Scope, Send
from starlette.responses import Response

from faker_engine.chaos.config import ChaosConfigView
from faker_engine.chaos.manager import ChaosManager
from faker_engine.chaos.types import ChaosScope
from faker_engine.chaos.registry import build_ops_registry


def default_scope_resolver(scope: Scope) -> ChaosScope:
    path = scope.get('path', '') or ''
    if path.startswith('/v1/admin'):
        return 'admin'
    if path.startswith('/v1/validate'):
        return 'validate'
    if path.startswith('/v1/schemas'):
        return 'generate' if path.endswith('/generate') else 'schema'
    return 'schema'


def _seed_from_scope(scope: Scope) -> int:
    rid = None
    headers: List[Tuple[bytes, bytes]] = scope.get('headers') or []
    for k, v in headers:
        if k.lower() == b'x-request-id':
            rid = v.decode('latin-1', errors='ignore')
            break
    base = f"{scope.get('method', 'GET')}:{scope.get('path', '/')}:{rid or ''}"
    return abs(hash(base)) % (2 ** 31 - 1)


class _Ctx:
    def __init__(self):
        self.meta: Dict[str, Any] = {}


class ChaosRequestMiddleware:
    def __init__(self, app: ASGIApp, cfg: Dict[str, Any],
                 scope_resolver: Optional[
                     Callable[[Scope], ChaosScope]] = None):
        self.app = app
        self.cfg_view = ChaosConfigView(cfg)
        self.scope_resolver = scope_resolver or default_scope_resolver

        # Load only ops that are present under features.chaos.ops in config (lazy import)
        op_names = list((cfg.get('features', {}).get('chaos', {}).get('ops',
                                                                      {}) or {}).keys())
        self.ops_registry = build_ops_registry(op_names)

    async def __call__(self, scope: Scope, receive: Receive,
                       send: Send) -> None:
        if scope['type'] != 'http':
            await self.app(scope, receive, send)
            return

        scope_kind = self.scope_resolver(scope)
        rng = random.Random(_seed_from_scope(scope))

        ctx = _Ctx()
        mgr = ChaosManager(cfg=self.cfg_view, ops_registry=self.ops_registry,
                           rng=rng)

        early = mgr.apply_request(scope_kind, ctx, scope)
        if isinstance(early, Response):
            await early(scope, receive, send)
            return

        scope = self._mutate_headers(scope, ctx, rng)
        await self.app(scope, receive, send)

    def _mutate_headers(self, scope: Scope, ctx: _Ctx,
                        rng: random.Random) -> Scope:
        headers: List[Tuple[bytes, bytes]] = list(scope.get('headers') or [])
        auth = getattr(ctx, '_chaos_auth', None)
        if isinstance(auth, dict):
            mode = auth.get('mode')
            if mode == 'drop':
                headers = [(k, v) for (k, v) in headers if
                           k.lower() != b'authorization']
            elif mode == 'invalid':
                new_headers: List[Tuple[bytes, bytes]] = []
                replaced = False
                for k, v in headers:
                    if k.lower() == b'authorization':
                        new_headers.append((k, b'Bearer invalid.mock.token'))
                        replaced = True
                    else:
                        new_headers.append((k, v))
                if not replaced:
                    new_headers.append(
                        (b'authorization', b'Bearer invalid.mock.token'))
                headers = new_headers

        chaos_meta = getattr(ctx, 'meta', None)
        if isinstance(chaos_meta, dict):
            info = chaos_meta.get('chaos', {}).get('request_header_anomaly')
            if isinstance(info, dict):
                pattern = info.get('pattern')
                if pattern == 'huge_value':
                    size = int(info.get('size', 8192))
                    headers.append((info.get('header', 'X-Debug-Blob').encode(
                        'latin-1'), (b'X' * size)))
                elif pattern == 'non_ascii':
                    headers.append((info.get('header', 'X-NonAscii').encode(
                        'latin-1'), b'\xff\xfe'))
                elif pattern == 'dup_keys':
                    key = info.get('header', 'X-Dup-Key').encode('latin-1')
                    count = max(2, int(info.get('count', 2)))
                    for _ in range(count):
                        headers.append((key, b'dup'))

        new_scope = dict(scope)
        new_scope['headers'] = headers
        return new_scope
