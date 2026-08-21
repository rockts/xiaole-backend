#!/usr/bin/env python3
from __future__ import annotations

import json
import logging
from pathlib import Path
import sys

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from auth import get_current_user
from routers.chat_v2 import get_brain_core, router
from xiaole_core.brain import BrainCore
from xiaole_core.schemas import ProfileGatewayResponse


SELF_PROFILE_QUESTIONS = (
    "你认识我吗？", "你知道我是谁吗？", "我是谁？", "介绍一下我",
    "你对我了解多少？", "说说你知道的我", "你记得我什么？",
    "我对你来说是什么样的人？",
)
FORBIDDEN_CURRENT_MARKERS = (
    "烟铺小学", "家庭敏感成员", "子女敏感学校", "外貌敏感描述", "隐私小区",
    "饮食敏感偏好", "旧课程表敏感内容", "科学", "数学", "六年级",
)


def _profile():
    return {"fields": {
        "display_name": {"value": "高鹏", "status": "confirmed", "subject": "current_user"},
        "current_school": {"value": "新华门小学", "status": "confirmed", "subject": "current_user"},
        "occupation": {"value": "中小学教师", "status": "confirmed", "subject": "current_user"},
        "education_focus": {"value": ["科技教育"], "status": "confirmed", "subject": "current_user"},
        "stable_interests": {"value": ["AI", "编程", "自动化"], "status": "confirmed", "subject": "current_user"},
        "long_term_projects": {"value": ["小乐", "乐知", "小可", "乐教库"], "status": "confirmed", "subject": "current_user"},
        "historical_school": {"value": ["烟铺小学"], "status": "historical", "subject": "current_user"},
        "current_teaching_subjects": {"value": ["科学", "数学"], "status": "needs_confirmation", "subject": "current_user"},
        "current_grade_levels": {"value": ["六年级"], "status": "needs_confirmation", "subject": "current_user"},
        "precise_address": {"value": "隐私小区", "status": "confirmed", "subject": "current_user"},
        "family_members": {"value": ["家庭敏感成员"], "status": "confirmed", "subject": "current_user"},
        "children_school": {"value": "子女敏感学校", "status": "confirmed", "subject": "current_user"},
        "children_appearance": {"value": "外貌敏感描述", "status": "confirmed", "subject": "current_user"},
        "food_preferences": {"value": ["饮食敏感偏好"], "status": "confirmed", "subject": "current_user"},
        "old_schedule": {"value": "旧课程表敏感内容", "status": "historical", "subject": "current_user"},
    }}


class LocalContext:
    def __init__(self):
        self.rows = [{"role": "assistant", "content": "共享会话Legacy家庭住址饮食旧课程表"}]

    def resolve(self, _user, conversation_id, _message):
        return conversation_id or "local-self-profile"

    def history(self, _user, _conversation_id):
        return list(self.rows[-12:])

    def append_exchange(self, _user, _conversation_id, message, answer):
        self.rows.extend(({"role": "user", "content": message}, {"role": "assistant", "content": answer}))


class ForbiddenModel:
    def __init__(self): self.calls = 0
    def complete(self, *_):
        self.calls += 1
        raise AssertionError("local self-profile E2E called the model")
    classify = complete


class LocalGateway:
    def __init__(self, available=True):
        self.available, self.profile_calls, self.memory_calls = available, 0, 0

    def profile(self, _request_id):
        self.profile_calls += 1
        if not self.available:
            return ProfileGatewayResponse(result="unavailable", reason_codes=["profile_timeout"])
        return ProfileGatewayResponse(payload=_profile(), result="success", reason_codes=["profile_request_success"])

    def ask(self, *_):
        self.memory_calls += 1
        raise AssertionError("local self-profile E2E called Memory")


class ForbiddenAction:
    def __init__(self): self.calls = 0
    def execute(self, *_):
        self.calls += 1
        raise AssertionError("local self-profile E2E called Action")


