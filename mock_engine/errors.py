"""Module: mock_engine.errors.

This module defines the top-level and domain-specific exceptions used throughout
the project. It follows a top-down design: broad categories inherit from
`FakerEngineError`, and subpackages extend the tree locally without renaming
existing types.

All exceptions accept an optional `path` argument to prefix messages with a
contextual location (e.g., a schema path or config key)."""
from __future__ import annotations
from typing import Optional


class MockEngineError(Exception):
    """Base exception for all mock_engine errors.

    Args:
        message: Human-readable error message.
        path: Optional dotted or slash-separated location used to prefix the
            message for easier debugging (e.g., "fields.event_date").

    Examples:
        >>> raise MockEngineError("something went wrong")
        Traceback (most recent call last):
        ...
        FakerEngineError: something went wrong

        >>> raise MockEngineError("missing field", path="fields.event_date")
        Traceback (most recent call last):
        ...
        FakerEngineError: [fields.event_date] missing field
    """

    def __init__(self: object, message: Optional[str] = None,
                 path: tuple[str, ...] | None = None) -> None:
        """Init _.

Args:
    message (Optional[str]): Value.
    path (tuple[str, ...] | None): Schema location for error reporting.

Returns:
    None: Value."""
        self.path = path
        if path:
            message = f'[{path}] {message}'
        super().__init__(message or '')


class ContextError(MockEngineError):
    """Errors related to generation context (seed, RNG, locale)."""


class InvalidSeedError(ContextError):
    """Provided seed is invalid or unsupported by the RNG backend."""


class InvalidRNGError(ContextError):
    """Random number generator cannot be constructed or configured."""


class InvalidLocaleError(ContextError):
    """Requested locale is not available or not supported."""


class ConfigError(MockEngineError):
    """Top-level configuration problems (DEPRICATED.yaml, runtime flags, etc.)."""


class MissingSchemaError(ConfigError):
    """Schema file cannot be located or loaded."""


class SchemaParseError(ConfigError):
    """Schema file exists but failed to parse (syntax/format)."""


class BatchConfigError(ConfigError):
    """Invalid or inconsistent batch mode configuration."""


class StreamingConfigError(ConfigError):
    """Invalid or inconsistent streaming mode configuration."""


class SpecError(MockEngineError):
    """Specification-level problems (invalid type, structure, normalization)."""


class MissingTypeError(SpecError):
    """`type` key is required but missing in a spec node."""


class UnknownTypeError(SpecError):
    """`type` key provided but does not map to a known generator/contract."""


class FromSpecMissingError(SpecError):
    """Generator/contract is missing a `from_spec` constructor."""


class InvalidSpecStructureError(SpecError):
    """Spec structure is invalid for the targeted generator/contract."""


class NormalizationError(SpecError):
    """Spec values cannot be normalized or coerced into valid form."""


class APIError(MockEngineError):
    """Errors surfaced at the API layer (request handling/build failures)."""


class BuildFailure(APIError):
    """Factory/build process failed while preparing a handler response."""


class InvalidGeneratorInstanceError(APIError):
    """API received a generator instance that does not conform to the base API."""


class FunctionalAPIError(APIError):
    """Errors specific to functional-style API usage."""


class OOPAPIError(APIError):
    """Errors specific to OOP-style API usage."""
