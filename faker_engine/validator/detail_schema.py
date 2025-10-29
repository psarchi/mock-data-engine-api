from __future__ import annotations
from collections.abc import Callable, Iterable, Mapping, MutableMapping, \
    Sequence
from typing import Any, Mapping, Optional
from .errors import IssueCode

DETAIL_KEYS: dict[IssueCode, tuple[str, ...]] = {
    IssueCode.REQUIRED: ('field',), IssueCode.EXTRA: ('key',),
    IssueCode.TYPE: ('expected', 'received'),
    IssueCode.RANGE: ('allowed', 'received'),
    IssueCode.REGEX: ('pattern', 'received'),
    IssueCode.ENUM: ('allowed', 'received'),
    IssueCode.ALIAS: ('alias', 'canonical'),
    IssueCode.DEPRECATION: ('name', 'since'), IssueCode.RULE: ('reason',)}

# TODO: Unused?
def shape_detail(code: IssueCode, detail: Optional[Mapping[str, Any]] = None,
                 **kwargs: Any) -> Optional[dict[str, Any]]:
    """Shape detail.

        Args:
            code (IssueCode): Value.
            detail (Optional[Mapping[str, Any]]): Value.
            **kwargs (Any): Keyword arguments.

        Returns:
    Optional[dict[str, Any]]: Value."""
    if detail is None and (not kwargs):
        return None
    data: dict[str, Any] = {}
    if isinstance(detail, Mapping):
        data.update(detail)
    data.update(kwargs)
    required = DETAIL_KEYS.get(code, tuple())
    normalized = {}
    for k in required:
        if k in data:
            normalized[k] = data[k]
    return normalized or None
