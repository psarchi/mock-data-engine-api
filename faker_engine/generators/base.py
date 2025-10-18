from __future__ import annotations
from typing import Any, TYPE_CHECKING
import inspect
from abc import abstractmethod

if TYPE_CHECKING:  # import only for type checking to avoid runtime cycles
    from faker_engine.context import GenContext


class BaseGenerator:
    __abstract__ = True

    @abstractmethod
    def generate(self, ctx: "GenContext") -> Any:
        ...

    def _sanity_check(self, ctx: "GenContext") -> None:
        ...

    @classmethod
    def _init_fields(cls) -> list[str]:
        fields = getattr(cls, "_cached_init_fields", None)
        if fields is not None:
            return fields
        sig = inspect.signature(cls.__init__)  # type: ignore[method-assign]
        # Exclude 'self'
        fields = [p.name for p in sig.parameters.values() if p.name != "self"]
        setattr(cls, "_cached_init_fields", fields)
        return fields

    @classmethod
    def from_spec(cls, builder: object,
                  spec: dict[str, object]) -> "BaseGenerator":
        init_names = cls._init_fields()
        init_kwargs: dict[str, object] = {}
        for name in init_names:
            if name in spec:
                init_kwargs[name] = spec[name]
        inst = cls(**init_kwargs)  # type: ignore[misc]
        # Pass through remaining keys to configure()
        remaining = {k: v for k, v in spec.items() if k not in init_names}
        if remaining:
            inst.configure(**remaining)
        return inst

    def configure(self, *args: object, **kwargs: object) -> "BaseGenerator":
        init_names = self._init_fields()
        for position, value in enumerate(args):
            if position < len(init_names):
                setattr(self, init_names[position], value)
        for name, value in kwargs.items():
            if name in init_names:
                setattr(self, name, value)
        return self

    def reset(self) -> "BaseGenerator":
        for name in self._init_fields():
            setattr(self, name, None)
        return self
