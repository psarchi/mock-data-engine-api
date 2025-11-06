"""Chaos request middleware.

Injects controlled randomness into requests/responses based on a configured
chaos profile. Behavior is preserved; docstrings/typing/TODOs updated to
match the golden style.
"""
from __future__ import annotations

from collections.abc import Callable, Iterable
from random import Random
from typing import Any, Optional
import random

from starlette.responses import Response
from starlette.types import ASGIApp, Receive, Scope, Send

from mock_engine.chaos.config import ChaosConfigView
from mock_engine.chaos.manager import ChaosManager
from mock_engine.chaos.registry import build_ops_registry
from mock_engine.chaos.types import ChaosScope


# TODO: Probably want to make this pluggable/configurable at some point.
def default_scope_resolver(scope: Scope) -> ChaosScope:
    """Return the chaos scope for a given ASGI ``scope``.

    Args:
        scope (Scope): ASGI scope to evaluate.

    Returns:
        ChaosScope: One of ``"admin"``, ``"validate"``, ``"schema"``, or ``"generate"``.
    """
    path = (scope.get("path", "") or "").lower()
    if path.startswith("/v1/admin"):
        return "admin"
    if path.startswith("/v1/validate"):
        return "validate"
    if path.startswith("/v1/schemas"):
        return "generate" if path.endswith("/generate") else "schema"
    return "schema"


def _extract_header(headers: Iterable[tuple[bytes, bytes]] | None, name: bytes) -> Optional[str]:
    """Extract a header value by case-insensitive name.

    Args:
        headers (Iterable[tuple[bytes, bytes]] | None): ASGI-style header list.
        name (bytes): Canonical header name in bytes (e.g., ``b"x-seed"``).

    Returns:
        str | None: Decoded header value (``latin-1``) or ``None`` if not found/decodable.
    """
    if not headers:
        return None
    lname = name.lower()
    for key, value in headers:
        if key.lower() == lname:
            try:
                return value.decode("latin-1")
            except Exception:  # noqa: BLE001 (kept behavior)
                # TODO(errors): Narrow to UnicodeDecodeError once headers are normalized.
                return None
    return None


def _seed_from_scope(scope: Scope) -> int:
    """Derive a deterministic seed from headers or scope.

    Prefers the ``x-seed`` header (integer). Otherwise derives a seed from
    ``method:path:request-id`` for stability across retries.

    Args:
        scope (Scope): ASGI scope to inspect.

    Returns:
        int: Deterministic 31-bit positive integer seed.
    """
    headers: list[tuple[bytes, bytes]] = scope.get("headers") or []
    incoming_seed = _extract_header(headers, b"x-seed")
    if incoming_seed:
        try:
            return int(incoming_seed)
        except Exception:  # noqa: BLE001 (kept behavior)
            # Fall through to derived seed when header is malformed.
            pass
    request_id = _extract_header(headers, b"x-request-id") or ""
    seed_base = f"{scope.get('method', 'GET')}:{scope.get('path', '/')}:{request_id}"
    return abs(hash(seed_base)) % (2**31 - 1)


class _RequestCtx:
    """Lightweight context bag for chaos metadata.

    Attributes:
        meta (dict[str, Any]): Free-form metadata emitted into the response path.
    """

    __slots__ = ("meta",)

    def __init__(self) -> None:
        """Initialize an empty metadata map."""
        self.meta: dict[str, Any] = {}


