import inspect
from abc import abstractmethod


class BaseGenerator:
    @abstractmethod
    def generate(self, ctx):
        ...

    def _sanity_check(self, ctx):
        # placeholder validation
        ...

    @classmethod
    def _init_fields(cls):
        fields = getattr(cls, "_cached_init_fields", None)
        if fields is None:
            sig = inspect.signature(cls.__init__)
            fields = tuple(n for n in sig.parameters if n != "self")
            setattr(cls, "_cached_init_fields", fields)
        return fields

    @classmethod
    def from_spec(cls, builder, spec: dict):
        """Default: just forward params into constructor."""
        params = {k: v for k, v in spec.items() if k != "type"}
        return cls(**params)

    def configure(self, *args, **kwargs):
        init_names = self._init_fields()
        for position, value in enumerate(args):
            if position < len(init_names):
                setattr(self, init_names[position], value)
        for name, value in kwargs.items():
            if name in init_names:
                setattr(self, name, value)
        return self

    def reset(self):
        for name in self._init_fields():
            setattr(self, name, None)
        return self
