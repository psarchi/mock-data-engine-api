from __future__ import annotations
from typing import Any, Dict, Optional


class ChaosConfigView:
    def __init__(self, cfg: Dict[str, Any]):
        features = cfg.get('features', {})
        chaos = features.get('chaos', {})
        self.enabled: bool = bool(chaos.get('enabled', False))
        self.scopes = set(chaos.get('scopes', ['generate']))

        selection = chaos.get('selection', {})
        self.selection_min_ops: int = int(selection.get('min_ops', 0))
        max_ops_val = selection.get('max_ops', 'all')
        self.selection_max_ops: Optional[int] = None if str(
            max_ops_val).lower() == 'all' else int(max_ops_val)
        self.selection_ensure_one: bool = bool(
            selection.get('ensure_at_least_one_when_any_enabled', False))

        budgets = chaos.get('budgets', {})
        self.budget_max_added_latency_ms: int = int(
            budgets.get('max_added_latency_ms', 1500))
        self.budget_max_faults_per_request: int = int(
            budgets.get('max_faults_per_request', 999))

        self.ops: Dict[str, Dict[str, Any]] = chaos.get('ops', {})

    def is_scope_enabled(self, scope: str) -> bool:
        return scope in self.scopes
