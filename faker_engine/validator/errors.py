VAL_MISSING_REQUIRED = "VAL_MISSING_REQUIRED"
VAL_TYPE_MISMATCH = "VAL_TYPE_MISMATCH"
VAL_ENUM_INVALID = "VAL_ENUM_INVALID"
VAL_RANGE_VIOLATION = "VAL_RANGE_VIOLATION"
VAL_PATTERN_MISMATCH = "VAL_PATTERN_MISMATCH"
VAL_KEY_UNKNOWN = "VAL_KEY_UNKNOWN"
VAL_ALIAS_UNDECLARED = "VAL_ALIAS_UNDECLARED"
VAL_DEPRECATED_FIELD = "VAL_DEPRECATED_FIELD"
VAL_CROSS_RULE = "VAL_CROSS_RULE"


def map_pydantic_error(err):
    etype = getattr(err, "type", None) or (
        err.get("type") if isinstance(err, dict) else None) or ""
    loc = getattr(err, "loc", None) or (
        err.get("loc") if isinstance(err, dict) else ())
    msg = getattr(err, "msg", None) or (
        err.get("msg") if isinstance(err, dict) else "validation error")

    code = VAL_TYPE_MISMATCH
    if isinstance(etype, str):
        if etype.startswith("missing"):
            code = VAL_MISSING_REQUIRED
        elif etype.startswith("enum"):
            code = VAL_ENUM_INVALID
        elif ("greater_than" in etype) or ("less_than" in etype) or (
                "ge" in etype) or ("le" in etype) or ("range" in etype):
            code = VAL_RANGE_VIOLATION
        elif ("string_pattern_mismatch" in etype) or ("pattern" in etype):
            code = VAL_PATTERN_MISMATCH
        else:
            code = VAL_TYPE_MISMATCH

    path = ".".join(str(p) for p in (loc or ()))
    return {"code": code, "path": path, "message": str(msg), "hint": None}
