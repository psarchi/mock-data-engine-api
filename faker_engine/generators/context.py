import random
import faker

class GenContext:
    def __init__(self, seed = None):
        self.seed = seed
        if seed is None:
            self.rng = random.Random()
        else:
            self.rng = random.Random(seed)
        self._faker = None

    @property
    def faker(self) -> faker.Faker:
        if self._faker is None:
            f = faker.Faker()
            f.random = self.rng
            self._faker = f
        return self._faker