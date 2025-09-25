import random


class GenContext:
    def __init__(self, seed):
        if seed is None:
            self.rng = random.Random()
        else:
            self.rng = random.Random(seed)
