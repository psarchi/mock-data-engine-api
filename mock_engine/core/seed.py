from __future__ import annotations

from fastapi import Request

# TODO(constants): promote header name to a shared constants module if reused elsewhere
SEED_HEADER_NAME: str = "x-seed"
# TODO(constants): consider sharing with other hashing/seed utilities
MAX_SIGNED_31: int = 2_147_483_647  # 2**31 - 1


# TODO: unused; planned for future use
def get_request_seed(request: Request, fallback: int | None = None) -> int:
    """Return a deterministic seed for this request.

    Resolution order:
    1) ``X-Seed`` request header (string cast to ``int``)
    2) ``request.state.seed`` (string/number cast to ``int``)
    3) ``fallback`` if provided
    4) fingerprint of ``{method}:{url}`` hashed and truncated to a 31-bit signed range

    Args:
        request (Request): Incoming FastAPI request.
        fallback (int | None): Optional explicit fallback seed.

    Returns:
        int: Deterministic seed value.
    """
    # 1) Header override (FastAPI headers are case-insensitive)
    seed_header = request.headers.get(SEED_HEADER_NAME)
    if seed_header is not None:
        try:
            return int(seed_header)
        except (TypeError, ValueError):
            # TODO(errors): consider raising a typed error if strict parsing is desired
            pass

    # 2) request.state.seed
    state_seed = getattr(getattr(request, "state", None), "seed", None)
    if state_seed is not None:
        try:
            return int(state_seed)
        except (TypeError, ValueError):
            # TODO(errors): consider raising a typed error if strict parsing is desired
            pass

    # 3) explicit fallback
    if fallback is not None:
        return int(fallback)

    # 4) stable fingerprint of method+url
    fingerprint_base = f"{getattr(request, 'method', 'GET')}:{getattr(request, 'url', '')}"
    return abs(hash(fingerprint_base)) % MAX_SIGNED_31
