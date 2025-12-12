from __future__ import annotations
import random
from typing import Any
import string
from mock_engine.chaos.ops.base import BaseChaosOp, ApplyResult
from mock_engine.chaos.ops.utils import iter_leaf_refs
from mock_engine.registry import Registry


@Registry.register(BaseChaosOp)
class SchemaBloatOp(BaseChaosOp):
    """Schema/response bloat chaos operation.

    Inflates payload size **in place** by enlarging **one randomly selected string field**
    anywhere under the body (top-level, items, nested dicts/lists). Two strategies:
      - "insert": insert random characters into strings (default)
      - "repeat": repeat existing string content (e.g., "city") until target size

    The op keeps JSON valid and avoids touching non-strings.

    Args:
        enabled (bool): Toggle.
        p (float): Probability [0,1].
        weight (float): Relative weight.
        extra_kb (int): ~Additional bytes to add (best effort) **to one field**.
        strategy (str): "insert" | "repeat" (default "insert").

    Returns:
        ApplyResult: mutated body; description like
            ["schema_bloat(path=<path>,+<bytes> bytes,strat=<strategy>)"].
    """

    key = "schema_bloat"

    def __init__(
        self,
        *,
        enabled: bool,
        p: float = 0.0,
        weight: float = 1.0,
        extra_kb: int = 32,
        strategy: str = "insert",
        **kw,
    ) -> None:
        super().__init__(enabled=enabled, p=p, weight=weight, **kw)
        self.extra_kb = max(0, int(extra_kb or 0))
        s = (strategy or "insert").strip().lower()
        self.strategy = s if s in {"insert", "repeat"} else "insert"

    @staticmethod
    def _rand_chars(rng: random.Random, n: int) -> str:
        pool = string.ascii_letters + string.digits + string.punctuation + " "
        L = len(pool)
        return "".join(pool[int(rng.random() * L)] for _ in range(n))

    def _inflate_insert(self, s: str, need: int, rng: random.Random) -> tuple[str, int]:
        if need <= 0:
            return s, 0
        chunk = min(max(8, need // 4), need)
        ins = self._rand_chars(rng, chunk)
        pos = int(rng.random() * (len(s) + 1))
        out = s[:pos] + ins + s[pos:]
        return out, len(ins)

    def _inflate_repeat(self, s: str, need: int, rng: random.Random) -> tuple[str, int]:
        if not s:
            return self._inflate_insert(s, need, rng)
        token = s
        parts = s.split()
        if parts:
            token = parts[-1]
        # ensure token non-empty
        if not token:
            token = s
        max_chunk = max(8, need)
        reps = max(
            1, min(need // max(1, len(token)), 64)
        )  # cap reps to avoid huge loops
        addition = (token + " ") * reps
        out = s + addition
        added = len(addition)
        if added > need:
            out = s + addition[:need]
            added = need
        return out, added

    def apply(self, *, request, response, body: Any, rng: random.Random) -> ApplyResult:
        if not isinstance(body, (dict, list)):
            return ApplyResult(body=body, descriptions=[])

        slots = list(iter_leaf_refs(body, predicate=lambda v: isinstance(v, str)))
        if not slots:
            return ApplyResult(body=body, descriptions=[])

        rng.shuffle(slots)
        node_ref = slots[0]
        parent, key, path = node_ref.parent, node_ref.key, node_ref.path

        extra_bytes = self.extra_kb * 1024
        if extra_bytes <= 0:
            return ApplyResult(body=body, descriptions=[])
        to_add_total = extra_bytes

        strat = self.strategy

        if parent is None or key is None:
            return ApplyResult(body=body, descriptions=[])
        cur = parent[key]
        if not isinstance(cur, str):
            return ApplyResult(body=body, descriptions=[])

        bytes_added = 0
        for _ in range(256):
            remaining = to_add_total - bytes_added
            if remaining <= 0:
                break
            if strat == "insert":
                new_val, inc = self._inflate_insert(cur, remaining, rng)
            else:  # "repeat"
                new_val, inc = self._inflate_repeat(cur, remaining, rng)
            if inc <= 0:
                break
            parent[key] = new_val
            cur = new_val
            bytes_added += inc

        return ApplyResult(
            body=body,
            descriptions=[
                f"schema_bloat(path={path},+{bytes_added} bytes,strat={strat})"
            ],
        )
