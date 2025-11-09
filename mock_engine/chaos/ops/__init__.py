from __future__ import annotations

import importlib
import pkgutil
from types import ModuleType
from typing import List

__all__: List[str] = []

try:
    from mock_engine.chaos.ops.base import BaseChaosOp
except Exception:
    BaseChaosOp = None  # type: ignore


def _export_public_from_module(mod: ModuleType) -> None:
    global __all__
    exported: List[str] = []
    names = getattr(mod, "__all__", None)
    if isinstance(names, (list, tuple)):
        for n in names:
            try:
                globals()[n] = getattr(mod, n)
                exported.append(n)
            except Exception:
                pass
    else:
        if BaseChaosOp is not None:
            for attr, val in vars(mod).items():
                try:
                    if isinstance(val, type) and issubclass(val,
                                                            BaseChaosOp) and val is not BaseChaosOp:
                        globals()[attr] = val
                        exported.append(attr)
                except Exception:
                    continue
    if exported:
        __all__.extend(exported)


def _autoload() -> None:
    pkg_name = __name__
    try:
        pkg = importlib.import_module(pkg_name)
        pkg_path = pkg.__path__  # type: ignore[attr-defined]
    except Exception:
        return
    for _finder, name, _ispkg in pkgutil.walk_packages(pkg_path,
                                                       prefix=pkg_name + "."):
        short = name.rsplit(".", 1)[-1]
        if short.startswith("_"):
            continue
        try:
            mod = importlib.import_module(name)
        except Exception:
            continue
        _export_public_from_module(mod)


_autoload()
