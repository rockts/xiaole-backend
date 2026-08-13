import unittest
import requests

from xiaole_core.errors import ActionUnavailable, MemoryUnavailable
from xiaole_core.gateways.action import ActionGateway
from xiaole_core.gateways.memory import MemoryGateway
from xiaole_core.schemas import ActionCommand


class Response:
    def __init__(self, status, body): self.status_code, self.body = status, body
    def json(self):
        if isinstance(self.body, Exception): raise self.body
        return self.body


class Transport:
    def __init__(self, responses): self.responses, self.calls = list(responses), []
    def post(self, url, **kwargs): self.calls.append(("POST", url, kwargs)); return self.responses.pop(0)
    def get(self, url, **kwargs):
        self.calls.append(("GET", url, kwargs))
        response = self.responses.pop(0)
        if isinstance(response, Exception): raise response
        return response


class GatewayTests(unittest.TestCase):
    def test_profile_classifies_success_without_exposing_payload_in_metadata(self):
        secret_value = "敏感学校名称"
        result = MemoryGateway("http://local", "secret", transport=Transport([
            Response(200, {"fields":{"current_school":{"value":secret_value,"status":"confirmed","subject":"current_user"}}})
        ])).profile("r")
        self.assertEqual(result.result, "success")
        self.assertEqual(result.reason_codes, ["profile_request_success"])
        self.assertEqual(result.payload["fields"]["current_school"]["value"], secret_value)
        self.assertNotIn(secret_value, str({"result":result.result,"reason_codes":result.reason_codes}))

    def test_profile_classifies_401_as_unauthorized(self):
        result = MemoryGateway("http://local", transport=Transport([Response(401, {})])).profile("r")
        self.assertEqual(result.result, "unauthorized")
        self.assertEqual(result.reason_codes, ["profile_http_401"])
        self.assertEqual(result.payload, {})

    def test_profile_classifies_timeout_as_unavailable_without_exception_text(self):
        marker = "https://secret.example/path?token=must-not-leak"
        result = MemoryGateway("http://local", transport=Transport([requests.Timeout(marker)])).profile("r")
        self.assertEqual(result.result, "unavailable")
        self.assertEqual(result.reason_codes, ["profile_timeout"])
        self.assertNotIn(marker, repr(result))

    def test_profile_classifies_invalid_json_and_schema(self):
        cases = (
            (Response(200, ValueError("raw secret response")), "profile_invalid_json"),
            (Response(200, []), "profile_schema_invalid"),
        )
        for response, reason in cases:
            with self.subTest(reason=reason):
                result = MemoryGateway("http://local", transport=Transport([response])).profile("r")
                self.assertEqual(result.result, "invalid_response")
                self.assertEqual(result.reason_codes, [reason])

    def test_memory_preserves_complete_sources_and_contract(self):
        sources = [{"title":"通知", "original_path":"x.pdf", "issue_date":"2026-08-11", "custom":"keep"}]
        transport = Transport([Response(200, {"ok":True,"question":"q","answer":"grounded","sources":sources,"flags":{"degraded":False}})])
        result = MemoryGateway("http://127.0.0.1:8765", "secret", transport=transport).ask("q", [], "r1")
        self.assertEqual(result.sources, sources)
        call = transport.calls[0]
        self.assertEqual(call[2]["json"], {"q":"q","mode":"ask","context":[]})
        self.assertEqual(call[2]["headers"]["X-KOS-Token"], "secret")
        self.assertNotIn("secret", result.model_dump_json())

    def test_memory_failures_do_not_become_answers(self):
        for response in (Response(403, {}), Response(200, ValueError()), Response(200, {"ok":False})):
            with self.subTest(response=response.status_code), self.assertRaises(MemoryUnavailable):
                MemoryGateway("http://local", transport=Transport([response])).ask("q", [], "r")

    def test_memory_resolves_relative_source_links_against_configured_lezhi(self):
        sources = [{"title":"通知", "open_url":"/file?path=a.pdf", "preview_url":"https://public.example/p"}]
        transport = Transport([Response(200, {"ok":True,"answer":"grounded","sources":sources,"flags":{}})])
        result = MemoryGateway("http://127.0.0.1:8765", transport=transport).ask("q", [], "r")
        self.assertEqual(result.sources[0]["open_url"], "http://127.0.0.1:8765/file?path=a.pdf")
        self.assertEqual(result.sources[0]["preview_url"], "https://public.example/p")

    def test_action_uses_real_task_contract_and_hides_internal_details(self):
        transport = Transport([
            Response(202, {"task":{"task_id":"t1","status":"pending"},"created":True,"request_id":"r1"}),
            Response(200, {"task":{"task_id":"t1","status":"success","result":{"ok":True},"attempts":[{"stdout":"secret","evidence":{"delivery_status":"sent","http_status":200,"target_service":"monitor-service"}}],"audit_events":[{}]},"request_id":"r1"}),
        ])
        command = ActionCommand.notification("c1", "r1")
        result = ActionGateway("http://127.0.0.1:8766", "token", transport=transport, sleeper=lambda _:None).execute(command, "r1")
        self.assertEqual(result.status, "success")
        payload = transport.calls[0][2]["json"]
        self.assertEqual(payload["task_type"], "notification.send")
        self.assertEqual(payload["source_system"], "xiaole")
        self.assertEqual(transport.calls[0][2]["headers"]["Authorization"], "Bearer token")
        serialized = result.model_dump_json()
        self.assertNotIn("stdout", serialized)
        self.assertNotIn("audit_events", serialized)
        self.assertNotIn("target_service", serialized)
        self.assertEqual(result.evidence, {"execution_confirmed": True})

    def test_action_terminal_failure_never_reports_success(self):
        transport = Transport([Response(202,{"task":{"task_id":"t","status":"pending"}}),Response(200,{"task":{"task_id":"t","status":"dead","error":{"code":"x"}}})])
        result = ActionGateway("http://local", "t", transport=transport, sleeper=lambda _:None).execute(ActionCommand.notification("c","r"), "r")
        self.assertEqual(result.status, "dead")
        self.assertNotIn("成功", result.summary)

    def test_action_timeout_reports_accepted_waiting_delivery_not_success(self):
        transport = Transport([
            Response(202,{"task":{"task_id":"t","status":"pending"}}),
            Response(200,{"task":{"task_id":"t","status":"running"}}),
        ])
        result = ActionGateway(
            "http://local", "t", timeout=.001, poll_interval=1,
            transport=transport, sleeper=lambda _:None,
        ).execute(ActionCommand.notification("c","r"), "r")
        self.assertEqual(result.status, "timeout")
        self.assertIn("通知已受理，正在等待发送", result.summary)
        self.assertNotIn("执行成功", result.summary)

    def test_unconfigured_action_is_unavailable_without_network_call(self):
        transport = Transport([])
        with self.assertRaises(ActionUnavailable):
            ActionGateway("", "", transport=transport).execute(ActionCommand.notification("c", "r"), "r")
        self.assertEqual(transport.calls, [])


if __name__ == "__main__": unittest.main()
