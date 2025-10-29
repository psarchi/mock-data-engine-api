from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
import json
import os
import threading
import time
from typing import Any

from pydantic import BaseModel

from faker_engine.config.schema import validate_default_yaml_schema
from faker_engine.config.builder import build_model_from_default

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None  # type: ignore


class ConfigManager:
    """Configuration manager for default/override YAML, validation, and effective model.
        Responsibilities
        - Load and validate the default configuration (YAML)
        - Read/write overrides with atomic persistence, revisioning, and audit log
        - Build a Pydantic model from the default spec and validate the merged view"""

    def __init__(self, project_root: Path | str) -> None:
        """Initialize the configuration manager.

        Args:
            project_root (Path | str): Project root directory containing the
                ``config/`` folder with ``default.yaml`` and ``overrides.yaml``.
        """
        self._root = Path(project_root)
        # TODO(constants): consider lifting file names/paths to a constants module
        # TODO(Maybe): support from CONFIG file ?
        self._default_path = self._root / "config" / "default.yaml"
        self._overrides_path = self._root / "config" / "overrides.yaml"
        self._rev_path = self._root / "config" / ".overrides_rev"
        self._audit_path = self._root / "config" / "audit.log"

        self._lock = threading.RLock()
        self._revision = 0

        self._model_cls: type[BaseModel] | None = None
        self._meta_tree: dict[str, Any] = {}
        self._defaults_tree: dict[str, Any] = {}
        self._effective: BaseModel | None = None
        self._overrides: dict[str, Any] = {}

        self.reload()

    # TODO(utils): consider moving to utils/io module if shared
    @staticmethod
    def _deep_merge(base: Mapping[str, Any], addendum: Mapping[str, Any]) -> dict[str, Any]:
        """Deep-merge two mapping trees (non-destructive for ``base``).

        Dicts are merged recursively; other values override.

        Args:
            base (Mapping[str, Any]): Original mapping.
            addendum (Mapping[str, Any]): Mapping whose values override/extend ``base``.

        Returns:
            dict[str, Any]: New mapping containing the merged view.
        """
        # NOTE: using JSON round-trip to clone simple dict/list primitives.
        merged: dict[str, Any] = json.loads(json.dumps(base))
        for key, value in (addendum or {}).items():
            if isinstance(value, dict) and isinstance(merged.get(key), dict):
                merged[key] = ConfigManager._deep_merge(merged[key], value)
            else:
                merged[key] = value
        return merged

    # TODO(utils): consider moving to utils/io module if shared
    @staticmethod
    def _atomic_write(path: Path, content: str) -> None:
        """Write ``content`` to ``path`` atomically.

        Args:
            path (Path): Target file path.
            content (str): Text content to write.
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = path.with_suffix(path.suffix + ".tmp")
        with tmp_path.open("w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        tmp_path.replace(path)

    def _load_yaml(self, path: Path) -> dict[str, Any]:
        """Load a YAML file into a mapping (empty mapping if file missing).

        Args:
            path (Path): YAML file path.

        Returns:
            dict[str, Any]: Parsed mapping, or ``{}`` if the file does not exist.

        Raises:
            RuntimeError: If PyYAML is not available.
            ValueError: If the file exists but does not contain a top-level mapping.
        """
        if not path.exists():
            return {}
        if yaml is None:
            # TODO(errors): consider raising ConfigDependencyError (errors.ConfigDependencyError)
            raise RuntimeError("PyYAML is required to load config files")
        with path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
            if not isinstance(data, dict):
                # TODO(errors): consider raising ConfigSchemaError (errors.ConfigSchemaError)
                raise ValueError(f"Config file {path} must be a mapping at top-level")
            return data

    def reload(self) -> None:
        """Reload defaults and overrides, rebuild model, and validate.

        On success, updates effective config, metadata, defaults, and revision.
        """
        with self._lock:
            base_defaults = self._load_yaml(self._default_path)
            validate_default_yaml_schema(base_defaults)

            model_cls, defaults_tree, meta_tree = build_model_from_default(base_defaults)
            self._model_cls = model_cls
            self._meta_tree = meta_tree
            self._defaults_tree = defaults_tree

            overrides = self._load_yaml(self._overrides_path)
            merged = self._deep_merge(defaults_tree, overrides)

            self._effective = model_cls.model_validate(merged)
            self._overrides = overrides

            try:
                if self._rev_path.exists():
                    rev_text = self._rev_path.read_text(encoding="utf-8").strip() or "0"
                    self._revision = int(rev_text)
            except Exception:
                # TODO(errors): replace broad Exception with a typed error (e.g., RevisionReadError)
                self._revision = 0

    def effective(self) -> BaseModel:
        """Return the current validated effective configuration model."""
        assert self._effective is not None
        return self._effective

    def overrides(self) -> dict[str, Any]:
        """Return a deep copy of the current overrides mapping."""
        return json.loads(json.dumps(self._overrides))

    def revision(self) -> int:
        """Return current overrides revision number."""
        return self._revision

    def meta(self) -> dict[str, Any]:
        """Return metadata (accepts/description) aligned to the defaults tree."""
        return json.loads(json.dumps(self._meta_tree))

    def json_schema(self) -> dict[str, Any]:
        """Return the Pydantic JSON schema for the effective model type."""
        assert self._model_cls is not None
        try:
            return self._model_cls.model_json_schema()
        except Exception:
            # TODO(errors): replace broad Exception with a typed error (e.g., SchemaBuildError)
            return {}

    def _bump_revision(self) -> int:
        """Increment revision, persist to file, and return the new value."""
        self._revision += 1
        ConfigManager._atomic_write(self._rev_path, str(self._revision))
        return self._revision

    def _write_overrides(self, overrides: Mapping[str, Any]) -> None:
        """Persist overrides to YAML using an atomic write.

        Args:
            overrides (Mapping[str, Any]): Overrides to persist.
        """
        if yaml is None:
            # TODO(errors): consider raising ConfigDependencyError (errors.ConfigDependencyError)
            raise RuntimeError("PyYAML is required to persist config overrides")
        # Using a local alias to keep type-checkers happy for optional import.
        import yaml as _yaml  # type: ignore

        payload = _yaml.safe_dump(dict(overrides), sort_keys=True, allow_unicode=True)
        ConfigManager._atomic_write(self._overrides_path, payload)

    def _audit(self, actor: str, operation: str, payload: Mapping[str, object], new_revision: int) -> None:
        """Append an audit entry as a single JSON line.

        Args:
            actor (str): Who performed the action.
            operation (str): Operation name (e.g., "patch", "replace", "reset").
            payload (Mapping[str, object]): Payload associated with the action.
            new_revision (int): Revision number after the action.
        """
        event = {
            "ts": time.time(),
            "actor": actor,
            "op": operation,
            "revision": new_revision,
            "payload": payload,
        }
        line = json.dumps(event, ensure_ascii=False)
        self._audit_path.parent.mkdir(parents=True, exist_ok=True)
        with self._audit_path.open("a", encoding="utf-8") as handle:
            handle.write(line + "")

    def apply_replace(self, new_overrides: Mapping[str, Any], actor: str = "system") -> dict[str, Any]:
        """Replace overrides entirely and return new revision + effective model dump."""
        with self._lock:
            merged = self._deep_merge(self._defaults_tree, dict(new_overrides))
            assert self._model_cls is not None
            effective_model = self._model_cls.model_validate(merged)

            self._write_overrides(new_overrides)
            self._overrides = dict(new_overrides)
            self._effective = effective_model

            new_rev = self._bump_revision()
            self._audit(actor, "replace", dict(new_overrides), new_rev)
            return {"revision": new_rev, "effective": effective_model.model_dump()}

    def apply_patch(self, partial_overrides: Mapping[str, Any], actor: str = "system") -> dict[str, Any]:
        """Patch overrides (deep-merge), validate, and return new revision + effective."""
        with self._lock:
            patched = self._deep_merge(self._overrides, dict(partial_overrides))
            merged = self._deep_merge(self._defaults_tree, patched)
            assert self._model_cls is not None
            effective_model = self._model_cls.model_validate(merged)

            self._write_overrides(patched)
            self._overrides = patched
            self._effective = effective_model

            new_rev = self._bump_revision()
            self._audit(actor, "patch", dict(partial_overrides), new_rev)
            return {"revision": new_rev, "effective": effective_model.model_dump()}

    def dry_run(self, payload: Mapping[str, object]) -> dict[str, Any]:
        """Validate a potential patch against the model without persisting.

        Returns an object with keys: ``ok`` (bool), ``errors`` (list[str]), and
        optionally ``effective`` when validation succeeds.
        """
        with self._lock:
            trial = self._deep_merge(self._overrides, dict(payload))
            merged = self._deep_merge(self._defaults_tree, trial)
            result: dict[str, Any] = {"ok": True, "errors": []}
            try:
                assert self._model_cls is not None
                effective_model = self._model_cls.model_validate(merged)
                result["effective"] = effective_model.model_dump()
            except Exception as exc:
                # TODO(errors): catch specific validation error types (e.g., ValidationError)
                result["ok"] = False
                result["errors"] = [str(exc)]
            return result

    def reset_overrides(self, actor: str = "system") -> dict[str, Any]:
        """Clear overrides, validate defaults, and return new revision + effective."""
        with self._lock:
            self._write_overrides({})
            self._overrides = {}

            assert self._model_cls is not None
            effective_model = self._model_cls.model_validate(self._defaults_tree)
            self._effective = effective_model

            new_rev = self._bump_revision()
            self._audit(actor, "reset", {}, new_rev)
            return {"revision": new_rev, "effective": effective_model.model_dump()}
