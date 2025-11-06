
import mock_engine.generators as gens
from mock_engine.core.registry import GeneratorRegistry
from mock_engine.core.factory import GeneratorFactory

def test_registry_and_factory_resolve():
    reg = GeneratorRegistry().register_from_module(gens)
    fac = GeneratorFactory(reg)
    g = fac.resolve("bool")
    # generate via context
    from mock_engine.context import GenContext
    assert isinstance(g.generate(GenContext(seed=1)), bool)
