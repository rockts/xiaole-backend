import unittest

from xiaole_core.self_profile import (
    render_employment_history,
    render_profile_unavailable,
    render_self_profile,
)


def governed_profile():
    return {
        "fields": {
            "display_name": {"value": "高鹏", "status": "confirmed", "subject": "current_user"},
            "region": {"value": "甘肃天水", "status": "confirmed", "subject": "current_user"},
            "current_school": {"value": "新华门小学", "status": "confirmed", "subject": "current_user"},
            "occupation": {"value": "中小学教师", "status": "confirmed", "subject": "current_user"},
            "professional_roles": {"value": ["科技教育实践者"], "status": "confirmed", "subject": "current_user"},
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
            "legacy_fact": {"value": "Legacy敏感内容", "status": "confirmed", "subject": "current_user"},
            "other_person": {"value": "其他主体敏感内容", "status": "confirmed", "subject": "family_member"},
        }
    }


class SelfProfilePolicyTests(unittest.TestCase):
    def test_current_profile_minimizes_privacy_and_never_promotes_unconfirmed_values(self):
        result = render_self_profile(governed_profile())

        for expected in ("高鹏", "新华门小学", "中小学教师", "AI", "小乐"):
            self.assertIn(expected, result.answer)
        self.assertIn("还没有确认", result.answer)
        for forbidden in (
            "烟铺小学", "科学", "数学", "六年级", "隐私小区", "家庭敏感成员",
            "子女敏感学校", "外貌敏感描述", "饮食敏感偏好", "旧课程表敏感内容",
            "Legacy敏感内容", "其他主体敏感内容",
        ):
            self.assertNotIn(forbidden, result.answer)
        self.assertEqual(result.admitted_sources, ("confirmed_profile", "needs_confirmation"))
        self.assertEqual(result.provenance_categories, ("user_confirmed_profile", "needs_confirmation"))

    def test_history_uses_only_historical_profile_and_labels_it_as_past(self):
        result = render_employment_history(governed_profile())

        self.assertIn("烟铺小学", result.answer)
        self.assertIn("曾经", result.answer)
        self.assertNotIn("新华门小学", result.answer)
        self.assertEqual(result.admitted_sources, ("historical_profile",))
        self.assertEqual(result.provenance_categories, ("historical_profile",))

    def test_provenance_is_code_owned_and_never_claims_everything_was_confirmed(self):
        result = render_self_profile(governed_profile())

        self.assertIn("根据你已确认的个人资料", result.answer)
        self.assertNotIn("所有这些信息都来自您亲自确认过的乐知资料", result.answer)

    def test_malformed_or_empty_profile_fails_closed(self):
        for profile in ({}, {"fields": []}, {"fields": {}}):
            with self.subTest(profile=profile):
                result = render_self_profile(profile)
                self.assertIn("无法安全确认", result.answer)
                self.assertEqual(result.admitted_sources, ())
                self.assertEqual(result.provenance_categories, ())

        unavailable = render_profile_unavailable("self_profile")
        self.assertIn("暂时无法读取", unavailable.answer)
        self.assertEqual(unavailable.admitted_sources, ())


if __name__ == "__main__":
    unittest.main()
