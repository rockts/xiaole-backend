from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SelfProfileResult:
    answer: str
    admitted_sources: tuple[str, ...] = ()
    provenance_categories: tuple[str, ...] = ()


_SELF_PROFILE_LABELS = (
    ("display_name", "你是{name}"),
    ("region", "来自{value}"),
    ("current_school", "目前在{value}工作"),
    ("occupation", "是一名{value}"),
    ("professional_roles", "你的专业角色包括{value}"),
    ("education_focus", "你长期关注{value}"),
    ("stable_interests", "也关注{value}"),
    ("long_term_projects", "并持续建设{value}"),
    ("long_term_goals", "长期目标包括{value}"),
)
_NEEDS_CONFIRMATION = ("current_teaching_subjects", "current_grade_levels")
_HISTORICAL_SCHOOLS = ("historical_school", "historical_schools")


def _fields(profile: dict) -> dict:
    if not isinstance(profile, dict) or not isinstance(profile.get("fields"), dict):
        return {}
    return profile["fields"]


def _allowed_fact(fields: dict, key: str, status: str) -> dict | None:
    fact = fields.get(key)
    if not isinstance(fact, dict):
        return None
    if fact.get("subject") != "current_user" or fact.get("status") != status:
        return None
    if fact.get("value") in (None, "", []):
        return None
    return fact


def _text(value) -> str:
    if isinstance(value, (list, tuple)):
        return "、".join(str(item) for item in value if item not in (None, ""))
    return str(value)


def render_profile_unavailable(scope: str) -> SelfProfileResult:
    subject = "历史任职资料" if scope == "employment_history" else "已确认的个人资料"
    return SelfProfileResult(f"我暂时无法读取{subject}，因此不会用旧资料或猜测来回答。")


def render_self_profile(profile: dict) -> SelfProfileResult:
    fields = _fields(profile)
    if not fields:
        return SelfProfileResult("我目前无法安全确认你的个人资料，因此不会用旧资料来猜。")

    clauses = []
    for key, template in _SELF_PROFILE_LABELS:
        fact = _allowed_fact(fields, key, "confirmed")
        if not fact:
            continue
        value = _text(fact["value"])
        clauses.append(template.format(name=value, value=value))

    if not clauses:
        return SelfProfileResult("我目前无法安全确认你的个人资料，因此不会用旧资料来猜。")

    unconfirmed = any(_allowed_fact(fields, key, "needs_confirmation") for key in _NEEDS_CONFIRMATION)
    answer = "认识。根据你已确认的个人资料，" + "；".join(clauses) + "。"
    admitted = ["confirmed_profile"]
    provenance = ["user_confirmed_profile"]
    if unconfirmed:
        answer += "不过，你当前具体任教的学科或主要服务年级还没有确认，所以我不会拿旧资料来补全。"
        admitted.append("needs_confirmation")
        provenance.append("needs_confirmation")
    return SelfProfileResult(answer, tuple(admitted), tuple(provenance))


def render_employment_history(profile: dict) -> SelfProfileResult:
    fields = _fields(profile)
    schools = []
    for key in _HISTORICAL_SCHOOLS:
        fact = _allowed_fact(fields, key, "historical")
        if fact:
            values = fact["value"] if isinstance(fact["value"], (list, tuple)) else [fact["value"]]
            schools.extend(str(value) for value in values if value not in (None, ""))
    schools = list(dict.fromkeys(schools))
    if not schools:
        return SelfProfileResult("根据当前已确认的历史资料，我还无法安全确认你以前任职过的学校。")
    return SelfProfileResult(
        f"根据你的历史个人资料，可以确认你曾经在{'、'.join(schools)}工作过。这里说的是历史经历，不是当前任职学校。",
        ("historical_profile",),
        ("historical_profile",),
    )