class Capture(logging.Handler):
    def __init__(self):
        super().__init__(); self.events = []
    def emit(self, record):
        message = record.getMessage()
        if message.startswith('{"event":"core2_safe_diagnostics"'):
            self.events.append(json.loads(message))


def run_acceptance():
    failures = []
    model, gateway, action = ForbiddenModel(), LocalGateway(), ForbiddenAction()
    brain = BrainCore(LocalContext(), model, gateway, action, read_gateway=gateway)
    app = FastAPI(); app.include_router(router, prefix="/api")
    app.dependency_overrides[get_current_user] = lambda: "local-user"
    app.dependency_overrides[get_brain_core] = lambda: brain
    client = TestClient(app)
    capture = Capture(); logger = logging.getLogger("xiaole_ai"); logger.addHandler(capture); logger.setLevel(logging.INFO)
    try:
        for question in SELF_PROFILE_QUESTIONS:
            response = client.post("/api/v2/chat", json={"message": question})
            body = response.json(); answer = body.get("answer", ""); diagnostics = body.get("diagnostics", {})
            if response.status_code != 200: failures.append(f"self_profile_http:{question}")
            if "新华门小学" not in answer: failures.append(f"current_school:{question}")
            if any(marker in answer for marker in FORBIDDEN_CURRENT_MARKERS): failures.append(f"privacy:{question}")
            if "还没有确认" not in answer: failures.append(f"needs_confirmation:{question}")
            if "所有这些信息都来自" in answer: failures.append(f"provenance:{question}")
            if diagnostics.get("renderer") != "deterministic" or diagnostics.get("model"):
                failures.append(f"renderer:{question}")

        history_response = client.post("/api/v2/chat", json={"message": "我以前在哪些学校工作过？"})
        history_answer = history_response.json().get("answer", "")
        history_passed = (
            history_response.status_code == 200 and "烟铺小学" in history_answer
            and "历史" in history_answer and "新华门小学" not in history_answer
        )
        if not history_passed: failures.append("employment_history")

        unavailable_gateway = LocalGateway(available=False)
        unavailable_brain = BrainCore(LocalContext(), model, unavailable_gateway, action, read_gateway=unavailable_gateway)
        app.dependency_overrides[get_brain_core] = lambda: unavailable_brain
        unavailable_response = client.post("/api/v2/chat", json={"message": "你认识我吗？"})
        unavailable_answer = unavailable_response.json().get("answer", "")
        profile_failure_passed = (
            unavailable_response.status_code == 200 and "暂时无法读取" in unavailable_answer
            and "烟铺小学" not in unavailable_answer
        )
        if not profile_failure_passed: failures.append("profile_failure")
    finally:
        logger.removeHandler(capture)

    for event in capture.events:
        if event.get("scope") in ("self_profile", "employment_history"):
            if event.get("model_called") or event.get("renderer") != "deterministic": failures.append("diagnostics_model")
            serialized = json.dumps(event, ensure_ascii=False)
            if any(marker in serialized for marker in ("新华门小学", "烟铺小学", "家庭敏感成员")):
                failures.append("diagnostics_value_leak")

    return {
        "passed": not failures,
        "failures": failures,
        "self_profile_questions": len(SELF_PROFILE_QUESTIONS),
        "employment_history_passed": history_passed,
        "profile_failure_passed": profile_failure_passed,
        "model_calls": model.calls,
        "memory_calls": gateway.memory_calls + unavailable_gateway.memory_calls,
        "action_calls": action.calls,
        "diagnostic_events": len(capture.events),
    }


if __name__ == "__main__":
    report = run_acceptance()
    print(f"Self Profile Grounding Local: {'PASS' if report['passed'] else 'FAIL'}")
    if report["failures"]:
        print("Failed checks: " + ", ".join(report["failures"]))
    raise SystemExit(0 if report["passed"] else 1)
