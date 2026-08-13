import unittest

from xiaole_core.intent import IntentRouter
from xiaole_core.schemas import Intent


class IntentRouterTests(unittest.TestCase):
    def test_routes_real_use_recovery_scopes(self):
        router = IntentRouter()
        self.assertEqual(router.classify("今天我最应该关注什么？", [], "r1").intent, Intent.STATUS)
        self.assertEqual(router.classify("我最近有什么值得写的内容吗？我想发个公众号。", [], "r2").intent, Intent.PLANNING)
        self.assertEqual(router.classify("我在科创比赛中得过奖吗？", [], "r3").intent, Intent.KNOWLEDGE)
        self.assertEqual(router.classify("我现在在哪个学校工作？", [], "r4").intent, Intent.KNOWLEDGE)
        self.assertEqual(router.classify("给我手机发一条测试通知。", [], "r3").intent, Intent.ACTION)

    def test_ambiguous_message_uses_classifier_without_executing_anything(self):
        calls = []
        router = IntentRouter(lambda message, history, request_id: calls.append(message) or "knowledge")
        result = router.classify("帮我看看这个", [], "r4")
        self.assertEqual(result.intent, Intent.KNOWLEDGE)
        self.assertTrue(result.used_fallback)
        self.assertEqual(calls, ["帮我看看这个"])

    def test_invalid_classifier_output_falls_back_to_conversation(self):
        router = IntentRouter(lambda *_: "tool_loop")
        self.assertEqual(router.classify("帮我看看这个", [], "r5").intent, Intent.CONVERSATION)


if __name__ == "__main__":
    unittest.main()
