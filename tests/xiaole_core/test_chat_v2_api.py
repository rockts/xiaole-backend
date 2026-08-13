import unittest
import json
import logging
from datetime import timedelta

from fastapi import FastAPI
from fastapi.testclient import TestClient

from auth import ADMIN_USERNAME, create_access_token
from routers.chat_v2 import get_brain_core, router
from xiaole_core.schemas import BrainResponse, Diagnostics, Intent


class FakeBrain:
    def __init__(self): self.user=None
    def respond(self, request, user):
        self.user=user
        return BrainResponse(request_id="r",conversation_id=request.conversation_id or "c",intent=Intent.CONVERSATION,answer="ok",diagnostics=Diagnostics())


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.brain=FakeBrain(); app=FastAPI(); app.include_router(router,prefix="/api")
        app.dependency_overrides[get_brain_core]=lambda:self.brain
        self.client=TestClient(app)

    def test_no_or_invalid_jwt_is_401(self):
        self.assertEqual(self.client.post("/api/v2/chat",json={"message":"你好"}).status_code,401)
        self.assertEqual(self.client.post("/api/v2/chat",headers={"Authorization":"Bearer bad"},json={"message":"你好"}).status_code,401)

    def test_existing_valid_jwt_supplies_current_user(self):
        token=create_access_token({"sub":ADMIN_USERNAME},timedelta(minutes=5))
        response=self.client.post("/api/v2/chat",headers={"Authorization":f"Bearer {token}"},json={"message":"你好"})
        self.assertEqual(response.status_code,200)
        self.assertEqual(self.brain.user,ADMIN_USERNAME)
        self.assertEqual(response.json()["intent"],"conversation")

    def test_unexpected_core_error_does_not_leak_detail(self):
        class BrokenBrain:
            def respond(self, *_): raise RuntimeError("secret prompt and token")
        self.client.app.dependency_overrides[get_brain_core]=lambda:BrokenBrain()
        token=create_access_token({"sub":ADMIN_USERNAME},timedelta(minutes=5))
        response=self.client.post("/api/v2/chat",headers={"Authorization":f"Bearer {token}"},json={"message":"你好"})
        self.assertEqual(response.status_code,500)
        self.assertNotIn("secret",response.text)

    def test_core_error_emits_one_validation_safe_fallback_event(self):
        records = []
        class Handler(logging.Handler):
            def emit(self, record): records.append(record.getMessage())
        handler = Handler(); logger = logging.getLogger("xiaole_ai"); logger.addHandler(handler); logger.setLevel(logging.INFO)
        try:
            class BrokenBrain:
                def respond(self, *_): raise RuntimeError("secret prompt token https://private")
            self.client.app.dependency_overrides[get_brain_core]=lambda:BrokenBrain()
            token=create_access_token({"sub":ADMIN_USERNAME},timedelta(minutes=5))
            self.client.post("/api/v2/chat",headers={"Authorization":f"Bearer {token}"},json={"message":"private question"})
        finally:
            logger.removeHandler(handler)
        events = [json.loads(line) for line in records if line.startswith('{"event":"core2_safe_diagnostics"')]
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["scope"], "validation_safe_failure")
        rendered = json.dumps(events, ensure_ascii=False)
        for marker in ("secret", "prompt", "token", "https://", "private question"):
            self.assertNotIn(marker, rendered)


if __name__ == "__main__": unittest.main()
