import random
import faker
from .errors import InvalidSeedError, InvalidRNGError, InvalidLocaleError, ContextError


class GenContext:
    def __init__(self, seed=None, rng=None, locale=None):
        if rng is not None and not isinstance(rng, random.Random):
            raise InvalidRNGError("rng must be an instance of random.Random")
        self.rng = rng or random.Random(seed)
        self.seed = seed
        self.locale = locale
        self._faker = None

    @property
    def faker(self):
        if self._faker is None:
            try:
                f = faker.Faker(self.locale) if self.locale else faker.Faker()
            except Exception as e:
                raise InvalidLocaleError(str(e))
            f.seed_instance(self.rng.randint(0, 2**31 - 1))
            self._faker = f
        return self._faker
