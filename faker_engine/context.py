import random
import faker
import uuid
import time
import json
import hashlib
import secrets
import base64
import pickle
from .errors import InvalidSeedError, InvalidRNGError, InvalidLocaleError, \
    ContextError


def _now_iso_utc_ms() -> str:
    t = time.time()
    secs = int(t)
    ms = int((t - secs) * 1000)
    return time.strftime("%Y-%m-%dT%H:%M:%S",
                         time.gmtime(secs)) + f".{ms:03d}Z"


def _short_hash(obj) -> str:
    try:
        blob = json.dumps(obj, sort_keys=True, default=str).encode("utf-8")
    except TypeError:
        blob = str(obj).encode("utf-8")
    return hashlib.sha1(blob).hexdigest()[:6]


def _derive_seed64(*parts) -> int:
    h = hashlib.sha1("|".join(map(str, parts)).encode()).digest()
    return int.from_bytes(h[:8], "big")


class GenContext:
    def __init__(self, seed=None, rng=None, locale=None):
        if rng is not None:
            if not isinstance(rng, random.Random):
                raise InvalidRNGError("Provided RNG isn't random.Random class")
            self.rng = rng
            self.seed = seed  # may be None; external RNG is authoritative
            # TODO: add rng_state to meta with debug option
            try:
                self.rng_state = self.rng.getstate()
                self.rng_state_b64 = base64.b64encode(
                    pickle.dumps(self.rng_state)).decode()
            except Exception:
                self.rng_state = None
                self.rng_state_b64 = None
        else:
            if seed is None:
                seed = secrets.randbits(64)  # explicit 64-bit seed for replay
            self.seed = seed
            self.rng = random.Random(self.seed)
            self.rng_state = self.rng.getstate()  # TODO: same as above
            self.rng_state_b64 = base64.b64encode(
                pickle.dumps(self.rng_state)).decode()

        self.locale = locale
        self._faker = None

        self.sequence = 0
        self.request_id = None  # UUIDv4 set on first build_meta()
        self.trace_id = None  # = request_id for now  TODO: OTEL
        self.scenario = None
        self.config_hash = None
        self.generator_version = "0.1.0"  # TODO: comes from global config file
        self.emit_meta = True
        self.schema_name = None
        self.schema_version = "unknown"  # TODO: comes from global config file

    @property
    def faker(self):
        if self._faker is None:
            try:
                f = faker.Faker(self.locale) if self.locale else faker.Faker()
            except Exception as e:
                raise InvalidLocaleError(str(e))
            # deterministic seed for Faker, independent from main RNG state
            if self.seed is not None:
                fk_seed = _derive_seed64(self.seed, "faker",
                                         self.schema_name or "", "v1")
            else:
                # external RNG only: derive from RNG state fingerprint
                fk_seed = _derive_seed64(self.rng_state_b64 or "", "faker",
                                         self.schema_name or "", "v1")
            f.seed_instance(fk_seed)
            self._faker = f
        return self._faker

    def build_meta(self) -> dict:
        if self.request_id is None:
            self.request_id = str(uuid.uuid4())
        if self.trace_id is None:
            self.trace_id = self.request_id
        self.sequence += 1
        cfg_hash = self.config_hash or _short_hash({
            "schema": self.schema_name,
            "version": self.schema_version,
            "seed": self.seed,
        })
        meta = {
            "schema": self.schema_name,
            "schema_version": self.schema_version,
            "seed": self.seed,
            "sequence": self.sequence,
            "generated_at": _now_iso_utc_ms(),
            "scenario": self.scenario,
            "config_hash": cfg_hash,
            "request_id": self.request_id,
            "trace_id": self.trace_id,
            "generator_version": self.generator_version,
            "source": "mock-data-api",
        }
        # lightweight fingerprint
        if self.seed is None and self.rng_state_b64:
            meta["rng_fp"] = hashlib.sha1(
                self.rng_state_b64.encode()).hexdigest()[:12]
        return meta
