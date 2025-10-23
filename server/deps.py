from __future__ import annotations
from functools import lru_cache
from faker_engine.validator.validator import Validator
from faker_engine.validator.registry_adapter import RegistryAdapter
from faker_engine.validator.normalizer import SpecNormalizer
from faker_engine.validator.model_provider import ModelProvider


@lru_cache(maxsize=1)
def get_validator() -> Validator:
    return Validator(
        registry=RegistryAdapter(),
        normalizer=SpecNormalizer(),
        models=ModelProvider(),
    )
