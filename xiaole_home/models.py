from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


HealthStatus = Literal["healthy", "degraded", "unavailable"]
Availability = Literal["available", "unavailable"]


class SystemHealth(BaseModel):
    status: HealthStatus
    label: str
    message: str


class Degradation(BaseModel):
    dependency: Literal["lezhi", "xiaoke", "conversations"]
    code: Literal["timeout", "unavailable", "invalid_response", "stale"]
    message: str


class HomeViewModel(BaseModel):
    schema_version: Literal[1] = 1
    generated_at: str
    cache: dict[str, Any]
    today: dict[str, Any]
    recommendations: dict[str, Any]
    no_notification_summary: dict[str, Any]
    systems: dict[str, SystemHealth]
    profile_status: dict[str, Any]
    recent_conversations: list[dict[str, Any]] = Field(default_factory=list)
    quick_questions: list[str] = Field(default_factory=list)
    degradations: list[Degradation] = Field(default_factory=list)
