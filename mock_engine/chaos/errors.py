from __future__ import annotations


class ChaosError(Exception):
    """Base class for all Chaos-related errors."""


class RegistryError(ChaosError):
    """Raised when op discovery/lookup fails."""


class ConfigError(ChaosError):
    """Raised for invalid or missing configuration values."""


class OpError(ChaosError):
    """Raised by an individual op during application."""
