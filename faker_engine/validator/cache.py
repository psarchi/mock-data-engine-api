from __future__ import annotations


class SchemaCache:
    def __init__(self, root):
        self.root = root

    def build(self, force):
        return {}

    def load(self, name):
        return {}

    def fingerprint(self, generator_obj):
        return "ok"
