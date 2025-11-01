"""Dependency providers for FastAPI routes.

Exposes cached constructors for the validator and a settings accessor. Behavior
is unchanged; docstrings and typing follow the golden style.
"""
from __future__ import annotations

from functools import lru_cache

from faker_engine.config import get_config_manager
from faker_engine.validator.model_provider import ModelProvider
from faker_engine.validator.normalizer import SpecNormalizer
from faker_engine.validator.registry_adapter import RegistryAdapter
from faker_engine.validator.validator import Validator

__all__ = ["get_validator", "get_settings"]


@lru_cache(maxsize=1)
def get_validator() -> Validator:
    """Return a cached :class:`Validator` instance.

    Returns:
        Validator: Validator wired to the default registry/normalizer/model provider.
    """
    return Validator(
        registry=RegistryAdapter(),
        normalizer=SpecNormalizer(),
        models=ModelProvider(),
    )


def get_settings() -> object:
    """Return the current effective settings/config object.

    Returns:
        object: Framework settings (concrete type depends on the config layer).
    """
    # TODO(types): Narrow return type once the concrete settings model is public.
    return get_config_manager().effective()
