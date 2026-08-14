from __future__ import annotations

import json
from typing import Literal

from pydantic import Field

from .schemas import StrictModel
from logger import logger



class Core2SafeDiagnosticsEvent(StrictModel):
    """Final safe event. `scope` is the intent router reason, not a data-access scope."""

    event: Literal["core2_safe_diagnostics"] = "core2_safe_diagnostics"
    request_id: str
    intent: Literal["conversation", "knowledge", "status", "planning", "action", "reminder"]
    scope: str
    gateways_used: list[Literal["profile", "memory", "knowledge", "status", "recommendation", "action", "reminder"]] = Field(default_factory=list)
    model_called: bool
    profile_gateway_called: bool
    profile_gateway_result: Literal["not_called", "success", "unavailable", "unauthorized", "invalid_response", "missing_fact"]
    profile_current_school_state: Literal["not_applicable", "ready", "missing", "not_confirmed", "wrong_subject", "invalid"]
    deterministic_profile_hit: bool
    profile_reason_codes: list[Literal[
        "profile_request_success", "profile_connect_error", "profile_timeout",
        "profile_http_401", "profile_http_403", "profile_http_404", "profile_http_5xx",
        "profile_invalid_json", "profile_schema_invalid", "profile_fields_missing",
        "current_school_missing", "current_school_status_not_confirmed",
        "current_school_subject_not_current_user", "current_school_value_missing",
        "current_school_ready", "deterministic_profile_hit", "deterministic_profile_miss",
    ]] = Field(default_factory=list)


def emit_core2_safe_diagnostics(event: Core2SafeDiagnosticsEvent) -> None:
    payload = {
        "event": event.event,
        "request_id": event.request_id,
        "intent": event.intent,
        "scope": event.scope,
        "gateways_used": list(event.gateways_used),
        "model_called": event.model_called,
        "profile_gateway_called": event.profile_gateway_called,
        "profile_gateway_result": event.profile_gateway_result,
        "profile_current_school_state": event.profile_current_school_state,
        "deterministic_profile_hit": event.deterministic_profile_hit,
        "profile_reason_codes": list(event.profile_reason_codes),
    }
    logger.info(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
