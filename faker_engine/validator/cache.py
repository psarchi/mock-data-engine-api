import json, inspect, importlib
from pathlib import Path

MANIFEST = "manifest.json"
CACHE_VERSION = "2"


def _sha256_bytes(data):
    import hashlib
    return hashlib.sha256(data).hexdigest()


def _file_sha256(path):
    try:
        return _sha256_bytes(Path(path).read_bytes())
    except FileNotFoundError:
        return ""


def _load_core_registry():
    diagnostics = []
    try:
        mod = importlib.import_module("faker_engine.core.registry")
    except Exception as e:
        diagnostics.append(
            "registry: cannot import faker_engine.core.registry: %s" % e.__class__.__name__)
        return [], diagnostics
    for attr in ("REGISTRY", "GENERATORS"):
        reg = getattr(mod, attr, None)
        if reg is None:
            diagnostics.append(
                "registry: faker_engine.core.registry has no %s" % attr)
            continue
        try:
            classes = [c for c in reg]
        except Exception as e:
            diagnostics.append("registry iterable error on %s: %s" % (
            attr, e.__class__.__name__))
            continue
        classes = [c for c in classes if isinstance(c, type)]
        return classes, diagnostics
    diagnostics.append("registry: no REGISTRY/GENERATORS found")
    return [], diagnostics


class SchemaCache:
    def __init__(self, project_root=".", root=".cache/schema_cache"):
        self.project_root = Path(project_root)
        self.root = self.project_root / root
        self.root.mkdir(parents=True, exist_ok=True)

    def _extract_entry_from_class(self, cls):
        gen_name = getattr(cls, "__name__", cls.__qualname__)
        meta = getattr(cls, "__meta__", {}) or {}
        version = str(meta.get("version", "")) if isinstance(meta,
                                                             dict) else ""
        aliases = getattr(cls, "__aliases__", {}) or {}
        fields = {}

        Spec = getattr(cls, "Spec", None)
        if Spec is not None:
            ann = getattr(Spec, "__annotations__", {}) or {}
            for field_name, field_type in ann.items():
                required = not hasattr(Spec, field_name)
                default = getattr(Spec, field_name,
                                  None) if not required else None
                fields[field_name] = {
                    "type": getattr(field_type, "__name__", str(field_type)),
                    "required": required,
                    "default": default,
                }
        elif hasattr(cls, "__slots__"):
            slots = getattr(cls, "__slots__", ())
            if isinstance(slots, (list, tuple)):
                for s in slots:
                    fields[str(s)] = {"type": "Any", "required": False,
                                      "default": None}

        entry = {
            "name": gen_name,
            "version": version,
            "fields": fields,
            "aliases": aliases if isinstance(aliases, dict) else {},
            "deprecations": meta.get("deprecations", []) if isinstance(meta,
                                                                       dict) else [],
            "rules": meta.get("rules", []) if isinstance(meta, dict) else [],
            "cache_v": CACHE_VERSION,
        }
        return entry

    def build(self, force=False):
        manifest_path = self.root / MANIFEST
        classes, diagnostics = _load_core_registry()
        manifest = {
            "cache_v": CACHE_VERSION,
            "generators": [],
            "diagnostics": diagnostics,
        }
        if not classes:
            manifest_path.write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2,
                           sort_keys=True), encoding="utf-8")
            return manifest
        for cls in classes:
            entry = self._extract_entry_from_class(cls)
            try:
                src_file = inspect.getsourcefile(cls) or ""
            except Exception:
                src_file = ""
            src_hash = _file_sha256(Path(src_file)) if src_file else ""
            core = json.dumps(
                {"name": entry["name"], "version": entry["version"],
                 "fields": entry["fields"]}, sort_keys=True).encode("utf-8")
            entry["fingerprint"] = _sha256_bytes(
                src_hash.encode("utf-8") + core + CACHE_VERSION.encode(
                    "utf-8"))
            out = self.root / ("%s.json" % entry["name"])
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(entry, ensure_ascii=False, indent=2,
                                      sort_keys=True), encoding="utf-8")
            manifest["generators"].append({
                "name": entry["name"],
                "class": "%s.%s" % (cls.__module__, cls.__qualname__),
                "fingerprint": entry["fingerprint"],
            })
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8")
        return manifest

    def load(self, name):
        path = self.root / ("%s.json" % name)
        if not path.exists():
            raise FileNotFoundError(
                "cache entry not found for generator: %s" % name)
        return json.loads(path.read_text(encoding="utf-8"))

    def fingerprint(self, generator_obj):
        try:
            src_file = inspect.getsourcefile(generator_obj) or ""
            src_hash = _file_sha256(Path(src_file)) if src_file else ""
        except Exception:
            src_hash = ""
        core = getattr(generator_obj, "__meta__", {})
        payload = json.dumps(core, sort_keys=True).encode("utf-8")
        return _sha256_bytes(
            src_hash.encode("utf-8") + payload + CACHE_VERSION.encode("utf-8"))
