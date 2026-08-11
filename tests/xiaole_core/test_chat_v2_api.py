import unittest
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


if __name__ == "__main__": unittest.main()
