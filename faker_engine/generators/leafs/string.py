import re
from string import ascii_lowercase, ascii_uppercase, digits

try:
    import exrex
except Exception as _e:  # pragma: no cover
    exrex = None

from faker_engine.errors import ContextError, InvalidParameterError, OutOfBoundsError
from faker_engine.generators.base import BaseGenerator
from faker_engine.context import GenContext


class StringGenerator(BaseGenerator):
    
    __meta__ = {
        'aliases': {
        'charset': 'charset',
        'max_length': 'max_length',
        'min_length': 'min_length',
        'n_charset': 'n_charset',
        'n_type': 'n_type',
        'regex': 'regex',
        'string_type': 'string_type',
        'template': 'template',
        },
        'deprecations': [],
        'rules': [],
        # TODO: introduce per-generator versioning (SemVer) once contracts stabilize.
    }
    __slots__ = (
        'string_type',
        'min_length', 'max_length',
        'regex', 'template',
        'charset', 'n_type', 'n_charset'
    )
    __aliases__ = ('string', 'str')

    def __init__(self, string_type=None, min_length=None, max_length=None,
                 regex=None, template=None, charset=None, n_type=None, n_charset=None):
        self.string_type = string_type
        self.min_length = min_length
        self.max_length = max_length
        self.regex = regex
        self.template = template
        self.charset = n_charset if charset is None else charset
        self.n_type = n_type
        self.n_charset = n_charset

    def _resolve_faker_provider(self, name, ctx: GenContext):
        fk = getattr(ctx, 'faker', None)
        if fk is None and hasattr(ctx, 'get_faker'):
            fk = ctx.get_faker()
        if fk is None:
            raise ContextError('Faker is not available in generation context')
        # allow dotted paths like 'profile' or 'internet.domain_name'
        attr = fk
        for part in str(name).split('.'):
            if not hasattr(attr, part):
                raise InvalidParameterError("Faker attribute '%s' not found" % name)
            attr = getattr(attr, part)
        if callable(attr):
            return attr
        return lambda: attr

    @classmethod
    def from_spec(cls, builder, spec):
        return cls(
            string_type=spec.get('string_type'),
            min_length=spec.get('min_length'),
            max_length=spec.get('max_length'),
            regex=spec.get('regex'),
            template=spec.get('template'),
            charset=spec.get('charset'),
            n_type=spec.get('n_type'),
            n_charset=spec.get('n_charset'),
        )

    def _sanity_check(self, ctx: GenContext):
        if self.min_length is not None and self.max_length is not None and int(self.min_length) > int(self.max_length):
            raise OutOfBoundsError('min_length must be <= max_length')
        if self.string_type and (self.regex or self.template):
            raise InvalidParameterError('string_type is mutually exclusive with regex/template')
        if self.template and self.regex:
            raise InvalidParameterError('template is mutually exclusive with regex')

    def _token_chars(self):
        if self.n_charset:
            return self.n_charset
        if self.n_type == 'numeric':
            return digits
        if self.n_type == 'lower':
            return ascii_lowercase
        return ascii_uppercase

    def _apply_template(self, ctx: GenContext):
        s = self.template
        def repl(m):
            ncount = len(m.group(1))
            chars = self._token_chars()
            out = []
            for _ in range(ncount):
                out.append(chars[ctx.rng.randint(0, len(chars) - 1)])
            return ''.join(out)
        return re.sub(r'\{(n+)\}', repl, s)

    def _plain_synth(self, ctx: GenContext):
        chars = self.charset or ascii_lowercase
        lo = int(self.min_length) if self.min_length is not None else 1
        hi = int(self.max_length) if self.max_length is not None else 100
        if hi < lo:
            hi = lo
        length = ctx.rng.randint(lo, hi)
        out = []
        for _ in range(length):
            out.append(chars[ctx.rng.randint(0, len(chars) - 1)])
        return ''.join(out)

    def _regex_generate(self, ctx: GenContext):
        if exrex is None:
            raise InvalidParameterError('exrex is required for regex generation but is not installed')
        pattern = self.regex
        if not isinstance(pattern, str) or not pattern:
            raise InvalidParameterError('regex must be a non-empty string')
        # exrex.getone has no seed param; make it deterministic by
        # temporarily seeding the global random used inside exrex.
        import random
        state = random.getstate()
        try:
            # derive a stable seed from ctx RNG without disturbing it
            rnd_seed = int(ctx.rng.random() * 1_000_000_000)
            random.seed(rnd_seed)
            return exrex.getone(pattern)
        except Exception as e:
            raise InvalidParameterError('regex generation failed: %s' % e)
        finally:
            random.setstate(state)

    def generate(self, ctx: GenContext):
        self._sanity_check(ctx)
        if self.template:
            return self._apply_template(ctx)
        if self.regex:
            return self._regex_generate(ctx)
        if self.string_type:
            provider = self._resolve_faker_provider(self.string_type, ctx)
            out = provider()
            if out is None or not isinstance(out, str):
                raise InvalidParameterError("Faker attribute '%s' did not return a string" % self.string_type)
            return out
        return self._plain_synth(ctx)
