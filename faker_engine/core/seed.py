from __future__ import annotations
from typing import Optional
from fastapi import Request


def get_request_seed(request: Request, fallback: Optional[int] = None) -> int:
    try:
        if 'x-seed' in request.headers:
            return int(request.headers['x-seed'])
    except Exception:
        pass
    try:
        seed = getattr(request, 'state', None) and getattr(request.state,
                                                           'seed', None)
        if seed is not None:
            return int(seed)
    except Exception:
        pass
    if fallback is not None:
        return int(fallback)
    base = f"{getattr(request, 'method', 'GET')}:{getattr(request, 'url', '')}"
    return abs(hash(base)) % (2 ** 31 - 1)
