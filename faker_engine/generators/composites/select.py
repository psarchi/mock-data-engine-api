from __future__ import annotations
from typing import Optional, Sequence, Mapping, Any

from faker_engine.errors import ContextError, MissingChildError, \
    InvalidParameterError
from faker_engine.generators.base import BaseGenerator
from faker_engine.context import GenContext


class SelectGenerator(BaseGenerator):
    __slots__ = ("options", "pick")
    __aliases__ = ("select",)

    def __init__(self, options: Mapping[str, Any] | None = None,
                 pick: Optional[int] = None) -> None:
        self.options = options or {}
        self.pick = pick or {}

    @classmethod
    def from_spec(cls, builder: object,
                  spec: dict[str, object]) -> "SelectGenerator":
        opts = spec.get("options")
        if not opts or not isinstance(opts, dict):
            raise MissingChildError("select requires 'options' dict")
        built = {}
        meta = {}
        for key, conf in opts.items():
            if not isinstance(conf, dict) or "of" not in conf:
                raise MissingChildError("each option must have an 'of' spec")
            built[key] = builder.build(conf.get("of"))
            meta[key] = {
                "required": bool(conf.get("required")),
                "default": conf.get("default", None),
            }
        pick = spec.get("pick") or {}
        mode = pick.get("mode", "any")
        if mode not in ("any", "at_least_one", "exact", "range"):
            raise InvalidParameterError(
                "pick.mode must be any|at_least_one|exact|range")
        if mode == "exact" and pick.get("min") is None:
            raise InvalidParameterError(
                "pick.min is required when mode=exact (exact count)")
        if mode == "range" and (
                pick.get("min") is None or pick.get("max") is None):
            raise InvalidParameterError(
                "pick.min and pick.max are required when mode=range")
        return cls(options={"built": built, "meta": meta}, pick=pick)

    def _sanity_check(self, ctx: GenContext) -> None:
        if not isinstance(ctx, GenContext):
            raise ContextError("ctx must be an instance of GenContext")
        if not self.options or not self.options.get("built"):
            raise MissingChildError("select requires options")

    def configure(self, options: Mapping[str, Any] | None = None,
                  pick: Optional[int] = None,
                  **kwargs: object) -> "SelectGenerator":
        if options is not None:
            self.options = options
        if pick is not None:
            self.pick = pick
        return self

    def _weighted_sample(self, rng: object, items: list[str],
                         weights: list[float], k: int) -> list[str]:
        chosen = []
        pool_items = list(items)
        pool_weights = [weights.get(x, 1.0) for x in pool_items]
        for _ in range(min(k, len(pool_items))):
            total = float(sum(pool_weights))
            r = rng.random() * total
            acc = 0.0
            idx = 0
            for i, w in enumerate(pool_weights):
                acc += float(w)
                if r <= acc:
                    idx = i
                    break
            chosen.append(pool_items.pop(idx))
            pool_weights.pop(idx)
        return chosen

    def _decide_keys(self, rng: object) -> list[str]:
        built = self.options["built"]
        meta = self.options["meta"]
        required = [k for k, m in meta.items() if m.get("required")]
        optional = [k for k in built.keys() if k not in required]
        pick = self.pick or {}
        mode = pick.get("mode", "any")
        weights = pick.get("weights", {}) or {}

        if not optional and mode in ("any", "at_least_one", "exact", "range"):
            # Only required keys exist
            return required

        if mode == "exact":
            k = int(pick.get("min"))
        elif mode == "range":
            k = rng.randint(int(pick.get("min")), int(pick.get("max")))
        elif mode == "at_least_one":
            k = rng.randint(1, len(optional))
        else:  # any
            min_k = int(pick.get("min", 0))
            max_k = int(pick.get("max", len(optional)))
            if max_k < min_k:
                max_k = min_k
            k = rng.randint(min_k, max_k) if (
                        min_k or max_k != len(optional)) else rng.randint(0,
                                                                          len(optional))

        chosen_optional = self._weighted_sample(rng, optional, weights, k)
        return required + chosen_optional

    def generate(self, ctx: GenContext) -> Any:
        self._sanity_check(ctx)
        keys = self._decide_keys(ctx.rng)
        built = self.options["built"]
        out = {}
        for key in keys:
            out[key] = built[key].generate(ctx)
        return out
