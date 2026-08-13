from __future__ import annotations

import ipaddress
from typing import Any
from urllib.parse import urlparse


REASON_LABELS = {
    "low_relevance": "低相关未通知",
    "low_stars": "未达到通知优先级",
    "onboarding_history": "onboarding 历史",
    "whitelist_rejected": "白名单/范围拒绝",
    "partial_missing_attachment": "缺附件",
    "deadline_expired": "已过截止时间",
    "notification_queued": "等待发送",
    "notification_failed": "发送未完成",
    "new_collected": "新收录待判断",
}

PROFILE_FIELDS = {
    "current_teaching_subjects": "当前任教学科",
    "current_service_audiences": "当前服务对象",
    "current_role": "当前岗位",
    "preferred_name": "preferred_name",
}

ACTION_MAP = {
    "阅读": ("read", "阅读"),
    "转发学校": ("share_school", "转发学校"),
    "自己报名": ("apply_self", "自己报名"),
    "推荐学生": ("recommend_students", "推荐学生"),
    "等待更多信息": ("wait_for_information", "等待更多信息"),
    "忽略": ("ignore", "忽略"),
}


def safe_public_url(value: Any) -> str | None:
    text = str(value or "").strip()
    parsed = urlparse(text)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return None
    host = parsed.hostname.lower()
    if host == "localhost" or host.endswith(".local"):
        return None
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return text
    return None if not address.is_global else text


def _eligibility(value: Any) -> str:
    return {"yes": "eligible", "possible": "possible", "no": "ineligible"}.get(
        str(value or "").lower(), "unknown"
    )


def _action(value: Any) -> dict[str, str]:
    text = str(value or "")
    for phrase, (code, label) in ACTION_MAP.items():
        if phrase in text:
            return {"code": code, "label": label}
    return {"code": "read", "label": "查看详情"}


def map_recommendation(raw: dict[str, Any]) -> dict[str, Any]:
    eligibility = raw.get("eligibility") if isinstance(raw.get("eligibility"), dict) else {}
    try:
        stars = max(1, min(5, int(raw.get("stars") or 1)))
    except (TypeError, ValueError):
        stars = 1
    return {
        "stars": stars,
        "title": str(raw.get("title") or "").strip(),
        "source": str(raw.get("source") or "来源未标注").strip(),
        "published_at": str(raw.get("published_at") or "").strip() or None,
        "deadline": str(raw.get("deadline") or "").strip() or None,
        "reason": str(raw.get("recommendation_reason") or "").strip(),
        "eligibility": {
            "self": _eligibility(eligibility.get("self")),
            "students": _eligibility(eligibility.get("students")),
            "school": _eligibility(eligibility.get("school")),
        },
        "action": _action(raw.get("recommended_action")),
        "open_url": safe_public_url(raw.get("safe_open_url")),
    }


def map_no_notification(raw: dict[str, Any]) -> dict[str, Any]:
    recent = raw.get("recent_summary") if isinstance(raw.get("recent_summary"), dict) else {}
    categories = []
    for reason in raw.get("no_notification_reasons") or []:
        if not isinstance(reason, dict):
            continue
        code = str(reason.get("reason") or "")
        safe_code = code if code in REASON_LABELS else "other"
        try:
            count = max(0, int(reason.get("count") or 0))
        except (TypeError, ValueError):
            count = 0
        categories.append({
            "code": safe_code,
            "label": REASON_LABELS.get(safe_code, "其他未通知原因"),
            "count": count,
        })
    true_new = max(0, int(recent.get("true_new") or 0))
    summary = (
        "最近不是系统没工作，而是没有出现达到主动通知门槛的新事项。"
        if true_new == 0
        else "最近有新的信息进入乐知，但部分事项没有达到主动通知门槛。"
    )
    return {
        "status": "available",
        "period_days": max(1, int(recent.get("days") or 7)),
        "summary": summary,
        "true_new": true_new,
        "categories": categories,
    }


def map_profile(public: dict[str, Any], status: dict[str, Any]) -> dict[str, Any]:
    fields = public.get("fields") if isinstance(public.get("fields"), dict) else {}
    pending = status.get("needs_confirmation") if isinstance(status.get("needs_confirmation"), list) else []
    safe_fields = []
    for key, label in PROFILE_FIELDS.items():
        raw = fields.get(key) if isinstance(fields.get(key), dict) else {}
        state = "needs_confirmation" if key in pending else str(raw.get("status") or "unknown")
        safe_fields.append({"key": key, "label": label, "value": raw.get("value"), "state": state})
    count = len(pending)
    return {
        "status": "available",
        "needs_confirmation_count": count,
        "message": f"为了让推荐更准确，还有 {count} 项资料需要确认。" if count else "",
        "fields": safe_fields,
    }
