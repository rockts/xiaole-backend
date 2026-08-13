import json
import unittest

from xiaole_home.mappers import (
    map_no_notification,
    map_profile,
    map_recommendation,
    safe_public_url,
)


class MapperTests(unittest.TestCase):
    def test_recommendation_is_whitelisted_and_normalized(self):
        raw = {
            "item_id": "internal-1",
            "title": "未来智造家",
            "source": "中国科协",
            "published_at": "2026-08-01",
            "stars": 5,
            "deadline": "2026-10-20",
            "eligibility": {"self": "no", "students": "yes", "school": "possible"},
            "recommendation_reason": "与科技教育方向匹配",
            "recommended_action": "推荐学生",
            "safe_open_url": "https://example.gov.cn/notice",
            "manifest": {"path": "/private/vault"},
            "debug": "secret",
        }

        value = map_recommendation(raw)

        self.assertEqual(
            {
                "stars", "title", "source", "published_at", "deadline",
                "reason", "eligibility", "action", "open_url",
            },
            set(value),
        )
        self.assertEqual("eligible", value["eligibility"]["students"])
        self.assertEqual("ineligible", value["eligibility"]["self"])
        self.assertEqual("recommend_students", value["action"]["code"])
        self.assertNotIn("internal-1", json.dumps(value, ensure_ascii=False))

    def test_private_or_local_urls_are_removed(self):
        for url in (
            "http://127.0.0.1:8765/x",
            "http://localhost/x",
            "http://192.168.88.119/x",
            "http://10.0.0.2/x",
            "http://172.16.1.2/x",
            "file:///private/tmp/x",
        ):
            self.assertIsNone(safe_public_url(url), url)
        self.assertEqual("https://example.gov.cn/a", safe_public_url("https://example.gov.cn/a"))

    def test_notification_reasons_use_fixed_labels_and_hide_unknown_codes(self):
        value = map_no_notification({
            "recent_summary": {"days": 7, "true_new": 1},
            "no_notification_reasons": [
                {"reason": "low_relevance", "count": 2},
                {"reason": "raw_internal_error", "count": 3},
            ],
        })
        self.assertEqual("低相关未通知", value["categories"][0]["label"])
        self.assertEqual("other", value["categories"][1]["code"])
        self.assertNotIn("raw_internal_error", json.dumps(value, ensure_ascii=False))

    def test_profile_exposes_only_four_allowed_fields(self):
        public = {"fields": {
            "current_teaching_subjects": {"value": ["信息科技"], "status": "confirmed"},
            "current_service_audiences": {"value": ["学生"], "status": "confirmed"},
            "current_role": {"value": "教师", "status": "confirmed"},
            "preferred_name": {"value": "高老师", "status": "confirmed"},
            "current_school": {"value": "不应返回", "status": "confirmed"},
        }}
        status = {"needs_confirmation": ["current_teaching_subjects", "current_school"]}

        value = map_profile(public, status)

        self.assertEqual(2, value["needs_confirmation_count"])
        self.assertEqual(
            {"current_teaching_subjects", "current_service_audiences", "current_role", "preferred_name"},
            {field["key"] for field in value["fields"]},
        )
        self.assertNotIn("current_school", json.dumps(value, ensure_ascii=False))


if __name__ == "__main__":
    unittest.main()
