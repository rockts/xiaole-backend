from __future__ import annotations

import time
import uuid
import json
import re

from .errors import ActionUnavailable, MemoryUnavailable, ModelUnavailable
from .intent import IntentRouter, is_current_employment_query
from .schemas import ActionCommand, BrainRequest, BrainResponse, Diagnostics, Intent, ProfileGatewayResponse


class BrainCore:
    def __init__(self, context, models, memory_gateway, action_gateway, intent_router=None, persona="你是小乐。", read_gateway=None):
        self.context, self.models = context, models
        self.memory_gateway, self.action_gateway = memory_gateway, action_gateway
        self.intent_router = intent_router or IntentRouter(getattr(models, "classify", None))
        self.persona = persona
        self.read_gateway = read_gateway or memory_gateway

    def respond(self, request: BrainRequest, user_id: str) -> BrainResponse:
        started, request_id = time.monotonic(), str(uuid.uuid4())
        conversation_id = self.context.resolve(user_id, request.conversation_id, request.message)
        history = self.context.history(user_id, conversation_id)
        decision = self.intent_router.classify(request.message, history, request_id)
        answer, sources, action = "", [], None
        model, fallback, gateway, gateways = "", False, None, []
        if decision.intent in (Intent.KNOWLEDGE, Intent.STATUS, Intent.PLANNING):
            answer, sources, model, fallback, gateways, profile_diagnostics = self._read_answer(decision.intent, request.message, history, request_id)
            gateway = gateways[0] if len(gateways) == 1 else None
        elif decision.intent == Intent.ACTION:
            gateway = "action"
            gateways = ["action"]
            try:
                action = self.action_gateway.execute(ActionCommand.notification(conversation_id, request_id), request_id)
                answer = action.summary
            except ActionUnavailable:
                answer = "小可执行系统暂时不可用，测试通知没有确认成功。"
        else:
            try:
                result = self.models.complete(self.persona, [*history, {"role":"user","content":request.message}], request_id)
                answer, model, fallback = result.text, result.model, result.fallback
            except ModelUnavailable:
                answer = "模型服务暂时不可用，请稍后再试。"
        self.context.append_exchange(user_id, conversation_id, request.message, answer)
        profile_diagnostics = locals().get("profile_diagnostics", {})
        return BrainResponse(
            request_id=request_id, conversation_id=conversation_id, intent=decision.intent, answer=answer,
            sources=sources, action=action,
            diagnostics=Diagnostics(model=model, gateway_used=gateway, gateways_used=gateways, latency_ms=max(0,int((time.monotonic()-started)*1000)), fallback=fallback, **profile_diagnostics),
        )

    def _read_answer(self, intent, message, history, request_id):
        facts, sources, used, unavailable = {}, [], [], []
        profile_diagnostics = {}
        current_school = is_current_employment_query(message)
        personal_fact = current_school or any(x in message for x in ("得过奖", "获过奖", "学校", "职业", "身份", "角色"))
        names = {Intent.STATUS: ("status",), Intent.PLANNING: ("profile", "knowledge", "status", "memory"), Intent.KNOWLEDGE: (("profile", "memory") if personal_fact else ("memory",))}[intent]
        if current_school: names = ("profile",)
        for name in names:
            try:
                value = self.read_gateway.ask(message, history, request_id) if name == "memory" else getattr(self.read_gateway, name)(request_id)
                if name == "profile" and current_school:
                    profile_diagnostics = self._profile_diagnostics(value)
                    if isinstance(value, ProfileGatewayResponse):
                        if value.result != "success":
                            unavailable.append(name)
                            continue
                        value = value.payload
                facts[name] = self._project(name, value, intent, current_school=current_school); used.append(name)
                if name == "status" and isinstance(value, dict) and (value.get("recommended_items") or value.get("recommended_today")): used.append("recommendation")
                if name == "memory":
                    sources = self._display_sources(value.sources)
                    facts[name] = {"confidence": value.confidence, "evidence_snippets": self._memory_snippets(value)}
            except (MemoryUnavailable, AttributeError): unavailable.append(name)
        if intent == Intent.KNOWLEDGE and not personal_fact:
            if "memory" in facts:
                return self._safe_text(getattr(value, "answer", ""), 4000) or "我目前没能读取到可用资料。", sources, "", False, used, profile_diagnostics
            return "我目前没能读取到乐知资料，暂时无法确认相关信息。", [], "", False, used, profile_diagnostics
        if current_school:
            field = ((facts.get("profile") or {}).get("fields") or {}).get("current_school") or {}
            if field.get("status") == "confirmed" and field.get("subject") == "current_user" and field.get("value"):
                profile_diagnostics.update(profile_gateway_result="success", profile_current_school_state="ready", deterministic_profile_hit=True)
                profile_diagnostics["profile_reason_codes"] += ["current_school_ready", "deterministic_profile_hit"]
                return f"你现在在{field['value']}工作。", [], "", False, used, profile_diagnostics
            profile_diagnostics = self._current_school_miss(profile_diagnostics, facts)
        instruction = {
            Intent.STATUS: "根据今日扫描和推荐直接回答最应关注的事；说明是否扫描、新发布和无事项的原因，不要要求外部新闻。",
            Intent.PLANNING: "给出3个紧凑、有依据的公众号选题；每个包含 title/angle、why_now、source_basis、relation_to_user、suggested_next_step；资料不足要说明。不得主动承诺或提及小可执行动作，不得把 Action 或小可作为选题。",
            Intent.KNOWLEDGE: "回答个人事实，Profile confirmed 优先。获奖问题必须逐项列出三个主体：‘你本人’、‘你指导的学生’、‘学校’，并对每项说明已确认或证据不足；绝不得把存在获奖资料等同于你本人获奖。证据不足时以‘目前只能确认到……’开头。",
        }[intent]
        prompt = self.persona + "\n" + instruction + "\n只能使用下列已标注来源的事实，不得说‘乐知确认’，除非 memory 在 available_sources 中。\n" + json.dumps({"available_sources":used,"unavailable_sources":unavailable,"facts":facts}, ensure_ascii=False)
        try:
            result = self.models.complete(prompt, [{"role":"user","content":message}], request_id)
            answer = result.text
            if intent == Intent.KNOWLEDGE and any(x in message for x in ("得过奖", "获过奖")):
                missing = [label for label in ("你本人", "你指导的学生", "学校") if label not in answer]
                if missing:
                    answer = answer.rstrip() + "\n\n主体归因：\n- 你本人：目前证据不足。\n- 你指导的学生：目前证据不足。\n- 学校：目前证据不足。"
            return answer, sources, result.model, result.fallback, used, profile_diagnostics
        except ModelUnavailable:
            return "我目前没能完成回答；已读取到的资料不会被当作确认结论。", sources, "", False, used, profile_diagnostics

    @staticmethod
    def _profile_diagnostics(value):
        if isinstance(value, ProfileGatewayResponse):
            diagnostics = {
                "profile_gateway_called": True,
                "profile_gateway_result": value.result,
                "profile_current_school_state": "invalid",
                "deterministic_profile_hit": False,
                "profile_reason_codes": list(value.reason_codes),
            }
            if value.result == "success" and not isinstance(value.payload.get("fields"), dict):
                diagnostics["profile_gateway_result"] = "missing_fact"
                diagnostics["profile_reason_codes"].append("profile_fields_missing")
            return diagnostics
        return {
            "profile_gateway_called": True,
            "profile_gateway_result": "success",
            "profile_current_school_state": "invalid",
            "deterministic_profile_hit": False,
            "profile_reason_codes": ["profile_request_success"],
        }

    @staticmethod
    def _current_school_miss(diagnostics, facts):
        if not diagnostics:
            diagnostics = {"profile_gateway_called": True, "profile_gateway_result": "unavailable", "profile_current_school_state": "invalid", "deterministic_profile_hit": False, "profile_reason_codes": []}
        if diagnostics["profile_gateway_result"] != "success":
            if diagnostics["profile_gateway_result"] == "missing_fact":
                diagnostics["profile_current_school_state"] = "invalid"
            diagnostics["profile_reason_codes"].append("deterministic_profile_miss")
            return diagnostics
        profile = facts.get("profile") or {}
        if "fields" not in profile:
            state, reason = "invalid", "profile_fields_missing"
        else:
            fields = profile.get("fields") or {}
            if "current_school" not in fields:
                state, reason = "missing", "current_school_missing"
            else:
                field = fields.get("current_school") or {}
                if field.get("status") != "confirmed": state, reason = "not_confirmed", "current_school_status_not_confirmed"
                elif field.get("subject") != "current_user": state, reason = "wrong_subject", "current_school_subject_not_current_user"
                else: state, reason = "invalid", "current_school_value_missing"
        diagnostics.update(profile_gateway_result="missing_fact", profile_current_school_state=state)
        diagnostics["profile_reason_codes"] += [reason, "deterministic_profile_miss"]
        return diagnostics

    @classmethod
    def _project(cls, name, value, intent, current_school=False):
        if not isinstance(value, dict): return {}
        if name == "profile":
            allowed = ("current_school",) if current_school else (("education_focus", "stable_interests", "long_term_projects", "long_term_goals") if intent == Intent.PLANNING else ())
            fields = value.get("fields") if isinstance(value.get("fields"), dict) else {}
            if current_school and "current_school" not in fields and isinstance(value.get("current_school"), dict):
                fields = {"current_school": value["current_school"]}
            return {"fields": {key: cls._fact(fields[key]) for key in allowed if key in fields}}
        if name == "knowledge":
            recent = value.get("recent_additions") if isinstance(value.get("recent_additions"), dict) else {}
            return {"recent_additions": {key: recent.get(key) for key in ("recent_30d_raw", "recent_30d_cards", "recent_30d_intelligence") if key in recent}}
        if name == "status":
            today = value.get("today") if isinstance(value.get("today"), dict) else {}
            return {"today": {key: today.get(key) for key in ("last_scan", "next_scan", "new_discovered", "relevant") if key in today}, "recommendations": cls._recommendations(value)}
        return {}

    @staticmethod
    def _fact(value):
        if not isinstance(value, dict): return {}
        return {key: value.get(key) for key in ("value", "status", "subject") if key in value}

    @classmethod
    def _recommendations(cls, value):
        rows = value.get("recommended_items") or (value.get("recommended_today") or {}).get("items") or []
        result = []
        for row in rows[:5]:
            if not isinstance(row, dict): continue
            item = {key: cls._safe_text(row.get(key), 300) for key in ("title", "source", "published_at", "deadline", "recommendation_reason", "recommended_action") if row.get(key)}
            if item: result.append(item)
        return result

    @classmethod
    def _memory_snippets(cls, result):
        snippets = []
        summary = cls._safe_text(result.answer, 500)
        if summary: snippets.append({"snippet": summary})
        for source in cls._ranked_sources(result.sources)[:4]:
            raw = next((source.get(key) for key in ("snippet", "excerpt", "summary") if source.get(key)), "")
            title, snippet = cls._safe_text(source.get("title"), 160), cls._safe_text(raw, 500)
            if title or snippet: snippets.append({key:value for key,value in (("title",title),("snippet",snippet)) if value})
        return snippets

    @classmethod
    def _display_sources(cls, candidates):
        result, seen = [], set()
        for source in cls._ranked_sources(candidates):
            title = cls._safe_text(source.get("title"), 160)
            normalized = re.sub(r"\s+", " ", title).strip().casefold()
            if not title or re.fullmatch(r"\d+", normalized) or normalized == "source" or normalized.startswith("attachment-"):
                continue
            if "[redacted]" in title or normalized in seen:
                continue
            seen.add(normalized)
            item = {"title": title, "provenance": source.get("provenance", "memory")}
            blocked = {"path", "file_path", "open_url", "preview_url", "url", "token", "secret", "password", "authorization"}
            for key, value in source.items():
                if key in item or key in blocked or key in ("snippet", "excerpt", "summary"):
                    continue
                if isinstance(value, (str, int, float, bool)) and value is not None:
                    item[key] = cls._safe_text(value, 300) if isinstance(value, str) else value
            raw = next((source.get(key) for key in ("snippet", "excerpt", "summary") if source.get(key)), "")
            snippet = cls._safe_text(raw, 500)
            if snippet: item["snippet"] = snippet
            result.append(item)
            if len(result) == 5: break
        return result

    @classmethod
    def _ranked_sources(cls, candidates):
        keywords = ("科创", "比赛", "获奖", "学生", "学校", "指导")
        rows = [source for source in candidates if isinstance(source, dict)]
        return sorted(
            rows,
            key=lambda source: sum(word in (str(source.get("title") or "") + str(source.get("snippet") or source.get("excerpt") or source.get("summary") or "")) for word in keywords),
            reverse=True,
        )

    @staticmethod
    def _safe_text(value, limit):
        text = " ".join(str(value or "").split())
        text = re.sub(r"(?:/Users/|/Volumes/|file://)\S+", "[redacted]", text, flags=re.IGNORECASE)
        text = re.sub(r"(?i)\b(?:token|api[_ -]?key|password|authorization|database[_ -]?url|secret)\b\s*[:=]?\s*\S+", "[redacted]", text)
        return text[:limit]
