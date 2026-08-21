import json
import unittest
from datetime import timedelta

from fastapi import FastAPI
from fastapi.testclient import TestClient

from auth import ADMIN_USERNAME, create_access_token
from routers.knowledge_profile import get_knowledge_profile_gateway, router
from xiaole_home.knowledge_profile import map_knowledge_profile


PROFILE = {
    "fields": {
        "current_school": {
            "value": "新华门小学",
            "status": "confirmed",
            "subject": "current_user",
            "path": "/private/profile.json",
            "confidence": 0.99,
            "debug": "hidden",
        },
        "historical_school": {
            "value": ["烟铺小学"],
            "status": "historical",
            "subject": "current_user",
        },
        "current_teaching_subjects": {
            "value": ["信息科技"],
            "status": "needs_confirmation",
            "subject": "current_user",
        },
        "preferred_name": {
            "value": "高老师",
            "status": "current",
            "subject": "current_user",
        },
        "secret": {
            "value": "must-not-render",
            "status": "confirmed",
            "subject": "current_user",
        },
    },
    "path": "/private/profile.json",
    "debug": "hidden",
}


class KnowledgeProfileMapperTests(unittest.TestCase):
    def test_projects_current_historical_and_pending_without_sensitive_metadata(self):
        value = map_knowledge_profile(PROFILE)

        by_key = {field["key"]: field for field in value["fields"]}
        self.assertEqual("新华门小学", by_key["current_school"]["value"])
        self.assertEqual("confirmed", by_key["current_school"]["state"])
        self.assertEqual("current", by_key["preferred_name"]["state"])
        self.assertEqual("historical", by_key["historical_school"]["state"])
        self.assertEqual("needs_confirmation", by_key["current_teaching_subjects"]["state"])
        self.assertEqual({"key", "label", "value", "state"}, set(by_key["current_school"]))
        serialized = json.dumps(value, ensure_ascii=False)
        self.assertNotIn("must-not-render", serialized)
        for field in value["fields"]:
            self.assertTrue({"path", "confidence", "subject", "debug"}.isdisjoint(field))

    def test_historical_school_never_replaces_current_school(self):
        value = map_knowledge_profile({
            "fields": {
                "current_school": {
                    "value": "新华门小学",
                    "status": "confirmed",
                    "subject": "current_user",
                },
                "historical_school": {
                    "value": ["烟铺小学", "实验小学"],
                    "status": "historical",
                    "subject": "current_user",
                },
            }
        })

        by_key = {field["key"]: field for field in value["fields"]}
        self.assertEqual("新华门小学", by_key["current_school"]["value"])
        self.assertEqual(["烟铺小学", "实验小学"], by_key["historical_school"]["value"])

    def test_rejects_wrong_subject_unknown_state_and_empty_values(self):
        value = map_knowledge_profile({
            "fields": {
                "current_school": {"value": "错误学校", "status": "confirmed", "subject": "other"},
                "current_role": {"value": "猜测岗位", "status": "candidate", "subject": "current_user"},
                "preferred_name": {"value": "", "status": "confirmed", "subject": "current_user"},
            }
        })
        self.assertEqual([], value["fields"])


class Gateway:
    def profile(self):
        return PROFILE


class BrokenGateway:
    def profile(self):
        raise TimeoutError("profile unavailable")


class KnowledgeProfileApiTests(unittest.TestCase):
    def setUp(self):
        self.app = FastAPI()
        self.app.include_router(router, prefix="/api")
        self.client = TestClient(self.app)
        self.token = create_access_token({"sub": ADMIN_USERNAME}, timedelta(minutes=5))

    def test_requires_existing_jwt(self):
        self.app.dependency_overrides[get_knowledge_profile_gateway] = Gateway
        self.assertEqual(401, self.client.get("/api/v2/knowledge/profile").status_code)

    def test_returns_safe_profile_for_valid_jwt(self):
        self.app.dependency_overrides[get_knowledge_profile_gateway] = Gateway
        response = self.client.get(
            "/api/v2/knowledge/profile",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual("新华门小学", response.json()["fields"][0]["value"])

    def test_profile_failure_is_explicitly_unavailable(self):
        self.app.dependency_overrides[get_knowledge_profile_gateway] = BrokenGateway
        response = self.client.get(
            "/api/v2/knowledge/profile",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(503, response.status_code)
        self.assertEqual("Knowledge Profile unavailable", response.json()["detail"])


if __name__ == "__main__":
    unittest.main()
