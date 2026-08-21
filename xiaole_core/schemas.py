from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Intent(str, Enum):
    CONVERSATION = "conversation"
    KNOWLEDGE = "knowledge"
    MEMORY = "knowledge"  # Backward-compatible Python alias; API scope is knowledge.
    STATUS = "status"
    PLANNING = "planning"
    ACTION = "action"
    REMINDER = "reminder"


class IntentDecision(StrictModel):
    intent: Intent
    reason_code: str
    used_fallback: bool = False


class BrainRequest(StrictModel):
    message: str = Field(min_length=1, max_length=12000)
    conversation_id: str | None = None
    attachments: list[dict[str, Any]] = Field(default_factory=list)


class Source(StrictModel):
    model_config = ConfigDict(extra="allow")
    title: str = ""


class Diagnostics(StrictModel):
    model: str = ""
    gateway_used: str | None = None
    gateways_used: list[Literal["profile", "memory", "knowledge", "status", "recommendation", "action", "reminder"]] = Field(default_factory=list)
    latency_ms: int = Field(default=0, ge=0)
    fallback: bool = False
    profile_gateway_called: bool = False
    profile_gateway_result: Literal["not_called", "success", "unavailable", "unauthorized", "invalid_response", "missing_fact"] = "not_called"
    profile_current_school_state: Literal["not_applicable", "ready", "missing", "not_confirmed", "wrong_subject", "invalid"] = "not_applicable"
    deterministic_profile_hit: bool = False
    profile_reason_codes: list[Literal[
        "profile_request_success", "profile_connect_error", "profile_timeout",
        "profile_http_401", "profile_http_403", "profile_http_404", "profile_http_5xx",
        "profile_invalid_json", "profile_schema_invalid", "profile_fields_missing",
        "current_school_missing", "current_school_status_not_confirmed",
        "current_school_subject_not_current_user", "current_school_value_missing",
        "current_school_ready", "deterministic_profile_hit", "deterministic_profile_miss",
    ]] = Field(default_factory=list)
    profile_scope: Literal["not_applicable", "self_profile", "employment_history"] = "not_applicable"
    admitted_source_categories: list[Literal[
        "confirmed_profile", "historical_profile", "needs_confirmation", "governed_user_knowledge",
    ]] = Field(default_factory=list)
    excluded_source_categories: list[Literal[
        "legacy", "conversation", "old_schedule", "behavior_pattern", "model_inference",
    ]] = Field(default_factory=list)
    renderer: Literal["not_applicable", "deterministic"] = "not_applicable"
    provenance_categories: list[Literal[
        "user_confirmed_profile", "historical_profile", "needs_confirmation", "governed_user_knowledge",
    ]] = Field(default_factory=list)


class ProfileGatewayResponse(StrictModel):
    payload: dict[str, Any] = Field(default_factory=dict, exclude=True, repr=False)
    result: Literal["success", "unavailable", "unauthorized", "invalid_response"]
    reason_codes: list[Literal[
        "profile_request_success", "profile_connect_error", "profile_timeout",
        "profile_http_401", "profile_http_403", "profile_http_404", "profile_http_5xx",
        "profile_invalid_json", "profile_schema_invalid",
    ]] = Field(default_factory=list)


class MemoryResult(StrictModel):
    answer: str
    sources: list[dict[str, Any]] = Field(default_factory=list)
    confidence: Literal["grounded", "degraded", "no_sources"]
    request_id: str


class ActionCommand(StrictModel):
    task_type: Literal["notification.send"]
    parameters: dict[str, Any]
    conversation_id: str
    request_id: str

    @classmethod
    def notification(cls, conversation_id: str, request_id: str) -> "ActionCommand":
        key = f"xiaole:{request_id}"
        return cls(
            task_type="notification.send",
            conversation_id=conversation_id,
            request_id=request_id,
            parameters={
                "title": "【小乐 2.0】",
                "body": "小乐已成功通过小可完成生产闭环。",
                "level": "active",
                "group": "小乐",
                "url": "",
                "urgency": "normal",
                "delivery": "bark",
                "dedupe_key": key,
                "metadata": {},
            },
        )


class ActionResult(StrictModel):
    task_id: str
    status: Literal["pending", "running", "success", "failed", "cancelled", "dead", "timeout"]
    summary: str
    evidence: dict[str, Any] = Field(default_factory=dict)
    request_id: str


class ReminderCreateCommand(StrictModel):
    idempotency_key: str = Field(min_length=1, max_length=200)
    title: str = Field(min_length=1, max_length=200)
    category: Literal["repayment", "work", "daily"]
    event_at: str
    notify_at: str
    amount: str | None = Field(default=None, pattern=r"^\d+(?:\.\d{1,2})?$")
    notification_title: str = Field(min_length=1, max_length=200)
    notification_body: str = Field(min_length=1, max_length=5000)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("event_at", "notify_at")
    @classmethod
    def shanghai_offset_required(cls, value: str) -> str:
        if not value.endswith("+08:00"):
            raise ValueError("reminder times must use +08:00")
        return value

    def action_core_payload(self) -> dict[str, Any]:
        return {**self.model_dump(), "source_system": "xiaole", "timezone": "Asia/Shanghai", "currency": "CNY"}


class ReminderResult(StrictModel):
    reminder_id: str
    title: str
    category: Literal["repayment", "work", "daily"]
    event_at: str
    notify_at: str
    timezone: str
    status: Literal["draft", "enabled", "processing", "completed", "failed", "paused", "cancelled"]
    requires_confirmation: bool = False
    amount: str | None = None


class BrainResponse(StrictModel):
    request_id: str
    conversation_id: str
    intent: Intent
    answer: str
    sources: list[dict[str, Any]] = Field(default_factory=list)
    action: ActionResult | None = None
    diagnostics: Diagnostics
