from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Intent(str, Enum):
    CONVERSATION = "conversation"
    KNOWLEDGE = "knowledge"
    MEMORY = "knowledge"  # Backward-compatible Python alias; API scope is knowledge.
    STATUS = "status"
    PLANNING = "planning"
    ACTION = "action"


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
    gateways_used: list[Literal["profile", "memory", "knowledge", "status", "recommendation", "action"]] = Field(default_factory=list)
    latency_ms: int = Field(default=0, ge=0)
    fallback: bool = False


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


class BrainResponse(StrictModel):
    request_id: str
    conversation_id: str
    intent: Intent
    answer: str
    sources: list[dict[str, Any]] = Field(default_factory=list)
    action: ActionResult | None = None
    diagnostics: Diagnostics
