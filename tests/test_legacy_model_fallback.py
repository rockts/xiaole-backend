import os
import unittest
from unittest.mock import Mock, patch

import requests


original_database_url = os.environ.get("DATABASE_URL")
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
with patch("sqlalchemy.sql.schema.MetaData.create_all"):
    import agent as agent_module
    from agent import XiaoLeAgent
from error_handler import APIError
from llm_gateway import InMemoryLedger, LLMGateway
if original_database_url is None:
    os.environ.pop("DATABASE_URL", None)
else:
    os.environ["DATABASE_URL"] = original_database_url


class Response:
    def __init__(self, status_code, payload=None, lines=None):
        self.status_code = status_code
        self.payload = payload or {}
        self.lines = lines or []

    def json(self):
        return self.payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} response")

    def iter_lines(self):
        return iter(self.lines)


class Transport:
    def __init__(self, response):
        self.response, self.calls = response, 0

    def post(self, *_args, **_kwargs):
        self.calls += 1
        return self.response


def build_agent(response):
    instance = XiaoLeAgent.__new__(XiaoLeAgent)
    instance.model = "deepseek-v4-flash"
    instance._http_session = Transport(response)
    instance.llm_gateway = LLMGateway(
        api_key="deepseek-test-key",
        transport=instance._http_session,
        ledger=InMemoryLedger(),
        sleeper=lambda _delay: None,
        max_retries=0,
    )
    instance._get_llm_parameters = lambda _style: {
        "temperature": 0.5,
        "max_tokens": 512,
        "top_p": 0.9,
    }
    return instance


class LegacyModelFallbackTests(unittest.TestCase):
    def test_short_instructional_greeting_is_simple_chat(self):
        instance = XiaoLeAgent.__new__(XiaoLeAgent)

        self.assertTrue(instance._is_simple_chat("你好，只回复 OK"))

    def test_tool_request_is_not_simple_chat(self):
        instance = XiaoLeAgent.__new__(XiaoLeAgent)

        self.assertFalse(instance._is_simple_chat("帮我查一下今天北京的天气"))

    def test_nonstream_authentication_failure_falls_back_once(self):
        instance = build_agent(Response(401))
        instance._call_qwen_fallback = Mock(return_value="Qwen answer")

        result = instance._call_deepseek("system", "message")

        self.assertEqual(result, "Qwen answer")
        self.assertEqual(instance._http_session.calls, 1)
        instance._call_qwen_fallback.assert_called_once_with(
            "system", "message", 512
        )

    def test_history_authentication_failure_falls_back_once(self):
        instance = build_agent(Response(401))
        instance._call_qwen_with_history_fallback = Mock(
            return_value="Qwen history answer"
        )

        result = instance._call_deepseek_with_history(
            "system", [{"role": "user", "content": "message"}]
        )

        self.assertEqual(result, "Qwen history answer")
        self.assertEqual(instance._http_session.calls, 1)
        instance._call_qwen_with_history_fallback.assert_called_once()

    def test_stream_authentication_failure_falls_back_once(self):
        instance = build_agent(Response(401))
        instance._call_qwen_stream_fallback = Mock(
            return_value=iter(["Qwen ", "stream"])
        )

        result = list(instance._call_deepseek_stream(
            "system", [{"role": "user", "content": "message"}]
        ))

        self.assertEqual(result, ["Qwen ", "stream"])
        self.assertEqual(instance._http_session.calls, 1)
        instance._call_qwen_stream_fallback.assert_called_once()

    def test_nonstream_billing_402_falls_back_once(self):
        instance = build_agent(Response(402))
        instance._call_qwen_fallback = Mock(return_value="Qwen answer")

        result = instance._call_deepseek("system", "message")

        self.assertEqual(result, "Qwen answer")
        self.assertEqual(instance._http_session.calls, 1)
        instance._call_qwen_fallback.assert_called_once_with(
            "system", "message", 512
        )

    def test_history_billing_402_falls_back_once(self):
        instance = build_agent(Response(402))
        instance._call_qwen_with_history_fallback = Mock(
            return_value="Qwen history answer"
        )

        result = instance._call_deepseek_with_history(
            "system", [{"role": "user", "content": "message"}]
        )

        self.assertEqual(result, "Qwen history answer")
        self.assertEqual(instance._http_session.calls, 1)
        instance._call_qwen_with_history_fallback.assert_called_once()

    def test_stream_billing_402_falls_back_once(self):
        instance = build_agent(Response(402))
        instance._call_qwen_stream_fallback = Mock(
            return_value=iter(["Qwen ", "stream"])
        )

        result = list(instance._call_deepseek_stream(
            "system", [{"role": "user", "content": "message"}]
        ))

        self.assertEqual(result, ["Qwen ", "stream"])
        self.assertEqual(instance._http_session.calls, 1)
        instance._call_qwen_stream_fallback.assert_called_once()

    def test_billing_402_and_qwen_failure_stop_after_one_attempt_each(self):
        instance = build_agent(Response(402))
        instance._call_qwen_fallback = Mock(
            side_effect=RuntimeError("Qwen unavailable")
        )

        with self.assertRaisesRegex(RuntimeError, "Qwen unavailable"):
            instance._call_deepseek("system", "message")

        self.assertEqual(instance._http_session.calls, 1)
        self.assertEqual(instance._call_qwen_fallback.call_count, 1)


if __name__ == "__main__":
    unittest.main()
