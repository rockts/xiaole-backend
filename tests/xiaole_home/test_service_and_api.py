import importlib
import sys
import time
import types
import unittest
from datetime import timedelta
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from auth import ADMIN_USERNAME, create_access_token
from routers.home_v2 import get_home_service, router
from xiaole_home.cache import HomeCache
from xiaole_home.gateways.action_readiness import Readiness
from xiaole_home.service import HomeService


INTELLIGENCE = {"today":{"last_scan":"2026-08-13T09:30:00+08:00","next_scan":"2026-08-13T16:30:00+08:00","sources_healthy":5,"sources_unhealthy":2,"new_discovered":1,"relevant":2,"notified":0},"recent_summary":{"days":7,"true_new":1},"recommended_items":[{"title":"未来智造家","source":"中国科协","stars":5,"recommendation_reason":"适合科技教育","recommended_action":"推荐学生","eligibility":{"students":"yes"}}],"no_notification_reasons":[{"reason":"low_relevance","count":1}],"system_health":{"memory_service":"healthy","sources":"degraded","intelligence_scheduler":"healthy"}}

class Lezhi:
    def intelligence(self): return INTELLIGENCE
    def knowledge(self): return {"schema_version":1,"quality_warnings":[]}
    def profile(self): return {"fields":{}}
    def profile_status(self): return {"needs_confirmation":["current_teaching_subjects"]}

class BrokenLezhi:
    def __getattr__(self, _): return lambda: (_ for _ in ()).throw(TimeoutError())

class Action:
    def check(self): return Readiness("healthy","行动服务正常。")

class Conversations:
    def recent(self, user): return [{"session_id":"s1","title":"最近对话","updated_at":"2026-08-13","user_id":user,"debug":"x"}]

class ServiceTests(unittest.TestCase):
    def test_maps_complete_home_and_safe_conversations(self):
        value=HomeService(Lezhi(),Action(),Conversations(),HomeCache()).get("admin")
        self.assertEqual(1,value["schema_version"]); self.assertEqual("未来智造家",value["recommendations"]["items"][0]["title"])
        self.assertEqual({"session_id","title","updated_at"},set(value["recent_conversations"][0]))
        self.assertEqual("degraded",value["systems"]["memory"]["status"])

    def test_dependency_failure_returns_degraded_model(self):
        value=HomeService(BrokenLezhi(),Action(),Conversations(),HomeCache()).get("admin")
        self.assertEqual("unavailable",value["systems"]["memory"]["status"])
        self.assertEqual("unavailable",value["today"]["status"])
        self.assertTrue(value["degradations"])

    def test_stale_cache_is_returned_and_memory_cannot_stay_healthy(self):
        now=[1000.0]; cache=HomeCache(clock=lambda:now[0]); service=HomeService(Lezhi(),Action(),Conversations(),cache)
        service.get("admin"); now[0]+=61; service.lezhi=BrokenLezhi()
        value=service.get("admin")
        self.assertEqual("stale",value["cache"]["status"]); self.assertEqual("degraded",value["systems"]["memory"]["status"])

    def test_total_budget_is_not_multiplied_by_dependency_count(self):
        class Slow:
            def __getattr__(self,_): return lambda:(time.sleep(.2) or {})
        started=time.monotonic(); HomeService(Slow(),Action(),Conversations(),HomeCache(),budget=.05).get("admin")
        self.assertLess(time.monotonic()-started,.16)

class ApiTests(unittest.TestCase):
    def setUp(self):
        app=FastAPI(); app.include_router(router,prefix="/api"); app.dependency_overrides[get_home_service]=lambda:HomeService(Lezhi(),Action(),Conversations(),HomeCache()); self.client=TestClient(app)
    def test_requires_existing_jwt(self): self.assertEqual(401,self.client.get("/api/v2/home").status_code)
    def test_valid_jwt_returns_home(self):
        token=create_access_token({"sub":ADMIN_USERNAME},timedelta(minutes=5)); response=self.client.get("/api/v2/home",headers={"Authorization":f"Bearer {token}"})
        self.assertEqual(200,response.status_code); self.assertEqual(1,response.json()["schema_version"])


class DependencyConstructionTests(unittest.TestCase):
    def test_home_dependencies_import_and_service_construction(self):
        provider = types.ModuleType("dependencies")
        provider.get_xiaole_agent = lambda: None
        agent = types.ModuleType("agent")

        sys.modules.pop("xiaole_home.dependencies", None)
        with patch.dict(sys.modules, {"dependencies": provider, "agent": agent}):
            home_dependencies = importlib.import_module("xiaole_home.dependencies")
            home_dependencies.build_home_service.cache_clear()
            with (
                patch.object(home_dependencies, "LezhiHomeGateway"),
                patch.object(home_dependencies, "ActionReadinessGateway"),
                patch.object(home_dependencies, "HomeCache"),
            ):
                service = get_home_service()

            self.assertIsInstance(service, HomeService)
            home_dependencies.build_home_service.cache_clear()

if __name__ == "__main__": unittest.main()
