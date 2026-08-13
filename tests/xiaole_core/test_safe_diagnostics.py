import json
import logging
import unittest

from pydantic import ValidationError

from tests.xiaole_core.test_real_use_recovery import Action, Context, Model, ReadGateway
from xiaole_core.brain import BrainCore
from xiaole_core.schemas import BrainRequest, ProfileGatewayResponse
from xiaole_core.safe_diagnostics import Core2SafeDiagnosticsEvent


class CapturingHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.messages = []

    def emit(self, record):
        self.messages.append(record.getMessage())


class SafeDiagnosticsPersistenceTests(unittest.TestCase):
    def setUp(self):
        self.handler = CapturingHandler()
        self.logger = logging.getLogger("xiaole_ai")
        self.logger.addHandler(self.handler)
        self.logger.setLevel(logging.INFO)

    def tearDown(self):
        self.logger.removeHandler(self.handler)

    def events(self):
        return [json.loads(line) for line in self.handler.messages if line.startswith('{"event":"core2_safe_diagnostics"')]

    def brain(self, model=None, read=None):
        read = read or ReadGateway()
        return BrainCore(Context(), model or Model(), read, Action(), read_gateway=read)

    def test_event_model_rejects_non_whitelist_fields(self):
        with self.assertRaises(ValidationError):
            Core2SafeDiagnosticsEvent(
                request_id="r", intent="knowledge", scope="current_employment",
                gateways_used=["profile"], model_called=False,
                profile_gateway_called=True, profile_gateway_result="success",
                profile_current_school_state="ready", deterministic_profile_hit=True,
                profile_reason_codes=["current_school_ready"], prompt="must-not-enter-log",
            )

    def test_deterministic_current_school_emits_one_final_event(self):
        model = Model("must-not-run")
        response = self.brain(model).respond(BrainRequest(message="我现在在哪个学校工作？"), "u")
        events = self.events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0], {
            "event":"core2_safe_diagnostics", "request_id":response.request_id,
            "intent":"knowledge", "scope":"current_employment", "gateways_used":["profile"],
            "model_called":False, "profile_gateway_called":True,
            "profile_gateway_result":"success", "profile_current_school_state":"ready",
            "deterministic_profile_hit":True,
            "profile_reason_codes":["profile_request_success","current_school_ready","deterministic_profile_hit"],
        })
        self.assertEqual(model.calls, 0)

    def test_profile_failures_emit_safe_gateway_categories(self):
        cases = (
            (ProfileGatewayResponse(result="unauthorized", reason_codes=["profile_http_401"]), "unauthorized", "profile_http_401"),
            (ProfileGatewayResponse(result="unavailable", reason_codes=["profile_timeout"]), "unavailable", "profile_timeout"),
        )
        for gateway_value, result, reason in cases:
            with self.subTest(reason=reason):
                self.handler.messages.clear()
                class Gateway(ReadGateway):
                    def profile(self, _rid): return gateway_value
                self.brain(Model("safe fallback"), Gateway()).respond(BrainRequest(message="我现在在哪个学校工作？"), "u")
                event = self.events()[0]
                self.assertEqual(event["profile_gateway_result"], result)
                self.assertIn(reason, event["profile_reason_codes"])

    def test_model_fallback_is_recorded_without_sensitive_content(self):
        markers = ("private-question", "private-school", "Authorization", "token", "https://private", "raw exception", "memory text")
        class FallbackModel(Model):
            def complete(self, *_):
                self.calls += 1
                return type("Result", (), {"text":"safe answer","model":"qwen","fallback":True})()
        self.brain(FallbackModel()).respond(BrainRequest(message=markers[0]), "u")
        serialized = json.dumps(self.events()[0], ensure_ascii=False)
        self.assertTrue(self.events()[0]["model_called"])
        for marker in markers:
            self.assertNotIn(marker, serialized)

    def test_scope_is_intent_router_reason_not_data_access_scope(self):
        event = self.brain().respond(BrainRequest(message="你好"), "u")
        self.assertEqual(self.events()[0]["scope"], "conversation_rule")
        self.assertEqual(event.intent.value, "conversation")


if __name__ == "__main__": unittest.main()
