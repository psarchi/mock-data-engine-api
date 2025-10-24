
from __future__ import annotations
from typing import Any, Mapping, Dict
from pathlib import Path
import json, os, time, threading

from pydantic import BaseModel

from faker_engine.config.schema import validate_default_yaml_schema
from faker_engine.config.builder import build_model_from_default

try:
    import yaml  # type: ignore
except Exception:
    yaml = None  # will raise on load

class ConfigManager:
    def __init__(self, project_root: Path | str) -> None:
        self._root = Path(project_root)
        self._default_path = self._root / "config" / "default.yaml"
        self._overrides_path = self._root / "config" / "overrides.yaml"
        self._rev_path = self._root / "config" / ".overrides_rev"
        self._audit_path = self._root / "config" / "audit.log"
        self._lock = threading.RLock()
        self._revision = 0
        self._model_cls: type[BaseModel] | None = None
        self._meta_tree: Dict[str, Any] = {}
        self._defaults_tree: Dict[str, Any] = {}
        self._effective: BaseModel | None = None
        self._overrides: Dict[str, Any] = {}
        self.reload()

    @staticmethod
    def _deep_merge(base: Mapping[str, Any], add: Mapping[str, Any]) -> Dict[str, Any]:
        out: Dict[str, Any] = json.loads(json.dumps(base))
        for k, v in (add or {}).items():
            if isinstance(v, dict) and isinstance(out.get(k), dict):
                out[k] = ConfigManager._deep_merge(out[k], v)  # type: ignore[index]
            else:
                out[k] = v
        return out

    @staticmethod
    def _atomic_write(path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        tmp.replace(path)

    def _load_yaml(self, path: Path) -> Dict[str, Any]:
        if not path.exists():
            return {}
        if yaml is None:
            raise RuntimeError("PyYAML is required to load config files")
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
            if not isinstance(data, dict):
                raise ValueError(f"Config file {path} must be a mapping at top-level")
            return data

    def reload(self) -> None:
        with self._lock:
            base = self._load_yaml(self._default_path)
            validate_default_yaml_schema(base)
            model_cls, defaults, meta = build_model_from_default(base)
            self._model_cls = model_cls
            self._meta_tree = meta
            self._defaults_tree = defaults
            overrides = self._load_yaml(self._overrides_path)
            merged = self._deep_merge(defaults, overrides)
            self._effective = model_cls.model_validate(merged)
            self._overrides = overrides
            try:
                if self._rev_path.exists():
                    self._revision = int(self._rev_path.read_text(encoding="utf-8").strip() or "0")
            except Exception:
                self._revision = 0

    def effective(self) -> BaseModel:
        assert self._effective is not None
        return self._effective

    def overrides(self) -> Dict[str, Any]:
        return json.loads(json.dumps(self._overrides))

    def revision(self) -> int:
        return self._revision

    def meta(self) -> Dict[str, Any]:
        return json.loads(json.dumps(self._meta_tree))

    def json_schema(self) -> Dict[str, Any]:
        assert self._model_cls is not None
        try:
            return self._model_cls.model_json_schema()
        except Exception:
            return {}

    def _bump_revision(self) -> int:
        self._revision += 1
        ConfigManager._atomic_write(self._rev_path, str(self._revision))
        return self._revision

    def _write_overrides(self, overrides: Mapping[str, Any]) -> None:
        if yaml is None:
            raise RuntimeError("PyYAML is required to persist config overrides")
        import yaml as _yaml  # local alias
        ConfigManager._atomic_write(self._overrides_path, _yaml.safe_dump(dict(overrides), sort_keys=True, allow_unicode=True))

    def _audit(self, actor: str, operation: str, payload: Mapping[str, Any], new_revision: int) -> None:
        event = {"ts": time.time(), "actor": actor, "op": operation, "revision": new_revision, "payload": payload}
        line = json.dumps(event, ensure_ascii=False)
        self._audit_path.parent.mkdir(parents=True, exist_ok=True)
        with self._audit_path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    def apply_replace(self, new_overrides: Mapping[str, Any], actor: str = "system") -> Dict[str, Any]:
        with self._lock:
            merged = self._deep_merge(self._defaults_tree, dict(new_overrides))
            eff = self._model_cls.model_validate(merged)  # type: ignore[union-attr]
            self._write_overrides(new_overrides)
            self._overrides = dict(new_overrides)
            self._effective = eff
            rev = self._bump_revision()
            self._audit(actor, "replace", dict(new_overrides), rev)
            return {"revision": rev, "effective": eff.model_dump()}

    def apply_patch(self, partial_overrides: Mapping[str, Any], actor: str = "system") -> Dict[str, Any]:
        with self._lock:
            patched = self._deep_merge(self._overrides, dict(partial_overrides))
            merged = self._deep_merge(self._defaults_tree, patched)
            eff = self._model_cls.model_validate(merged)  # type: ignore[union-attr]
            self._write_overrides(patched)
            self._overrides = patched
            self._effective = eff
            rev = self._bump_revision()
            self._audit(actor, "patch", dict(partial_overrides), rev)
            return {"revision": rev, "effective": eff.model_dump()}

    def dry_run(self, payload: Mapping[str, Any]) -> Dict[str, Any]:
        with self._lock:
            trial = self._deep_merge(self._overrides, dict(payload))
            merged = self._deep_merge(self._defaults_tree, trial)
            result: Dict[str, Any] = {"ok": True, "errors": []}
            try:
                eff = self._model_cls.model_validate(merged)  # type: ignore[union-attr]
                result["effective"] = eff.model_dump()
            except Exception as exc:
                result["ok"] = False
                result["errors"] = [str(exc)]
            return result

    def reset_overrides(self, actor: str = "system") -> Dict[str, Any]:
        with self._lock:
            self._write_overrides({})
            self._overrides = {}
            eff = self._model_cls.model_validate(self._defaults_tree)  # type: ignore[union-attr]
            self._effective = eff
            rev = self._bump_revision()
            self._audit(actor, "reset", {}, rev)
            return {"revision": rev, "effective": eff.model_dump()}