class ChaosRequestMiddleware:
    """ASGI middleware that applies chaos operations per-request.

    Args:
        app (ASGIApp): Downstream ASGI application.
        cfg (dict[str, Any]): Raw configuration mapping.
        scope_resolver (Callable[[Scope], ChaosScope] | None): Optional resolver for
            mapping ASGI scope to a chaos scope. Defaults to :func:`default_scope_resolver`.
    """

    __slots__ = ("app", "cfg_view", "scope_resolver", "ops_registry")

    def __init__(
        self,
        app: ASGIApp,
        cfg: dict[str, Any],
        scope_resolver: Optional[Callable[[Scope], ChaosScope]] = None,
    ) -> None:
        """Initialize middleware and build the ops registry.

        Args:
            app (ASGIApp): Downstream ASGI application.
            cfg (dict[str, Any]): Raw configuration mapping.
            scope_resolver (Callable[[Scope], ChaosScope] | None): Optional scope resolver.
        """
        self.app = app
        self.cfg_view = ChaosConfigView(cfg)
        self.scope_resolver = scope_resolver or default_scope_resolver
        op_names = list((cfg.get("features", {}).get("chaos", {}).get("ops", {}) or {}).keys())
        self.ops_registry = build_ops_registry(op_names)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Process a request and optionally mutate headers/response.

        Args:
            scope (Scope): ASGI scope for the request.
            receive (Receive): ASGI receive callable.
            send (Send): ASGI send callable.
        """
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        scope_kind = self.scope_resolver(scope)
        seed = _seed_from_scope(scope)
        rng = random.Random(seed)

        state = scope.setdefault("state", {})
        state["seed"] = seed

        ctx = _RequestCtx()
        ctx.meta["seed"] = seed
        seed_source = "header" if _extract_header(scope.get("headers"), b"x-seed") else "derived"
        ctx.meta.setdefault("chaos", {})["seed_source"] = seed_source

        mgr = ChaosManager(cfg=self.cfg_view, ops_registry=self.ops_registry, rng=rng)
        early = mgr.apply_request(scope_kind, ctx, scope)
        if isinstance(early, Response):
            async def send_with_seed(message: dict[str, Any]) -> None:
                """Send a pre-built response, forcing ``x-seed`` header.

                Args:
                    message (dict[str, Any]): ASGI message (``http.response.start`` expected).
                """
                if message.get("type") == "http.response.start":
                    headers = message.setdefault("headers", [])
                    headers.append((b"x-seed", str(seed).encode("latin-1")))
                await early(scope, receive, send)

            await send_with_seed({"type": "http.response.start"})
            return

        scope = self._mutate_headers(scope, ctx, rng)

        async def send_wrapper(message: dict[str, Any]) -> None:
            """Append ``x-seed`` header to the outbound response.

            Args:
                message (dict[str, Any]): ASGI message.
            """
            if message.get("type") == "http.response.start":
                headers = message.get("headers")
                if headers is None:
                    message["headers"] = [(b"x-seed", str(seed).encode("latin-1"))]
                else:
                    message["headers"] = list(headers) + [
                        (b"x-seed", str(seed).encode("latin-1"))
                    ]
            await send(message)

        await self.app(scope, receive, send_wrapper)

    def _mutate_headers(self, scope: Scope, ctx: _RequestCtx, rng: Random) -> Scope:
        """Apply chaos header mutations to the ASGI ``scope``.

        Args:
            scope (Scope): Original ASGI scope.
            ctx (_RequestCtx): Request-scoped chaos context.
            rng (Random): Deterministic RNG (may be used by future strategies).

        Returns:
            Scope: New scope with possibly modified ``headers``.
        """
        headers: list[tuple[bytes, bytes]] = list(scope.get("headers") or [])
        # TODO: move strategies to more generic plugin system
        # Authorization header chaos
        chaos_auth = getattr(ctx, "_chaos_auth", None)
        if isinstance(chaos_auth, dict):
            mode = chaos_auth.get("mode")
            if mode == "drop":
                headers = [(k, v) for (k, v) in headers if k.lower() != b"authorization"]
            elif mode == "invalid":
                updated: list[tuple[bytes, bytes]] = []
                replaced = False
                for key, value in headers:
                    if key.lower() == b"authorization":
                        updated.append((key, b"Bearer invalid.mock.token"))
                        replaced = True
                    else:
                        updated.append((key, value))
                if not replaced:
                    updated.append((b"authorization", b"Bearer invalid.mock.token"))
                headers = updated
        # TODO: move to a proper plugin system
        # Request header anomaly chaos
        chaos_meta = getattr(ctx, "meta", None)
        if isinstance(chaos_meta, dict):
            info = chaos_meta.get("chaos", {}).get("request_header_anomaly")
            if isinstance(info, dict):
                pattern = info.get("pattern")
                if pattern == "huge_value":
                    size = int(info.get("size", 8192))
                    header_name = info.get("header", "X-Debug-Blob").encode("latin-1")
                    headers.append((header_name, b"X" * size))
                elif pattern == "non_ascii":
                    header_name = info.get("header", "X-NonAscii").encode("latin-1")
                    headers.append((header_name, b'\xff\xfe'))
                elif pattern == "dup_keys":
                    header_name = info.get("header", "X-Dup-Key").encode("latin-1")
                    count = max(2, int(info.get("count", 2)))
                    for _ in range(count):
                        headers.append((header_name, b"dup"))

        new_scope = dict(scope)
        new_scope["headers"] = headers
        return new_scope
