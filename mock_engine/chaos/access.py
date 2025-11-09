from __future__ import annotations

from threading import Lock
from typing import Optional

from .manager import ChaosManager
from .registry import get_registry
from mock_engine.config.access import get_config_manager

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
                reg = get_registry()
                rng = getattr(ctx, "rng", None) if ctx is not None else None
                _manager = ChaosManager(ctx=rng, config_snapshot=chaos_cfg,
                                        registry=reg)
                return _manager
    if ctx is not None:
        try:
            _manager.rng = getattr(ctx, "rng")  # type: ignore[attr-defined]
        except Exception:
            pass
    return _manager  # type: ignore[return-value]
