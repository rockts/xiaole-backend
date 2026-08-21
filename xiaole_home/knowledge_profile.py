from __future__ import annotations

from typing import Any


PROFILE_FIELDS = (
    ("current_school", "当前学校", {"confirmed"}),
    ("preferred_name", "我是谁", {"confirmed", "current", "confirmed_current"}),
    ("current_role", "当前工作 / 职业", {"confirmed", "current", "confirmed_current"}),
    ("current_teaching_subjects", "教育方向", {"confirmed", "current", "confirmed_current", "needs_confirmation"}),
    ("current_service_audiences", "专业角色", {"confirmed", "current", "confirmed_current", "needs_confirmation", "historical"}),
    ("current_grade_levels", "当前服务年级", {"confirmed", "current", "confirmed_current", "needs_confirmation"}),
    ("historical_school", "历史学校", {"historical"}),
    ("historical_schools", "历史学校", {"historical"}),
)


def map_knowledge_profile(profile: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    fields = profile.get("fields") if isinstance(profile, dict) else None
    if not isinstance(fields, dict):
        return {"fields": []}

    safe_fields = []
    for key, label, allowed_states in PROFILE_FIELDS:
        raw = fields.get(key)
        if not isinstance(raw, dict):
            continue
        state = str(raw.get("status") or "")
        value = raw.get("value")
        if raw.get("subject") != "current_user" or state not in allowed_states or value in (None, "", []):
            continue
        safe_fields.append({"key": key, "label": label, "value": value, "state": state})
    return {"fields": safe_fields}
