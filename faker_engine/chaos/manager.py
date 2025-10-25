from __future__ import annotations
from typing import Any, Dict, List, Optional
from faker_engine.chaos.types import ChaosScope, ChaosOpPhase
from faker_engine.chaos.config import ChaosConfigView
from fastapi import Response


class ChaosManager:
    def __init__(self, cfg: ChaosConfigView, ops_registry: Dict[str, Any],
                 rng):
        self.cfg = cfg
        self.ops_registry = ops_registry
        self.rng = rng

    def _select_ops(self, scope: ChaosScope) -> List[str]:
        if not self.cfg.enabled or not self.cfg.is_scope_enabled(scope):
            return []
        enabled_ops = [name for name, op_cfg in self.cfg.ops.items() if
                       op_cfg.get('enabled', False)]
        if not enabled_ops:
            return []

        activated: List[str] = []
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

    def _weighted_sample_one(self, names: List[str]) -> str:
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

    def _weighted_sample_k(self, names: List[str], k: int) -> List[str]:
        if k <= 0 or not names:
            return []
        pool = list(names)
        chosen: List[str] = []
        for _ in range(min(k, len(pool))):
            pick = self._weighted_sample_one(pool)
            chosen.append(pick)
            pool.remove(pick)
        return chosen

    def apply_request(self, scope: ChaosScope, ctx, request) -> Optional[
        Response]:
        selected = self._select_ops(scope)
        budgets = {
            'max_added_latency_ms': self.cfg.budget_max_added_latency_ms,
            'max_faults_per_request': self.cfg.budget_max_faults_per_request,
        }
        applied: List[str] = []
        faults = 0
        added_latency_ms = 0

        for name in selected:
            op = self.ops_registry.get(name)
            if not op or op.phase() != ChaosOpPhase.REQUEST:
                continue

            if faults >= budgets['max_faults_per_request']:
                continue

            result = op.maybe_request(scope=scope, ctx=ctx, request=request,
                                      rng=self.rng,
                                      cfg=self.cfg.ops.get(name, {}))
            if isinstance(result, Response):
                applied.append(name)
                faults += 1
                self._attach_meta(ctx, selected, applied, budgets,
                                  added_latency_ms)
                return result
            elif isinstance(result, dict) and 'added_latency_ms' in result:
                added_latency_ms += int(result['added_latency_ms'])
                applied.append(name)

            if added_latency_ms > budgets['max_added_latency_ms']:
                break

        self._attach_meta(ctx, selected, applied, budgets, added_latency_ms)
        return None

    def apply_response(self, scope: ChaosScope, ctx, payload: Any,
                       schema_name: Optional[str] = None) -> Any:
        selected = getattr(ctx, '_chaos_selected', None)
        if selected is None:
            selected = self._select_ops(scope)
        applied: List[str] = getattr(ctx, '_chaos_applied', [])
        payload_cur = payload

        for name in selected:
            op = self.ops_registry.get(name)
            if not op or op.phase() != ChaosOpPhase.RESPONSE:
                continue
            payload_cur = op.maybe_response(scope=scope, ctx=ctx,
                                            payload=payload_cur,
                                            schema_name=schema_name,
                                            rng=self.rng,
                                            cfg=self.cfg.ops.get(name, {}))
            applied.append(name)

        budgets = {
            'max_added_latency_ms': self.cfg.budget_max_added_latency_ms,
            'max_faults_per_request': self.cfg.budget_max_faults_per_request,
        }
        self._attach_meta(ctx, selected, applied, budgets,
                          getattr(ctx, '_chaos_added_latency_ms', 0))
        return payload_cur

    def _attach_meta(self, ctx, selected, applied, budgets,
                     added_latency_ms) -> None:
        setattr(ctx, '_chaos_selected', list(selected))
        setattr(ctx, '_chaos_applied', list(applied))
        setattr(ctx, '_chaos_added_latency_ms', int(added_latency_ms))
        meta = getattr(ctx, 'meta', None)
        if isinstance(meta, dict):
            meta.setdefault('chaos', {})
            meta['chaos'].update({
                'selected': list(selected),
                'applied': list(applied),
                'added_latency_ms': int(added_latency_ms),
                'budgets': budgets,
            })
