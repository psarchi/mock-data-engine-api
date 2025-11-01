from __future__ import annotations

from collections.abc import Mapping, Sequence
from random import Random
from typing import Any, Optional

from starlette.responses import Response

from faker_engine.chaos.config import ChaosConfigView
from faker_engine.chaos.types import ChaosOpPhase, ChaosScope


# TODO(arch): probably want to rename this to ChaosController or ChaosCoordinator
class ChaosManager:
    """Coordinator that selects and applies chaos operations.

    Args:
        cfg (ChaosConfigView): Read-only chaos configuration view.
        ops_registry (dict[str, Any]): Mapping of op-name → op object providing
            ``phase()``, ``maybe_request(...)``, and ``maybe_response(...)``.
        rng (Random): Deterministic RNG instance.
    """

    __slots__ = ("cfg", "ops_registry", "rng")

    def __init__(self, cfg, ops_registry: dict[str, Any], rng: Random) -> None:
        self.cfg = cfg
        self.ops_registry = ops_registry
        self.rng = rng

    # TODO(validation): Validate ops configs at load-time (weights >= 0, 0 ≤ p ≤ 1).
    def _select_ops(self, scope: ChaosScope) -> list[str]:
        """Select operation names eligible for ``scope`` using per-op probability.

        Args:
            scope (ChaosScope): Scope to evaluate (e.g., ``"request"`` / ``"response"`` / ``"global"``).

        Returns:
            list[str]: Ordered list of selected operation names.
        """
        if not self.cfg.enabled or not self.cfg.is_scope_enabled(scope):
            return []
        enabled_ops = [name for name, op_cfg in self.cfg.ops.items() if
                       op_cfg.get('enabled', False)]
        if not enabled_ops:
            return []

        activated: list[str] = []
        for name in enabled_ops:
            p = float(self.cfg.ops[name].get('p', 0.0))
            if p > 0.0 and self.rng.random() < p:
                activated.append(name)

        min_ops = self.cfg.selection_min_ops
        max_ops = self.cfg.selection_max_ops  # None means 'all'
        ensure_one = self.cfg.selection_ensure_one

        if not activated and ensure_one:
            activated = [self._weighted_sample_one(enabled_ops)]

        if len(activated) < min_ops:
            pool = [n for n in enabled_ops if n not in activated]
            needed = min_ops - len(activated)
            activated.extend(self._weighted_sample_k(pool, needed))

        if max_ops is not None and len(activated) > max_ops:
            activated = self._weighted_sample_k(activated, max_ops)

        self.rng.shuffle(activated)
        return activated

    def _weighted_sample_one(self, names: list[str]) -> str:
        """Return one name sampled by weight from ``names``.

        Args:
            names (Sequence[str]): Candidate operation names.

        Returns:
            str: Selected name.
        """
        weights = [float(self.cfg.ops[n].get('weight', 1.0)) for n in names]
        total = sum(weights)
        if total <= 0:
            return names[int(self.rng.random() * len(names))]
        pick = self.rng.random() * total
        acc = 0.0
        for n, w in zip(names, weights):
            acc += w
            if pick <= acc:
                return n
        return names[-1]

    def _weighted_sample_k(self, names: Sequence[str], k: int) -> list[str]:
        """Return up to ``k`` distinct names sampled without replacement by weight.

        Args:
            names (Sequence[str]): Candidate operation names.
            k (int): Number of names to sample.

        Returns:
            list[str]: Selected names (may be fewer than ``k`` if ``names`` is short).
        """
        if k <= 0 or not names:
            return []
        pool = list(names)
        chosen: list[str] = []
        for _ in range(min(k, len(pool))):
            pick = self._weighted_sample_one(pool)
            chosen.append(pick)
            pool.remove(pick)
        return chosen

    def apply_request(self, scope: ChaosScope, ctx: object, request: object) -> \
    Optional[Response]:
        """Apply request-phase chaos operations.

        Args:
            scope (ChaosScope): Scope to evaluate (typically ``"generate"`` / ``"schema"`` / ``"admin"``).
            ctx (object): Request-scoped context bag (holds ``meta`` and internal fields).
            request (object): Framework request object passed to ops.

        Returns:
            Optional[Response]: Early response if an op short-circuited the request; otherwise ``None``.
        """
        selected = self._select_ops(scope)
        budgets = {
            "max_added_latency_ms": self.cfg.budget_max_added_latency_ms,
            "max_faults_per_request": self.cfg.budget_max_faults_per_request,
        }
        applied: list[str] = []
        faults = 0
        added_latency_ms = 0

        for name in selected:
            op = self.ops_registry.get(name)
            if not op or op.phase() != ChaosOpPhase.REQUEST:
                continue
            if faults >= budgets["max_faults_per_request"]:
                continue

            result = op.maybe_request(
                scope=scope,
                ctx=ctx,
                request=request,
                rng=self.rng,
                cfg=self.cfg.ops.get(name, {}),
            )

            if isinstance(result, Response):
                applied.append(name)
                faults += 1
                self._attach_meta(ctx, selected, applied, budgets,
                                  added_latency_ms)
                return result

            if isinstance(result, dict) and "added_latency_ms" in result:
                added_latency_ms += int(
                    result["added_latency_ms"])  # type: ignore[arg-type]
                applied.append(name)

            if added_latency_ms > budgets["max_added_latency_ms"]:
                break

        self._attach_meta(ctx, selected, applied, budgets, added_latency_ms)
        return None

    def apply_response(
            self,
            scope: ChaosScope,
            ctx: object,
            payload: Mapping[str, Any],
            schema_name: Optional[str] = None,
    ) -> Any:
        """Apply response-phase chaos operations.

        Args:
            scope (ChaosScope): Scope to evaluate (typically ``"generate"`` / ``"schema"`` / ``"admin"``).
            ctx (object): Request-scoped context bag (holds ``meta`` and internal fields).
            payload (Mapping[str, Any]): HTTP/JSON payload to mutate.
            schema_name (str | None): Optional schema name for op context.

        Returns:
            Any: Mutated payload from the last applied op (or the original payload).
        """
        selected = getattr(ctx, "_chaos_selected", None)
        if selected is None:
            selected = self._select_ops(scope)

        applied: list[str] = getattr(ctx, "_chaos_applied", [])
        payload_cur: Any = payload

        for name in selected:
            op = self.ops_registry.get(name)
            if not op or op.phase() != ChaosOpPhase.RESPONSE:
                continue
            payload_cur = op.maybe_response(
                scope=scope,
                ctx=ctx,
                payload=payload_cur,
                schema_name=schema_name,
                rng=self.rng,
                cfg=self.cfg.ops.get(name, {}),
            )
            applied.append(name)

        budgets = {
            "max_added_latency_ms": self.cfg.budget_max_added_latency_ms,
            "max_faults_per_request": self.cfg.budget_max_faults_per_request,
        }
        self._attach_meta(ctx, selected, applied, budgets,
                          getattr(ctx, "_chaos_added_latency_ms", 0))
        return payload_cur

    # TODO(refactor): Move meta attachment to middleware or a decorator.
    def _attach_meta(
            self,
            ctx: object,
            selected: Sequence[str],
            applied: Sequence[str],
            budgets: Mapping[str, Any],
            added_latency_ms: int,
    ) -> None:
        """Attach chaos summary under ``ctx.meta['chaos']`` and store internals on ``ctx``.

        Args:
            ctx (object): Context bag updated in-place.
            selected (Sequence[str]): All selected operation names.
            applied (Sequence[str]): Successfully applied operation names.
            budgets (Mapping[str, Any]): Budgets used during this request.
            added_latency_ms (int): Cumulative added latency (ms).
        """
        setattr(ctx, "_chaos_selected", list(selected))
        setattr(ctx, "_chaos_applied", list(applied))
        setattr(ctx, "_chaos_added_latency_ms", int(added_latency_ms))

        meta = getattr(ctx, "meta", None)
        if isinstance(meta, dict):
            meta.setdefault("chaos", {})
            meta["chaos"].update(
                {
                    "selected": list(selected),
                    "applied": list(applied),
                    "added_latency_ms": int(added_latency_ms),
                    "budgets": dict(budgets),
                }
            )
