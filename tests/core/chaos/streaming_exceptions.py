STREAMING_UNDETECTABLE = {
    "auth_fault",
    "http_error",
    "http_mismatch",
    "header_anomaly",
    "random_header_case",
    "encoding_corrupt",
}

ARCHITECTURE_UNDETECTABLE = {
    "data_drift",
    "schema_drift",
}

ALL_UNDETECTABLE_STREAMING = STREAMING_UNDETECTABLE | ARCHITECTURE_UNDETECTABLE


def is_streaming_detectable(chaos_op: str) -> bool:
    return chaos_op not in ALL_UNDETECTABLE_STREAMING


def is_rest_detectable(chaos_op: str) -> bool:
    """Check if a chaos op can be detected in REST responses.

    For REST, only architecture-level drifts are undetectable.
    HTTP-level ops (auth_fault, http_error, etc.) CAN be detected via status codes.
    """
    return chaos_op not in ARCHITECTURE_UNDETECTABLE


def get_detection_mode(chaos_op: str, is_streaming: bool = False) -> str:
    """Get detection mode for a chaos op.

    Returns:
        "full": Can detect actual effects + metadata
        "metadata_only": Can only check metadata (not actual effects)
        "skip": Cannot detect at all, skip test
    """
    if is_streaming:
        if chaos_op in ARCHITECTURE_UNDETECTABLE:
            return "skip"
        elif chaos_op in STREAMING_UNDETECTABLE:
            return "metadata_only"
        else:
            return "full"
    else:
        if chaos_op in ARCHITECTURE_UNDETECTABLE:
            return "skip"
        else:
            return "full"
