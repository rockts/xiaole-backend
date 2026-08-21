import unittest

from xiaole_core.intent import IntentRouter
from xiaole_core.schemas import Intent


class IntentRouterTests(unittest.TestCase):
    def test_routes_self_profile_phrase_family_without_model_classifier(self):
        calls = []
        router = IntentRouter(lambda *args: calls.append(args) or "conversation")
        messages = (
            "你认识我吗？",
            "你知道我是谁吗？",
            "我是谁？",
            "介绍一下我",
            "你对我了解多少？",
            "说说你知道的我",
            "你记得我什么？",
        )

        for message in messages:
            with self.subTest(message=message):
                decision = router.classify(message, [], "self-profile")
                self.assertEqual(decision.intent, Intent.KNOWLEDGE)
                self.assertEqual(decision.reason_code, "self_profile")
        self.assertEqual(calls, [])

    def test_routes_employment_history_separately_from_current_employment(self):
        router = IntentRouter()

        history = router.classify("我以前在哪些学校工作过？", [], "history")
        current = router.classify("我现在在哪个学校工作？", [], "current")

        self.assertEqual((history.intent, history.reason_code), (Intent.KNOWLEDGE, "employment_history"))
        self.assertEqual((current.intent, current.reason_code), (Intent.KNOWLEDGE, "current_employment"))

    def test_self_profile_does_not_capture_specific_personal_fact_questions(self):
        router = IntentRouter()

        for message in ("你知道我的电话号码吗？", "介绍一下我的学校"):
            with self.subTest(message=message):
                self.assertNotEqual(router.classify(message, [], "specific").reason_code, "self_profile")

    def test_routes_relational_self_description_into_self_profile_without_classifier(self):
        calls = []
        router = IntentRouter(lambda *args: calls.append(args) or "conversation")

        decision = router.classify("我对你来说是什么样的人？", [], "relational-profile")

        self.assertEqual(decision.intent, Intent.KNOWLEDGE)
        self.assertEqual(decision.reason_code, "self_profile")
        self.assertEqual(calls, [])

    def test_routes_real_use_recovery_scopes(self):
        router = IntentRouter()
        self.assertEqual(router.classify("今天我最应该关注什么？", [], "r1").intent, Intent.STATUS)
        self.assertEqual(router.classify("我最近有什么值得写的内容吗？我想发个公众号。", [], "r2").intent, Intent.PLANNING)
        self.assertEqual(router.classify("我在科创比赛中得过奖吗？", [], "r3").intent, Intent.KNOWLEDGE)
        self.assertEqual(router.classify("我现在在哪个学校工作？", [], "r4").intent, Intent.KNOWLEDGE)
        self.assertEqual(router.classify("给我手机发一条测试通知。", [], "r3").intent, Intent.ACTION)

    def test_routes_unified_reminder_operations_before_generic_action(self):
        router = IntentRouter()
        for message in ("创建工作提醒", "查询提醒", "查看提醒 rem-1", "确认启用该提醒", "暂停提醒 rem-1", "取消提醒 rem-1"):
            with self.subTest(message=message):
                self.assertEqual(router.classify(message, [], "r").intent, Intent.REMINDER)

    def test_routes_relative_bark_reminder_to_unified_center(self):
        self.assertEqual(
            IntentRouter().classify("5分钟后用 Bark 提醒我洗完澡", [], "r").intent,
            Intent.REMINDER,
        )

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
