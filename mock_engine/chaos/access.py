from __future__ import annotations

from threading import Lock
from typing import Optional

from .manager import ChaosManager
from .ops.base import BaseChaosOp
from mock_engine.config.access import get_config_manager
from mock_engine.context import GenContext
from mock_engine.registry import Registry

_manager: Optional[ChaosManager] = None
_lock = Lock()


def get_chaos_manager(ctx=None) -> ChaosManager:
    """Return a singleton ChaosManager.
    If ctx is provided, attach its RNG to the existing manager.
    """
    # TODO: better way, refractor
    global _manager
    if _manager is None:
        with _lock:
            if _manager is None:
                chaos_cfg = get_config_manager().get_root("chaos")
                reg = Registry.get_all(BaseChaosOp)
                _manager = ChaosManager(
                    ctx=ctx or GenContext(),
                    config_snapshot=chaos_cfg,
                    registry=reg,
                )
                return _manager
    if ctx is not None:
        try:
            _manager.ctx = ctx  # type: ignore[attr-defined]
            _manager.rng = getattr(ctx, "rng", ctx)
        except Exception:
            setattr(_manager, "ctx", ctx)  # type: ignore[attr-defined]
    return _manager  # type: ignore[return-value]
