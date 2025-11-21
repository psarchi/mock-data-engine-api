from __future__ import annotations

import random
from types import SimpleNamespace
from typing import Any, Dict, List, Optional, Tuple, Type

from mock_engine.chaos.drift import get_drift_coordinator
from mock_engine.chaos.ops.base import ApplyResult, BaseChaosOp
from .registry import _Registry
from mock_engine.context import GenContext
from pydantic import BaseModel

class ChaosManager:
    """Coordinate chaos operations for a single response."""

    def __init__(
        self,
        *,
        ctx: GenContext | random.Random | None,
        config_snapshot: BaseModel,
        registry: Dict[str, Type[BaseChaosOp]],
    ) -> None:
        self.ctx = ctx
        self.registry = registry
        self._hits: Dict[str, int] = {}  # for now placeholder
        self.drift = get_drift_coordinator()
        self.cfg = config_snapshot
        if isinstance(ctx, GenContext):
            self.rng = ctx.rng
        elif isinstance(ctx, random.Random):
            self.rng = ctx
        else:
            self.rng = random.Random()

    def apply(
        self,
        *,
        response: Dict[str, Any],
        meta_enabled: bool,
        forced_activation: List[str] | None = None, # placeholder for forced activation
        schema_name: str | None = None,
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        if schema_name:
            # Track chaos usage under a single strategy bucket for drift bookkeeping.
            self.drift.record_hit(schema_name, "chaos")
        ops_cfg = getattr(self.cfg, "ops", None)  # never should be None 
        if ops_cfg is None:
            return response, {}
        selection_cfg = getattr(self.cfg, "selection", None)
        ensure_one = bool(
            getattr(selection_cfg, "ensure_at_least_one_when_any_enabled", False)
        )
        min_ops = getattr(selection_cfg, "min_ops", 0)
        if ensure_one and min_ops < 1:
            min_ops = 1
        max_ops = getattr(selection_cfg, "max_ops", 0)
        chosen_count = self.rng.randint(min_ops, max_ops)
        chosen_names: List[str] = []
        chosen_weights: List[float] = []
        activated_names: List[str] = []

        allowed_names = self.registry
        if forced_activation:
            # forced activation for testing/validation of specific ops
            allowed_names = {key: value for key, value in allowed_names.items() if key in forced_activation}
            activated_names = [k for k,v  in allowed_names.items() if k in forced_activation]
            
        else:
            for op_name, op_cls in allowed_names.items():
                op_cfg = getattr(ops_cfg, op_name, None)
                if not (op_cfg and getattr(op_cfg, "enabled", False) and getattr(op_cfg, "p", 0)):
                    continue
                if self.rng.random() < getattr(op_cfg, "p"):
                    chosen_names.append(op_name)
                    chosen_weights.append(getattr(op_cfg, "weight", 0))
                
            if chosen_names and sum(chosen_weights) > 0:
                activated_names = self.rng.choices(chosen_names, weights=chosen_weights, k=chosen_count)
            else:
                return response, {}
        
        # budget (without drifts)
        drift_ops: list[str] = []
        other_ops: list[str] = []

        for name in activated_names:
            (drift_ops if "drift" in name else other_ops).append(name)

        activated_names = other_ops
        budgets_cfg = getattr(self.cfg, "budgets", None)
        if budgets_cfg:
            if len(activated_names) > getattr(budgets_cfg, "max_faults_per_request"):
                activated_names = self.rng.sample(activated_names, k= getattr(budgets_cfg, "max_faults_per_request"))

        result = ApplyResult(body=response.get("body"))
        for op in activated_names:
            op_cls = self.registry.get(op)
            params = getattr(ops_cfg, op).model_dump()
            op_instance = op_cls(**params)
            op_result = op_instance.apply(
                request=response.get("request"),
                response=response.get("response"),
                body=result.body,
                rng=self.rng,
            )
            if result.descriptions:
                result.descriptions.extend(op_result.descriptions)
            else:
                result.descriptions = op_result.descriptions
            result.body = op_result.body
        
        return result, {}
    
