from __future__ import annotations
from pathlib import Path
from typing import Optional

from faker_engine.config.manager import ConfigManager

_SINGLETON: Optional[ConfigManager] = None


def get_config_manager(
        project_root: Path | str | None = None) -> ConfigManager:
    global _SINGLETON
    if _SINGLETON is None:
        root = Path(project_root or Path(__file__).resolve().parents[
            2])  # project root
        _SINGLETON = ConfigManager(project_root=root)
    return _SINGLETON
