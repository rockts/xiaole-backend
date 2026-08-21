import unittest
from datetime import datetime, timezone

from llm_gateway import (
    BudgetExceeded,
    GovernanceUnavailable,
    InMemoryLedger,
    LLMGateway,
    LLMRequest,
    ModelPolicyError,
)


class Response:
    def __init__(self, status=200, text="ok", usage=None):
        self.status_code = status
        self._payload = {
            "choices": [{"message": {"content": text}}],
            "usage": usage or {
                "prompt_tokens": 120,
                "completion_tokens": 30,
                "prompt_cache_hit_tokens": 20,
                "prompt_cache_miss_tokens": 100,
            },
        }

    def json(self):
        return self._payload


class Transport:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def request(**overrides):
    values = dict(
        caller="legacy.chat",
        source="legacy",
        request_id="request-1",
        task_id=None,
        priority="user",
        model="deepseek-v4-flash",
        allow_pro=False,
        system="system",
        messages=[{"role": "user", "content": "hello"}],
        memory_context="",
        tool_context="",
        max_output_tokens=256,
    )
    values.update(overrides)
    return LLMRequest(**values)


class LLMGatewayTests(unittest.TestCase):
    def build(self, outcomes=None, ledger=None, sleeps=None, **kwargs):
        transport = Transport(outcomes or [Response()])
        gateway = LLMGateway(
            api_key="test-placeholder",
            transport=transport,
            ledger=ledger or InMemoryLedger(),
            sleeper=(sleeps if sleeps is not None else []).append,
            clock=lambda: datetime(2026, 8, 21, 8, 0, tzinfo=timezone.utc),
            **kwargs,
        )
        return gateway, transport

    def test_background_cannot_request_pro(self):
        gateway, transport = self.build()
        with self.assertRaises(ModelPolicyError):
            gateway.complete(request(
                priority="background",
                model="deepseek-v4-pro",
                allow_pro=True,
            ))
        self.assertEqual(len(transport.calls), 0)

    def test_pro_requires_explicit_foreground_permission(self):
        gateway, transport = self.build()
        with self.assertRaises(ModelPolicyError):
            gateway.complete(request(model="deepseek-v4-pro"))
        self.assertEqual(len(transport.calls), 0)

    def test_legacy_model_names_normalize_to_flash(self):
        gateway, transport = self.build()
        gateway.complete(request(model="deepseek-chat"))
        self.assertEqual(
            transport.calls[0][1]["json"]["model"],
            "deepseek-v4-flash",
        )

    def test_context_categories_and_total_are_bounded(self):
        gateway, transport = self.build(
            context_limits={
                "system": 8,
                "history": 12,
                "memory": 4,
                "tool": 4,
                "user": 4,
                "total": 24,
            }
        )
        result = gateway.complete(request(
            system="s" * 100,
            messages=[
                {"role": "assistant", "content": "old" * 30},
                {"role": "user", "content": "new" * 30},
            ],
            memory_context="m" * 100,
            tool_context="t" * 100,
        ))
        payload = transport.calls[0][1]["json"]
        combined = "".join(m["content"] for m in payload["messages"])
        self.assertLessEqual(len(combined), 24)
        self.assertEqual(
            set(result.truncated_categories),
            {"system", "history", "memory", "tool", "user", "total"},
        )

    def test_retry_is_bounded_and_exponential(self):
        import requests

        sleeps = []
        gateway, transport = self.build(
            outcomes=[requests.Timeout(), Response(503), Response()],
            sleeps=sleeps,
        )
        result = gateway.complete(request())
        self.assertEqual(result.text, "ok")
        self.assertEqual(len(transport.calls), 3)
        self.assertEqual(sleeps, [1.0, 2.0])
        self.assertEqual(result.attempt_count, 3)

    def test_non_retryable_error_stops_immediately(self):
        gateway, transport = self.build(outcomes=[Response(401), Response()])
        with self.assertRaises(Exception):
            gateway.complete(request())
        self.assertEqual(len(transport.calls), 1)

    def test_foreground_task_call_cap_blocks_fourth_call(self):
        ledger = InMemoryLedger()
        gateway, transport = self.build(
            outcomes=[Response(), Response(), Response(), Response()],
            ledger=ledger,
        )
        for index in range(3):
            gateway.complete(request(caller=f"legacy.stage{index}"))
        with self.assertRaises(BudgetExceeded):
            gateway.complete(request(caller="legacy.stage4"))
        self.assertEqual(len(transport.calls), 3)

    def test_background_budget_does_not_consume_foreground_pool(self):
        ledger = InMemoryLedger()
        gateway, transport = self.build(
            outcomes=[Response(), Response(), Response()],
            ledger=ledger,
            budget_limits={
                "user_hour": 2,
                "user_day": 2,
                "background_hour": 1,
                "background_day": 1,
                "global_hour": 3,
                "global_day": 3,
            },
        )
        gateway.complete(request(
            request_id="background-1",
            task_id="job-1",
            priority="background",
        ))
        with self.assertRaises(BudgetExceeded):
            gateway.complete(request(
                request_id="background-2",
                task_id="job-2",
                priority="background",
            ))
        gateway.complete(request(request_id="user-2"))
        self.assertEqual(len(transport.calls), 2)

    def test_usage_record_contains_cost_tokens_duration_and_result(self):
        ledger = InMemoryLedger()
        gateway, _ = self.build(ledger=ledger)
        result = gateway.complete(request())
        record = ledger.records[0]
        self.assertEqual(record["caller"], "legacy.chat")
        self.assertEqual(record["request_id"], "request-1")
        self.assertEqual(record["model"], "deepseek-v4-flash")
        self.assertEqual(record["input_tokens"], 120)
        self.assertEqual(record["output_tokens"], 30)
        self.assertEqual(record["cache_hit_tokens"], 20)
        self.assertEqual(record["cache_miss_tokens"], 100)
        self.assertGreater(record["estimated_cost_cny"], 0)
        self.assertGreaterEqual(record["duration_ms"], 0)
        self.assertEqual(record["result"], "success")
        self.assertIsNone(record["error_category"])
        self.assertEqual(result.input_tokens, 120)

    def test_ledger_failure_prevents_network_call(self):
        class BrokenLedger:
            def reserve(self, *_args, **_kwargs):
                raise OSError("ledger unavailable")

        gateway, transport = self.build(ledger=BrokenLedger())
        with self.assertRaises(GovernanceUnavailable):
            gateway.complete(request())
        self.assertEqual(len(transport.calls), 0)

    def test_execution_lease_allows_only_one_consumer(self):
        ledger = InMemoryLedger()
        gateway, _ = self.build(ledger=ledger)
        self.assertTrue(gateway.acquire_execution_lease("scheduler:hour-1", 60))
        self.assertFalse(gateway.acquire_execution_lease("scheduler:hour-1", 60))

    def test_three_ordinary_chats_remain_below_ten_calls(self):
        ledger = InMemoryLedger()
        gateway, transport = self.build(
            outcomes=[Response() for _ in range(6)], ledger=ledger
        )
        for chat in range(3):
            for stage in ("intent", "answer"):
                gateway.complete(request(
                    request_id=f"chat-{chat}", caller=f"core2.{stage}"
                ))
        self.assertEqual(len(transport.calls), 6)

    def test_hourly_summary_aggregates_calls_tokens_and_cost(self):
        ledger = InMemoryLedger()
        gateway, _ = self.build(
            outcomes=[Response(), Response()], ledger=ledger
        )
        gateway.complete(request(request_id="summary-1"))
        gateway.complete(request(request_id="summary-2"))
        summary = ledger.summarize("hour", "2026-08-21T08")
        self.assertEqual(summary["calls"], 2)
        self.assertEqual(summary["input_tokens"], 240)
        self.assertEqual(summary["output_tokens"], 60)
        self.assertEqual(summary["successes"], 2)
        self.assertGreater(summary["estimated_cost_cny"], 0)


if __name__ == "__main__":
    unittest.main()
