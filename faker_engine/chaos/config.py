from __future__ import annotations

from typing import Any


class ChaosConfigView:
    """Lightweight, read-only view over chaos configuration.
    Parses a raw configuration mapping and exposes read-only fields used by the
    chaos middleware.
    Attributes:
        enabled (bool): Whether chaos features are enabled.
        scopes (set[str]): Enabled chaos scopes (e.g., {"generate", "schema", "admin"}).
        selection_min_ops (int): Minimum number of ops to apply.
        selection_max_ops (int | None): Maximum ops to apply; ``None`` means "all".
        selection_ensure_one (bool): Ensure at least one op is applied when any enabled.
        budget_max_added_latency_ms (int): Upper bound on injected latency (ms).
        budget_max_faults_per_request (int): Upper bound on injected faults per request.
        ops (dict[str, dict[str, Any]]): Per-operation configuration by op name.
    """

    __slots__ = (
        "enabled",
        "scopes",
        "selection_min_ops",
        "selection_max_ops",
        "selection_ensure_one",
        "budget_max_added_latency_ms",
        "budget_max_faults_per_request",
        "ops",
    )

    # TODO(config): Centralize defaults and keys in a single schema to keep API stable.
    # TODO(validation): Validate numeric fields and types at load-time; reject negatives/NaN.

    def __init__(self, cfg: dict[str, Any]) -> None:
        """Initialize the view from a raw configuration mapping.

        Args:
            cfg (dict[str, Any]): Root configuration mapping (expects ``features.chaos`` subtree).
        """
        features_dict: dict[str, Any] = cfg.get("features", {}) or {}
        chaos_dict: dict[str, Any] = features_dict.get("chaos", {}) or {}

        self.enabled: bool = bool(chaos_dict.get("enabled", False))

        scopes_value = chaos_dict.get("scopes", ["generate"]) or ["generate"]
        self.scopes: set[str] = set(str(s) for s in scopes_value)

        selection_dict: dict[str, Any] = chaos_dict.get("selection", {}) or {}
        self.selection_min_ops: int = int(selection_dict.get("min_ops", 0))
        max_ops_value = selection_dict.get("max_ops", "all")
        self.selection_max_ops: int | None = (
            None if str(max_ops_value).lower() == "all" else int(max_ops_value)
        )
        self.selection_ensure_one: bool = bool(
            selection_dict.get("ensure_at_least_one_when_any_enabled", False)
        )

        budgets_dict: dict[str, Any] = chaos_dict.get("budgets", {}) or {}
        self.budget_max_added_latency_ms: int = int(
            budgets_dict.get("max_added_latency_ms", 1500)
        )
        self.budget_max_faults_per_request: int = int(
            budgets_dict.get("max_faults_per_request", 999)
        )

        self.ops: dict[str, dict[str, Any]] = chaos_dict.get("ops", {}) or {}

    def is_scope_enabled(self, scope: str) -> bool:
        """Return whether ``scope`` is enabled for chaos operations.

        Args:
            scope (str): Scope to evaluate (e.g., ``"generate"``, ``"schema"``, ``"admin"``).

        Returns:
            bool: ``True`` if the scope is enabled, otherwise ``False``.
        """
        return scope in self.scopes
