"""Public API surface for building and using the mock data engine.

This module exposes helpers to build generators from specs and to produce
values with deterministic RNG/locale control.
"""
from __future__ import annotations

import random
from collections.abc import Mapping
from typing import TYPE_CHECKING

from mock_engine.core.factory import GeneratorFactory
from mock_engine.core.registry import GeneratorRegistry
from mock_engine.context import GenContext
from mock_engine.generators.base import BaseGenerator
from mock_engine.spec_builder import SpecBuilder
import mock_engine.generators as gens

if TYPE_CHECKING:  # import only for typing to avoid cycles
    from mock_engine.types import JsonValue  # noqa: F401

__all__ = [
    "build_generator",
    "generate_one",
    "generate_many",
    "MockEngine",
]

# Initialize global builder for the simple functional API.
_registry = GeneratorRegistry().register_from_module(gens)
_factory = GeneratorFactory(_registry)
_builder = SpecBuilder(_registry)


def build_generator(spec: Mapping[str, object]) -> BaseGenerator:
    """Build a generator from a spec mapping.

    Args:
        spec (Mapping[str, object]): Specification mapping parsed from configuration.

    Returns:
        BaseGenerator: Configured generator instance.
    """
    return _builder.build(spec)


def generate_one(
    gen: BaseGenerator,
    seed: int | None = None,
    locale: str = "en_US",
) -> "JsonValue":
    """Generate a single value from ``gen``.

    Args:
        gen (BaseGenerator): Generator instance.
        seed (int | None): Seed for deterministic behavior. ``None`` for random.
        locale (str): Locale identifier passed to :class:`GenContext`.

    Returns:
        JsonValue: Generated value.
    """
    rng = random.Random(seed)
    ctx = GenContext(rng=rng, locale=locale)
    return gen.generate(ctx)


def generate_many(
    gen: BaseGenerator,
    n: int = 10,
    seed: int | None = None,
    locale: str = "en_US",
) -> list["JsonValue"]:
    """Generate ``n`` values from ``gen``.

    Args:
        gen (BaseGenerator): Generator instance.
        n (int): Number of values to generate.
        seed (int | None): Seed for deterministic behavior. ``None`` for random.
        locale (str): Locale identifier passed to :class:`GenContext`.

    Returns:
        list[JsonValue]: List of generated values.
    """
    rng = random.Random(seed)
    ctx = GenContext(rng=rng, locale=locale)
    return [gen.generate(ctx) for _ in range(n)]


class MockEngine:
    """High-level façade for building generators and producing values.

    Wraps a registry, factory, and builder plus a reusable RNG/context.

    Args:
        seed (int | None): Seed for deterministic behavior. ``None`` for random.
        locale (str): Locale identifier passed to :class:`GenContext`.
    """

    __slots__ = ("registry", "factory", "builder", "rng", "ctx")

    def __init__(self, seed: int | None = None, locale: str = "en_US") -> None:
        """Initialize engine components and context.

        Args:
            seed (int | None): Seed for deterministic behavior. ``None`` for random.
            locale (str): Locale identifier passed to :class:`GenContext`.
        """
        self.registry = GeneratorRegistry().register_from_module(gens)
        self.factory = GeneratorFactory(self.registry)
        self.builder = SpecBuilder(self.registry)
        self.rng = random.Random(seed)
        self.ctx = GenContext(rng=self.rng, locale=locale)

    def build(self, spec: Mapping[str, object]) -> BaseGenerator:
        """Build a generator from a spec mapping.

        Args:
            spec (Mapping[str, object]): Specification mapping parsed from configuration.

        Returns:
            BaseGenerator: Configured generator instance.
        """
        return self.builder.build(spec)

    def generate_one(self, gen: BaseGenerator) -> "JsonValue":
        """Generate a single value using the engine context.

        Args:
            gen (BaseGenerator): Generator instance.

        Returns:
            JsonValue: Generated value.
        """
        return gen.generate(self.ctx)

    def generate_many(self, gen: BaseGenerator, n: int = 10) -> list["JsonValue"]:
        """Generate ``n`` values using the engine context.

        Args:
            gen (BaseGenerator): Generator instance.
            n (int): Number of values to generate.

        Returns:
            list[JsonValue]: List of generated values.
        """
        return [gen.generate(self.ctx) for _ in range(n)]
