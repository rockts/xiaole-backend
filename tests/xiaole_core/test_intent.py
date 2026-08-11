import unittest

from xiaole_core.intent import IntentRouter
from xiaole_core.schemas import Intent


class IntentRouterTests(unittest.TestCase):
    def test_routes_only_the_three_phase_a_intents(self):
        router = IntentRouter()
        self.assertEqual(router.classify("你好，今天我们做什么？", [], "r1").intent, Intent.CONVERSATION)
        self.assertEqual(router.classify("最近有什么值得我关注的官方通知？", [], "r2").intent, Intent.MEMORY)
        self.assertEqual(router.classify("给我手机发一条测试通知。", [], "r3").intent, Intent.ACTION)

    def test_ambiguous_message_uses_classifier_without_executing_anything(self):
        calls = []
        router = IntentRouter(lambda message, history, request_id: calls.append(message) or "memory")
        result = router.classify("帮我看看这个", [], "r4")
        self.assertEqual(result.intent, Intent.MEMORY)
        self.assertTrue(result.used_fallback)
        self.assertEqual(calls, ["帮我看看这个"])

    def test_invalid_classifier_output_falls_back_to_conversation(self):
        router = IntentRouter(lambda *_: "tool_loop")
        self.assertEqual(router.classify("帮我看看这个", [], "r5").intent, Intent.CONVERSATION)


if __name__ == "__main__":
    unittest.main()
