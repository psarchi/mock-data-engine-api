
import faker_engine.generators as gens
from faker_engine.core.registry import GeneratorRegistry
from faker_engine.core.factory import GeneratorFactory

def test_registry_and_factory_resolve():
    reg = GeneratorRegistry().register_from_module(gens)
    fac = GeneratorFactory(reg)
    g = fac.resolve("bool")
    # generate via context
    from faker_engine.context import GenContext
    assert isinstance(g.generate(GenContext(seed=1)), bool)
