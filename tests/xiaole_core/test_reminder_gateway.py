import unittest

import requests

from xiaole_core.errors import ReminderUnavailable
from xiaole_core.gateways.reminder import ReminderGateway
from xiaole_core.schemas import ReminderCreateCommand


class Response:
    def __init__(self, status, body):
        self.status_code, self.body = status, body

    def json(self):
        if isinstance(self.body, Exception):
            raise self.body
        return self.body


class Transport:
    def __init__(self, responses):
        self.responses, self.calls = list(responses), []

    def post(self, url, **kwargs):
        self.calls.append(("POST", url, kwargs))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    def get(self, url, **kwargs):
        self.calls.append(("GET", url, kwargs))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def reminder(reminder_id="rem-1", status="enabled", **overrides):
    value = {
        "reminder_id": reminder_id,
        "source_system": "xiaole",
        "title": "部署验收",
        "category": "work",
        "event_at": "2026-08-20T09:00:00+00:00",
        "notify_at": "2026-08-20T08:00:00+00:00",
        "timezone": "Asia/Shanghai",
        "amount": None,
        "currency": "CNY",
        "notification_title": "部署验收",
        "notification_body": "private body",
        "metadata": {"channel": "xiaole-v2"},
        "status": status,
        "requires_confirmation": False,
        "confirmed_at": None,
    }
    value.update(overrides)
    return value


class ReminderGatewayTests(unittest.TestCase):
    def command(self):
        return ReminderCreateCommand(
            idempotency_key="xiaole:req-1:reminder",
            title="部署验收",
            category="work",
            event_at="2026-08-20T17:00:00+08:00",
            notify_at="2026-08-20T16:00:00+08:00",
            notification_title="部署验收",
            notification_body="private body",
            metadata={"channel": "xiaole-v2"},
        )

    def test_create_uses_exact_contract_and_projects_private_fields(self):
        transport = Transport([Response(202, {"reminder": reminder(), "created": True, "request_id": "r"})])
        result = ReminderGateway("http://core", "secret", transport=transport).create(self.command(), "req-1")

        method, url, kwargs = transport.calls[0]
        self.assertEqual((method, url), ("POST", "http://core/v1/reminders"))
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer secret")
        self.assertEqual(kwargs["headers"]["X-Request-ID"], "req-1")
        self.assertEqual(kwargs["json"]["source_system"], "xiaole")
        self.assertEqual(kwargs["json"]["timezone"], "Asia/Shanghai")
        self.assertEqual(kwargs["json"]["event_at"], "2026-08-20T17:00:00+08:00")
        self.assertEqual(result.reminder_id, "rem-1")
        serialized = result.model_dump_json()
        self.assertNotIn("private body", serialized)
        self.assertNotIn("secret", serialized)

    def test_list_get_and_state_actions_use_exact_paths(self):
        transport = Transport([
            Response(200, {"reminders": [reminder()], "request_id": "r"}),
            Response(200, {"reminder": reminder(), "request_id": "r"}),
            Response(200, {"reminder": reminder(status="enabled"), "request_id": "r"}),
            Response(200, {"reminder": reminder(status="paused"), "request_id": "r"}),
            Response(200, {"reminder": reminder(status="cancelled"), "request_id": "r"}),
        ])
        gateway = ReminderGateway("http://core/", "secret", transport=transport)
        self.assertEqual(len(gateway.list({"status": "enabled", "category": "work"}, "r")), 1)
        gateway.get("rem-1", "r")
        gateway.confirm("rem-1", "r")
        gateway.pause("rem-1", "r")
        gateway.cancel("rem-1", "r")
        self.assertEqual(
            [(method, url) for method, url, _ in transport.calls],
            [
                ("GET", "http://core/v1/reminders"),
                ("GET", "http://core/v1/reminders/rem-1"),
                ("POST", "http://core/v1/reminders/rem-1/confirm"),
                ("POST", "http://core/v1/reminders/rem-1/pause"),
                ("POST", "http://core/v1/reminders/rem-1/cancel"),
            ],
        )
        self.assertEqual(transport.calls[0][2]["params"], {"status": "enabled", "category": "work"})

    def test_unconfigured_gateway_makes_no_network_call(self):
        transport = Transport([])
        with self.assertRaises(ReminderUnavailable) as raised:
            ReminderGateway("", "", transport=transport).list({}, "r")
        self.assertEqual(str(raised.exception), "reminder service unavailable")
        self.assertEqual(transport.calls, [])

    def test_transport_and_server_details_are_not_exposed(self):
        markers = (
            requests.Timeout("token=must-not-leak amount=999"),
            Response(500, {"detail": {"message": "private backend trace"}}),
            Response(200, ValueError("private invalid json")),
        )
        for marker in markers:
            with self.subTest(marker=type(marker).__name__):
                gateway = ReminderGateway("http://core", "secret", transport=Transport([marker]))
                with self.assertRaises(ReminderUnavailable) as raised:
                    gateway.list({}, "r")
                text = str(raised.exception)
                self.assertEqual(text, "reminder service unavailable")
                self.assertNotIn("private", text)
                self.assertNotIn("999", text)


if __name__ == "__main__":
    unittest.main()
