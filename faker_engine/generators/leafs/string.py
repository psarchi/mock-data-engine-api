import re
from string import ascii_lowercase, ascii_uppercase, digits
from faker_engine.errors import ContextError, InvalidParameterError, OutOfBoundsError
from faker_engine.generators.base import BaseGenerator
from faker_engine.context import GenContext


class StringGenerator(BaseGenerator):
    __slots__ = (
        'string_type',
        'min_length', 'max_length',
        'regex', 'template',
        'charset', 'n_type', 'n_charset'
    )
    __aliases__ = ('string', 'str')

    def __init__(self, string_type=None, min_length=None, max_length=None,
                 regex=None, template=None, charset=None, n_type=None, n_charset=None):
        self.min_length = min_length
        self.max_length = max_length
        self.string_type = string_type
        self.regex = regex
        self.template = template
        self.charset = charset
        self.n_type = n_type
        self.n_charset = n_charset

    @classmethod
    def from_spec(cls, builder, spec):
        st = spec.get('string_type') or spec.get('provider')
        return cls(
            string_type=st,
            min_length=spec.get('min_length'),
            max_length=spec.get('max_length'),
            regex=spec.get('regex'),
            template=spec.get('template'),
            charset=spec.get('charset'),
            n_type=spec.get('n_type'),
            n_charset=spec.get('n_charset'),
        )

    def _sanity_check(self, ctx):
        if not isinstance(ctx, GenContext):
            raise ContextError('ctx must be an instance of GenContext')
        if self.min_length is not None and self.max_length is not None:
            if int(self.min_length) > int(self.max_length):
                raise InvalidParameterError('min_length must be <= max_length')
        if self.min_length is not None and int(self.min_length) < 0:
            raise OutOfBoundsError('min_length must be >= 0')
        if self.max_length is not None and int(self.max_length) < 0:
            raise OutOfBoundsError('max_length must be >= 0')

    def _resolve_faker_provider(self, string_type, ctx):
        if not string_type:
            raise InvalidParameterError('string_type must be provided for Faker-backed generation')
        name = string_type.lower()
        fake = ctx.faker
        try:
            fn = getattr(fake, name)
        except AttributeError:
            raise InvalidParameterError("Unknown Faker provider: '%s'" % string_type)
        if not callable(fn):
            raise InvalidParameterError("Faker attribute '%s' is not callable" % string_type)
        return fn

    def _token_chars(self):
        if self.n_charset:
            return self.n_charset
        if self.n_type == 'numeric':
            return digits
        if self.n_type == 'lower':
            return ascii_lowercase
        return ascii_uppercase

    def _apply_template(self, ctx):
        s = self.template
        def repl(m):
            ncount = len(m.group(1))
            chars = self._token_chars()
            out = []
            for _ in range(ncount):
                out.append(chars[ctx.rng.randint(0, len(chars) - 1)])
            return ''.join(out)
        return re.sub(r'\{(n+)\}', repl, s)

    def _plain_synth(self, ctx):
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

    def _gen_matching_regex(self, ctx):
        attempts = 100
        pat = re.compile(self.regex)
        for _ in range(attempts):
            candidate = self._plain_synth(ctx)
            if pat.fullmatch(candidate):
                return candidate
        raise InvalidParameterError('could not satisfy regex within attempts')

    def generate(self, ctx):
        self._sanity_check(ctx)
        if self.template:
            return self._apply_template(ctx)
        if self.regex:
            return self._gen_matching_regex(ctx)
        if self.string_type:
            provider = self._resolve_faker_provider(self.string_type, ctx)
            out = provider()
            if not isinstance(out, str):
                raise InvalidParameterError("Faker attribute '%s' did not return a string" % self.string_type)
            return out
        return self._plain_synth(ctx)
