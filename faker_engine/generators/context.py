import random
import faker


class GenContext:
    def __init__(self, seed=None, rng=None, locale=None):
        if rng is not None:
            self.rng = rng
        else:
            self.rng = random.Random(seed)

        self.seed = seed
        self.locale = locale
        self._faker = None

    @property
    def faker(self):
        if self._faker is None:
            f = faker.Faker(self.locale) if self.locale else faker.Faker()
            f.seed_instance(self.rng.randint(0, 2 ** 31 - 1))
            self._faker = f
        return self._faker
