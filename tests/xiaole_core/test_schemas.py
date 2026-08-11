import unittest
from pydantic import ValidationError

from xiaole_core.schemas import ActionCommand, Diagnostics


class SchemaTests(unittest.TestCase):
    def test_only_notification_send_is_a_valid_phase_a_action(self):
        command = ActionCommand.notification("c1", "r1")
        self.assertEqual(command.task_type, "notification.send")
        self.assertEqual(command.parameters["delivery"], "bark")
        self.assertEqual(command.parameters["title"], "【小乐 2.0】")
        self.assertEqual(command.parameters["body"], "小乐已成功通过小可完成首次真实 Action。")
        with self.assertRaises(ValidationError):
            ActionCommand(task_type="shell.exec", parameters={}, conversation_id="c1", request_id="r1")

    def test_diagnostics_rejects_secret_fields(self):
        with self.assertRaises(ValidationError):
            Diagnostics(model="deepseek", token="secret")


if __name__ == "__main__":
    unittest.main()
