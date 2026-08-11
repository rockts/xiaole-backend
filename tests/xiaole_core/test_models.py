import unittest

from xiaole_core.errors import ModelUnavailable
from xiaole_core.models import ModelError, ModelRouter


class Provider:
    def __init__(self, value=None, error=None): self.value, self.error, self.calls = value, error, 0
    def complete(self, *_args, **_kwargs):
        self.calls += 1
        if self.error: raise self.error
        return self.value


class ModelTests(unittest.TestCase):
    def test_primary_and_single_fallback_are_bounded(self):
        primary, fallback = Provider(error=ModelError("timeout", retryable=True)), Provider("fallback answer")
        result = ModelRouter(primary, fallback).complete("system", [], "r1")
        self.assertEqual(result.text, "fallback answer")
        self.assertTrue(result.fallback)
        self.assertEqual((primary.calls, fallback.calls), (1, 1))

    def test_nonretryable_or_double_failure_is_safe(self):
        fallback = Provider("must not run")
        with self.assertRaises(ModelUnavailable):
            ModelRouter(Provider(error=ModelError("auth", retryable=False)), fallback).complete("s", [], "r")
        self.assertEqual(fallback.calls, 0)
        with self.assertRaises(ModelUnavailable):
            ModelRouter(Provider(error=ModelError("timeout", True)), Provider(error=ModelError("down", True))).complete("s", [], "r")


if __name__ == "__main__": unittest.main()
