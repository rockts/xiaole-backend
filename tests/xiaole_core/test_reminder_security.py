import unittest

from xiaole_core.gateways.reminder import ReminderGateway
from xiaole_core.reminders import ReminderOrchestrator


class NoNetwork:
    def __init__(self): self.calls=[]
    def get(self, *args, **kwargs): self.calls.append((args,kwargs)); raise AssertionError("network called")
    def post(self, *args, **kwargs): self.calls.append((args,kwargs)); raise AssertionError("network called")


class ReminderSecurityTests(unittest.TestCase):
    def test_unconfigured_brain_reminder_path_fails_closed_without_network(self):
        transport=NoNetwork()
        outcome=ReminderOrchestrator(ReminderGateway("", "", transport=transport)).handle("查询提醒", [], "c", "r")
        self.assertEqual(outcome.answer, "提醒服务暂时不可用，请稍后再试。")
        self.assertEqual(transport.calls, [])

    def test_private_values_are_not_gateway_attributes_or_exception_text(self):
        token="token-value-must-not-leak"
        gateway=ReminderGateway("http://core", token, transport=NoNetwork())
        self.assertNotIn(token, repr(gateway))


if __name__ == "__main__": unittest.main()
