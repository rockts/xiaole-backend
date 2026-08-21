import json
import re
import unittest

from xiaole_core.brain import BrainCore
from xiaole_core.errors import MemoryUnavailable
from xiaole_core.schemas import BrainRequest, MemoryResult, ProfileGatewayResponse
from tests.xiaole_core.test_self_profile import governed_profile


class Context:
    def resolve(self, _user, cid, _message): return cid or "c"
    def history(self, _user, _cid): return []
    def append_exchange(self, *_): pass


class LegacyHistoryContext(Context):
    def history(self, _user, _cid):
        return [{"role": "assistant", "content": "共享会话Legacy烟铺小学家庭住址饮食旧课程表"}]


class Model:
    def __init__(self, text="综合回答"): self.text, self.prompts, self.calls = text, [], 0
    def complete(self, prompt, messages, _request_id):
        self.calls += 1; self.prompts.append((prompt, messages))
        return type("Result", (), {"text": self.text, "model": "test", "fallback": False})()


class ReadGateway:
    def __init__(self, *, unavailable=()): self.calls, self.unavailable = [], set(unavailable)
    def _value(self, name, value):
        self.calls.append(name)
        if name in self.unavailable: raise MemoryUnavailable("down")
        return value
    def status(self, _rid): return self._value("status", {"today":{"last_scan":"2026-08-13T09:30:00+08:00","new_discovered":1},"high_priority":{"count":1,"items":[{"title":"AI 教育通知"}]},"recommended_items":[{"title":"AI 教育通知"}]})
    def knowledge(self, _rid): return self._value("knowledge", {"recent_additions":{"recent_30d_raw":3,"recent_30d_cards":2,"recent_30d_intelligence":1}})
    def profile(self, _rid): return self._value("profile", {"fields":{"current_school":{"value":"新华门小学","status":"confirmed","subject":"current_user"},"historical_school":{"value":["烟铺小学"],"status":"historical","subject":"current_user"},"education_focus":{"value":["科技教育"],"status":"confirmed","subject":"current_user"},"long_term_projects":{"value":["XiaoLe"],"status":"confirmed","subject":"current_user"}}})
    def ask(self, question, _context, rid):
        return self._value("memory", MemoryResult(answer="可确认的资料包含科创大赛获奖通知，但需区分本人与指导学生。",sources=[
            {"title":"2026秦州区科创大赛一等","snippet":"获奖通知涉及教师、学生与学校，未能仅从标题确认用户本人获奖。","path":"/Users/private/award.pdf","open_url":"http://127.0.0.1/private","token":"must-not-leak","provenance":"memory"},
            {"title":"科创比赛通知","snippet":"指导学生获奖与本人获奖需分开归因。","provenance":"memory"},
        ],confidence="grounded",request_id=rid))


class Action:
    def __init__(self): self.calls=0
    def execute(self, *_): self.calls += 1; raise AssertionError("action must stay isolated")


