class FakerEngineError(Exception):
    def __init__(self, message=None, path=None):
        self.path = path
        if path:
            message = f"[{path}] {message}"
        super().__init__(message or "")


class ContextError(FakerEngineError): pass


class InvalidSeedError(ContextError): pass


class InvalidRNGError(ContextError): pass


class InvalidLocaleError(ContextError): pass


class ConfigError(FakerEngineError): pass


class MissingSchemaError(ConfigError): pass


class SchemaParseError(ConfigError): pass


class BatchConfigError(ConfigError): pass


class StreamingConfigError(ConfigError): pass


class SpecError(FakerEngineError): pass


class MissingTypeError(SpecError): pass


class UnknownTypeError(SpecError): pass


class FromSpecMissingError(SpecError): pass


class InvalidSpecStructureError(SpecError): pass


class NormalizationError(SpecError): pass


class RegistryError(FakerEngineError): pass


class DuplicateAliasError(RegistryError): pass


class UnknownGeneratorError(RegistryError): pass


class InvalidRegistrationError(RegistryError): pass


class FactoryError(FakerEngineError): pass


class MissingConfigureMethodError(FactoryError): pass


class GeneratorInstantiationError(FactoryError): pass


class GeneratorError(FakerEngineError): pass


class GeneratorInitError(GeneratorError): pass


class GenerationError(GeneratorError): pass


class InvalidParameterError(GeneratorError): pass


class OutOfBoundsError(GeneratorError): pass


class EmptyEnumError(GeneratorError): pass


class InvalidChildGeneratorError(GeneratorError): pass


class CompositeError(GeneratorError): pass


class ArrayConfigError(CompositeError): pass


class MissingChildError(ArrayConfigError): pass


class InvalidMinItemsError(ArrayConfigError): pass


class InvalidMaxItemsError(ArrayConfigError): pass


class MaxLessThanMinError(ArrayConfigError): pass


class ObjectConfigError(CompositeError): pass


class MissingFieldsError(ObjectConfigError): pass


class InvalidFieldTypeError(ObjectConfigError): pass


class APIError(FakerEngineError): pass


class BuildFailure(APIError): pass


class InvalidGeneratorInstanceError(APIError): pass


class FunctionalAPIError(APIError): pass


class OOPAPIError(APIError): pass
