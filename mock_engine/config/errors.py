from mock_engine.errors import MockEngineError


class ConfigError(MockEngineError):
    """Base error for config package."""


class ConfigBuildError(ConfigError):
    """Raised when building models from config fails."""


class ConfigValidationError(ConfigError):
    """Raised when configuration values fail validation."""


class ConfigPathError(ConfigError):
    """Raised for missing/invalid configuration paths."""


class ConfigSchemaError(ConfigError):
    """Raised for schema-related configuration issues."""


class ModuleBuildError(ConfigError):
    """Raised to constructor related errors."""