class RealUseRecoveryTests(unittest.TestCase):
    def brain(self, model=None, read=None, action=None):
        read, action = read or ReadGateway(), action or Action()
        return BrainCore(Context(), model or Model(), read, action, read_gateway=read), read, action

    def test_today_combines_status_and_recommendation_without_external_news_excuse(self):
        brain, read, action = self.brain(Model("今天优先关注 AI 教育通知。"))
        response = brain.respond(BrainRequest(message="今天我最应该关注什么？"), "u")
        self.assertEqual(response.intent.value, "status")
        self.assertEqual(read.calls, ["status"])
        self.assertEqual(response.diagnostics.gateways_used, ["status", "recommendation"])
        self.assertNotIn("没有实时访问", response.answer)
        self.assertEqual(action.calls, 0)

    def test_self_profile_phrasings_use_only_profile_and_never_model_or_shared_history(self):
        class ProfileOnlyGateway(ReadGateway):
            def profile(self, _rid):
                return self._value("profile", ProfileGatewayResponse(
                    payload=governed_profile(), result="success", reason_codes=["profile_request_success"]
                ))

            def ask(self, *_):
                raise AssertionError("self_profile must not call Memory")

        messages = (
            "你认识我吗？", "你知道我是谁吗？", "我是谁？", "介绍一下我",
            "你对我了解多少？", "说说你知道的我", "你记得我什么？",
            "我对你来说是什么样的人？",
        )
        for message in messages:
            with self.subTest(message=message):
                model, read = Model("模型错误回答"), ProfileOnlyGateway()
                brain = BrainCore(LegacyHistoryContext(), model, read, Action(), read_gateway=read)
                response = brain.respond(BrainRequest(message=message), "u")
                self.assertIn("新华门小学", response.answer)
                for forbidden in ("烟铺小学", "家庭", "住址", "饮食", "旧课程表", "科学", "数学"):
                    self.assertNotIn(forbidden, response.answer)
                self.assertEqual(read.calls, ["profile"])
                self.assertEqual(model.calls, 0)
                self.assertEqual(response.diagnostics.gateways_used, ["profile"])
                self.assertEqual(response.diagnostics.profile_scope, "self_profile")
                self.assertEqual(response.diagnostics.renderer, "deterministic")

    def test_employment_history_is_separate_and_uses_only_historical_profile(self):
        class ProfileOnlyGateway(ReadGateway):
            def profile(self, _rid):
                return self._value("profile", ProfileGatewayResponse(
                    payload=governed_profile(), result="success", reason_codes=["profile_request_success"]
                ))

            def ask(self, *_):
                raise AssertionError("employment_history must not call Memory")

        model, read = Model("模型错误回答"), ProfileOnlyGateway()
        brain = BrainCore(LegacyHistoryContext(), model, read, Action(), read_gateway=read)
        response = brain.respond(BrainRequest(message="我以前在哪些学校工作过？"), "u")

        self.assertIn("烟铺小学", response.answer)
        self.assertIn("历史", response.answer)
        self.assertNotIn("新华门小学", response.answer)
        self.assertEqual(read.calls, ["profile"])
        self.assertEqual(model.calls, 0)
        self.assertEqual(response.diagnostics.profile_scope, "employment_history")

    def test_self_profile_profile_failure_is_explicit_and_never_falls_back(self):
        class UnavailableProfile(ReadGateway):
            def profile(self, _rid):
                return self._value("profile", ProfileGatewayResponse(
                    result="unavailable", reason_codes=["profile_timeout"]
                ))

            def ask(self, *_):
                raise AssertionError("Profile failure must not call Memory")

        model, read = Model("Legacy猜测"), UnavailableProfile()
        brain = BrainCore(LegacyHistoryContext(), model, read, Action(), read_gateway=read)
        response = brain.respond(BrainRequest(message="你认识我吗？"), "u")

        self.assertIn("暂时无法读取", response.answer)
        self.assertNotIn("Legacy猜测", response.answer)
        self.assertEqual(read.calls, ["profile"])
        self.assertEqual(model.calls, 0)
        self.assertEqual(response.diagnostics.profile_gateway_result, "unavailable")

    def test_content_ideas_combine_profile_memory_recent_knowledge(self):
        model = Model("1. AI 教育通知：值得写；依据是近期通知。\n2. 科技教育实践：与长期方向相关。\n3. XiaoLe 实用化：可引用项目资料。")
        brain, read, action = self.brain(model)
        response = brain.respond(BrainRequest(message="我最近有什么值得写的内容吗？我想发个公众号。"), "u")
        self.assertEqual(read.calls, ["profile", "knowledge", "status", "memory"])
        self.assertEqual(response.diagnostics.gateways_used, ["profile", "knowledge", "status", "recommendation", "memory"])
        prompt = json.dumps(model.prompts, ensure_ascii=False)
        self.assertIn("科技教育", prompt); self.assertIn("recent_additions", prompt)
        self.assertEqual(action.calls, 0)

    def test_current_school_uses_confirmed_profile_and_ignores_historical_school(self):
        brain, read, _ = self.brain(Model("烟铺小学"))
        response = brain.respond(BrainRequest(message="我现在在哪个学校工作？"), "u")
        self.assertEqual(response.answer, "你现在在新华门小学工作。")
        self.assertEqual(read.calls, ["profile"])
        self.assertTrue(response.diagnostics.profile_gateway_called)
        self.assertEqual(response.diagnostics.profile_gateway_result, "success")
        self.assertEqual(response.diagnostics.profile_current_school_state, "ready")
        self.assertTrue(response.diagnostics.deterministic_profile_hit)
        self.assertEqual(response.diagnostics.profile_reason_codes, ["profile_request_success", "current_school_ready", "deterministic_profile_hit"])

    def test_current_school_safe_diagnostics_cover_all_miss_states(self):
        cases = (
            (ProfileGatewayResponse(result="unauthorized", reason_codes=["profile_http_401"]), "unauthorized", "invalid", "profile_http_401"),
            (ProfileGatewayResponse(result="unavailable", reason_codes=["profile_timeout"]), "unavailable", "invalid", "profile_timeout"),
            (ProfileGatewayResponse(payload={}, result="success", reason_codes=["profile_request_success"]), "missing_fact", "invalid", "profile_fields_missing"),
            (ProfileGatewayResponse(payload={"fields":{}}, result="success", reason_codes=["profile_request_success"]), "missing_fact", "missing", "current_school_missing"),
            (ProfileGatewayResponse(payload={"fields":{"current_school":{"value":"敏感学校名称","status":"candidate","subject":"current_user"}}}, result="success", reason_codes=["profile_request_success"]), "missing_fact", "not_confirmed", "current_school_status_not_confirmed"),
            (ProfileGatewayResponse(payload={"fields":{"current_school":{"value":"敏感学校名称","status":"confirmed","subject":"other"}}}, result="success", reason_codes=["profile_request_success"]), "missing_fact", "wrong_subject", "current_school_subject_not_current_user"),
            (ProfileGatewayResponse(payload={"fields":{"current_school":{"value":"","status":"confirmed","subject":"current_user"}}}, result="success", reason_codes=["profile_request_success"]), "missing_fact", "invalid", "current_school_value_missing"),
        )
        for gateway_value, gateway_result, state, reason in cases:
            with self.subTest(reason=reason):
                class SafeGateway(ReadGateway):
                    def profile(self, _rid):
                        self.calls.append("profile")
                        return gateway_value
                model = Model("现有降级回答")
                brain, _, _ = self.brain(model, SafeGateway())
                response = brain.respond(BrainRequest(message="我现在在哪个学校工作？"), "u")
                diagnostics = response.diagnostics.model_dump()
                self.assertTrue(diagnostics["profile_gateway_called"])
                self.assertEqual(diagnostics["profile_gateway_result"], gateway_result)
                self.assertEqual(diagnostics["profile_current_school_state"], state)
                self.assertFalse(diagnostics["deterministic_profile_hit"])
                self.assertIn(reason, diagnostics["profile_reason_codes"])
                self.assertIn("deterministic_profile_miss", diagnostics["profile_reason_codes"])

    def test_profile_diagnostics_never_serialize_sensitive_data(self):
        marker_values = ("敏感学校名称", "must-not-leak-token", "Authorization", "prompt", "/Users/private", "https://secret.example")
        class SafeGateway(ReadGateway):
            def profile(self, _rid):
                self.calls.append("profile")
                return ProfileGatewayResponse(
                    payload={"fields":{"current_school":{"value":marker_values[0],"status":"candidate","subject":"current_user"}}},
                    result="success", reason_codes=["profile_request_success"],
                )
        response = self.brain(Model("现有降级回答"), SafeGateway())[0].respond(BrainRequest(message="我现在在哪个学校工作？"), "u")
        serialized = response.diagnostics.model_dump_json()
        for marker in marker_values:
            self.assertNotIn(marker, serialized)

    def test_current_school_natural_phrasings_share_deterministic_profile_path(self):
        messages = (
            "我现在在哪个学校工作？",
            "我现在在哪工作？",
            "我在哪个学校？",
            "我目前工作单位是哪？",
            "我现在的学校叫什么？",
            "我现在任职于哪里？",
        )
        for message in messages:
            with self.subTest(message=message):
                model = Model("不应调用模型")
                brain, read, _ = self.brain(model)
                response = brain.respond(BrainRequest(message=message), "u")
                self.assertEqual(response.intent.value, "knowledge")
                self.assertEqual(response.answer, "你现在在新华门小学工作。")
                self.assertEqual(read.calls, ["profile"])
                self.assertEqual(model.calls, 0)

    def test_current_school_accepts_confirmed_profile_field_without_historical_override(self):
        class ProductionProfileGateway(ReadGateway):
            def profile(self, _rid):
                return self._value("profile", {
                    "current_school": {"value": "新华门小学", "status": "confirmed", "subject": "current_user"},
                    "historical_school": {"value": "烟铺小学", "status": "historical", "subject": "current_user"},
                })
        model = Model("烟铺小学")
        brain, read, _ = self.brain(model, ProductionProfileGateway())
        response = brain.respond(BrainRequest(message="我目前工作单位是哪？"), "u")
        self.assertEqual(response.answer, "你现在在新华门小学工作。")
        self.assertEqual(read.calls, ["profile"])
        self.assertEqual(model.calls, 0)

    def test_achievement_uses_profile_and_personal_memory_with_provenance(self):
        brain, read, _ = self.brain(Model("目前只能确认到科创大赛获奖资料，尚不能确认是你本人获奖还是指导学生获奖。"))
        response = brain.respond(BrainRequest(message="我在科创比赛中得过奖吗？"), "u")
        self.assertEqual(read.calls, ["profile", "memory"])
        self.assertEqual(response.sources[0]["provenance"], "memory")
        self.assertIn("目前只能确认到", response.answer)

    def test_achievement_answer_always_distinguishes_all_three_subjects(self):
        brain, _, _ = self.brain(Model("目前只能确认到有相关资料，证据不足。"))
        response = brain.respond(BrainRequest(message="我在科创比赛中得过奖吗？"), "u")
        self.assertIn("你本人", response.answer)
        self.assertIn("你指导的学生", response.answer)
        self.assertIn("学校", response.answer)

    def test_unavailable_dependencies_degrade_honestly_without_false_attribution(self):
        brain, _, _ = self.brain(Model("根据目前可用信息，我暂时无法确认。"), ReadGateway(unavailable={"profile","memory"}))
        response = brain.respond(BrainRequest(message="我在科创比赛中得过奖吗？"), "u")
        self.assertNotIn("乐知确认", response.answer)
        self.assertNotRegex(response.answer, r"(/Users/|token|secret)")

    def test_model_context_minimizes_profile_memory_and_conversation_history(self):
        class HistoryContext(Context):
            def history(self, *_): return [{"role":"user","content":"无关个人秘密 unrelated-history"}]
        model, read, action = Model(), ReadGateway(), Action()
        brain = BrainCore(HistoryContext(), model, read, action, read_gateway=read)
        response = brain.respond(BrainRequest(message="我最近有什么值得写的内容吗？我想发个公众号。"), "u")
        prompt, messages = model.prompts[0]
        self.assertIn("education_focus", prompt)
        self.assertIn("long_term_projects", prompt)
        self.assertNotIn("current_school", prompt)
        self.assertNotIn("烟铺小学", prompt)
        self.assertIn("指导学生获奖", prompt)
        self.assertNotIn("/Users/", prompt)
        self.assertNotIn("must-not-leak", prompt)
        self.assertNotIn("127.0.0.1", prompt)
        self.assertEqual(messages, [{"role":"user","content":"我最近有什么值得写的内容吗？我想发个公众号。"}])
        self.assertNotIn("unrelated-history", prompt + json.dumps(messages, ensure_ascii=False))
        self.assertNotIn("prompt", response.diagnostics.model_dump())

    def test_achievement_sends_no_unrelated_profile_fields_and_selected_snippets_only(self):
        model = Model("目前只能确认到相关获奖资料，不能确认你本人获奖。")
        brain, _, _ = self.brain(model)
        brain.respond(BrainRequest(message="我在科创比赛中得过奖吗？"), "u")
        prompt = model.prompts[0][0]
        self.assertNotIn("current_school", prompt)
        self.assertNotIn("education_focus", prompt)
        self.assertNotIn("long_term_projects", prompt)
        self.assertIn("evidence_snippets", prompt)
        self.assertNotIn("open_url", prompt)
        self.assertNotIn("path", prompt)
        self.assertIn("可确认的资料包含科创大赛获奖通知", prompt)
        self.assertLessEqual(prompt.count('"snippet"'), 5)

    def test_achievement_separates_raw_candidates_model_evidence_and_display_sources(self):
        class ManySourcesGateway(ReadGateway):
            def ask(self, question, _context, rid):
                useful = [
                    {"title": "科创比赛获奖通知", "snippet": "学生和学校获奖，不能证明用户本人获奖。", "open_url": "/preview/award"},
                    {"title": "科创比赛获奖通知", "snippet": "重复来源。", "open_url": "/preview/award"},
                    {"title": "指导学生参赛记录", "snippet": "记录提到指导关系，但主体仍需核验。"},
                    {"title": "学校科技教育成果", "snippet": "学校层面的成果记录。"},
                ]
                garbage = [
                    {"title": f"{index:03d}", "snippet": "解析碎片"} for index in range(30)
                ] + [
                    {"title": "source", "snippet": "技术占位"},
                    {"title": "attachment-001-scan.pdf", "snippet": "附件碎片"},
                    {"title": "", "snippet": "无标题碎片"},
                    {"title": "/Users/private/award.pdf", "snippet": "本地路径"},
                ]
                sources = useful + garbage
                while len(sources) < 47:
                    sources.append({"title": f"attachment-{len(sources):03d}-part", "snippet": "附件碎片"})
                return self._value("memory", MemoryResult(
                    answer="目前只能确认到相关获奖资料，主体证据不足。",
                    sources=sources,
                    confidence="grounded",
                    request_id=rid,
                ))

        model = Model("目前只能确认到相关资料；你本人、你指导的学生、学校均证据不足。")
        brain, _, _ = self.brain(model, ManySourcesGateway())
        response = brain.respond(BrainRequest(message="我在科创比赛中得过奖吗？"), "u")
        prompt = model.prompts[0][0]
        titles = [source.get("title", "") for source in response.sources]

        self.assertLessEqual(len(response.sources), 5)
        self.assertLessEqual(prompt.count('"snippet"'), 5)
        self.assertEqual(len(titles), len(set(titles)))
        self.assertFalse(any(re.fullmatch(r"\d+", title) for title in titles))
        self.assertNotIn("source", [title.lower() for title in titles])
        self.assertFalse(any(title.lower().startswith("attachment-") for title in titles))
        self.assertNotRegex(json.dumps(response.sources, ensure_ascii=False), r"/Users/|/Volumes/|file://")
        self.assertIn("你本人", response.answer)
        self.assertIn("你指导的学生", response.answer)
        self.assertIn("学校", response.answer)

    def test_deterministic_current_school_bypasses_model_and_historical_field(self):
        model = Model("不应调用")
        brain, _, _ = self.brain(model)
        response = brain.respond(BrainRequest(message="我现在在哪个学校工作？"), "u")
        self.assertEqual(response.answer, "你现在在新华门小学工作。")
        self.assertEqual(model.calls, 0)

    def test_content_planning_forbids_unrequested_action_promises(self):
        class GuardModel(Model):
            def complete(self, prompt, messages, request_id):
                self.calls += 1; self.prompts.append((prompt, messages))
                text = "不包含执行承诺" if "不得主动承诺或提及小可" in prompt else "小可可帮你执行"
                return type("Result", (), {"text": text, "model": "test", "fallback": False})()
        brain, _, _ = self.brain(GuardModel())
        response = brain.respond(BrainRequest(message="我最近有什么值得写的内容吗？我想发个公众号。"), "u")
        self.assertNotIn("小可", response.answer)


if __name__ == "__main__": unittest.main()
