import random
from faker_engine.core.registry import GeneratorRegistry
from faker_engine.core.factory import GeneratorFactory
from faker_engine.context import GenContext
from faker_engine.spec_builder import SpecBuilder
import faker_engine.generators as gens

# build registry and auto-register everything from generators
_registry = GeneratorRegistry().register_from_module(gens)
_factory = GeneratorFactory(_registry)
_builder = SpecBuilder(_registry)


# -------- functional API --------

def build_generator(spec):
    return _builder.build(spec)


def generate_one(gen, seed=None, locale="en_US"):
    rng = random.Random(seed)
    ctx = GenContext(rng=rng, locale=locale)
    return gen.generate(ctx)


def generate_many(gen, n=10, seed=None, locale="en_US"):
    rng = random.Random(seed)
    ctx = GenContext(rng=rng, locale=locale)
    return [gen.generate(ctx) for _ in range(n)]


# -------- OOP API --------

class FakerEngine:
    def __init__(self, seed=None, locale="en_US"):
        self.registry = GeneratorRegistry().register_from_module(gens)
        self.factory = GeneratorFactory(self.registry)
        self.builder = SpecBuilder(self.registry)
        self.rng = random.Random(seed)
        self.ctx = GenContext(rng=self.rng, locale=locale)

    def build(self, spec):
        return self.builder.build(spec)

    def generate_one(self, gen):
        return gen.generate(self.ctx)

    def generate_many(self, gen, n=10):
        return [gen.generate(self.ctx) for _ in range(n)]
