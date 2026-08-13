import unittest

from xiaole_core.errors import ModelUnavailable
from xiaole_core.models import (
    ModelError,
    ModelRouter,
    OpenAICompatibleProvider,
)


class Provider:
    def __init__(self, value=None, error=None): self.value, self.error, self.calls, self.arguments = value, error, 0, []
    def complete(self, *_args, **_kwargs):
        self.calls += 1; self.arguments.append((_args, _kwargs))
        if self.error: raise self.error
        return self.value


class Response:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


class Transport:
    def __init__(self, response):
        self.response = response
        self.calls = 0

    def post(self, *_args, **_kwargs):
        self.calls += 1
        return self.response


class ModelTests(unittest.TestCase):
    def test_primary_and_single_fallback_are_bounded(self):
        primary, fallback = Provider(error=ModelError("timeout", retryable=True)), Provider("fallback answer")
        result = ModelRouter(primary, fallback).complete("system", [], "r1")
        self.assertEqual(result.text, "fallback answer")
        self.assertTrue(result.fallback)
        self.assertEqual((primary.calls, fallback.calls), (1, 1))
        self.assertEqual(primary.arguments, fallback.arguments)

    def test_primary_authentication_failure_uses_configured_fallback_with_identical_context(self):
        prompt = "minimal-profile-context"
        messages = [{"role": "user", "content": "current question"}]
        primary = OpenAICompatibleProvider(
            "https://api.deepseek.com/chat/completions",
            "configured-but-rejected-key",
            "deepseek-chat",
            transport=Transport(Response(401, {"error": {"message": "unauthorized"}})),
        )
        fallback = Provider("fallback answer")
        result = ModelRouter(primary, fallback).complete(prompt, messages, "auth-fallback")
        self.assertEqual(result.text, "fallback answer")
        self.assertTrue(result.fallback)
        self.assertEqual(fallback.arguments[0][0], (prompt, messages, "auth-fallback"))

    def test_nonretryable_or_double_failure_is_safe(self):
        fallback = Provider("must not run")
        with self.assertRaises(ModelUnavailable):
            ModelRouter(Provider(error=ModelError("auth", retryable=False)), fallback).complete("s", [], "r")
        self.assertEqual(fallback.calls, 0)
        with self.assertRaises(ModelUnavailable):
            ModelRouter(Provider(error=ModelError("timeout", True)), Provider(error=ModelError("down", True))).complete("s", [], "r")

    def test_billing_402_uses_each_provider_at_most_once_and_logs_safely(self):
        deepseek_transport = Transport(Response(402, {
            "error": {
                "message": "Insufficient Balance",
                "type": "invalid_request_error",
                "code": "invalid_request_error",
            }
        }))
        qwen_transport = Transport(Response(200, {
            "choices": [{"message": {"content": "Qwen answer"}}]
        }))
        router = ModelRouter(
            OpenAICompatibleProvider(
                "https://api.deepseek.com/chat/completions",
                "deepseek-secret",
                "deepseek-chat",
                transport=deepseek_transport,
            ),
            OpenAICompatibleProvider(
                "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
                "qwen-secret",
                "qwen-plus",
                transport=qwen_transport,
            ),
        )

        with self.assertLogs("xiaole_core.models", level="WARNING") as logs:
            result = router.complete("system", [], "request-402")

        self.assertEqual(result.text, "Qwen answer")
        self.assertTrue(result.fallback)
        self.assertEqual((deepseek_transport.calls, qwen_transport.calls), (1, 1))
        rendered_logs = "\n".join(logs.output)
        self.assertIn("provider=deepseek", rendered_logs)
        self.assertIn("category=billing_quota", rendered_logs)
        self.assertIn("request_id=request-402", rendered_logs)
        self.assertNotIn("deepseek-secret", rendered_logs)
        self.assertNotIn("qwen-secret", rendered_logs)

    def test_unknown_402_does_not_fallback(self):
        deepseek_transport = Transport(Response(402, {
            "error": {"message": "request rejected", "code": "unknown"}
        }))
        fallback = Provider("must not run")

        with self.assertRaises(ModelUnavailable):
            ModelRouter(
                OpenAICompatibleProvider(
                    "https://api.deepseek.com/chat/completions",
                    "deepseek-secret",
                    "deepseek-chat",
                    transport=deepseek_transport,
                ),
                fallback,
            ).complete("system", [], "request-unknown-402")

        self.assertEqual(deepseek_transport.calls, 1)
        self.assertEqual(fallback.calls, 0)

    def test_billing_402_and_fallback_failure_raise_honest_error_once(self):
        deepseek_transport = Transport(Response(402, {
            "error": {"message": "Insufficient Balance"}
        }))
        qwen_transport = Transport(Response(503, {
            "error": {"message": "service unavailable"}
        }))
        router = ModelRouter(
            OpenAICompatibleProvider(
                "https://api.deepseek.com/chat/completions",
                "deepseek-secret",
                "deepseek-chat",
                transport=deepseek_transport,
            ),
            OpenAICompatibleProvider(
                "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
                "qwen-secret",
                "qwen-plus",
                transport=qwen_transport,
            ),
        )

        with self.assertRaisesRegex(ModelUnavailable, "model service unavailable"):
            router.complete("system", [], "request-double-failure")

        self.assertEqual((deepseek_transport.calls, qwen_transport.calls), (1, 1))


if __name__ == "__main__": unittest.main()
