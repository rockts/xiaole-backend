import uuid

from fastapi import APIRouter, Depends, HTTPException

from auth import get_current_user
from xiaole_core.errors import ConversationAccessDenied
from xiaole_core.schemas import BrainRequest, BrainResponse
from xiaole_core.safe_diagnostics import Core2SafeDiagnosticsEvent, emit_core2_safe_diagnostics


router = APIRouter(tags=["chat-v2"])


def get_brain_core():
    from xiaole_core.dependencies import build_brain_core
    return build_brain_core()


@router.post("/v2/chat", response_model=BrainResponse)
def chat_v2(request: BrainRequest, current_user: str = Depends(get_current_user), brain=Depends(get_brain_core)):
    try:
        return brain.respond(request, current_user)
    except ConversationAccessDenied as exc:
        raise HTTPException(status_code=403, detail="Conversation access denied") from exc
    except Exception as exc:
        emit_core2_safe_diagnostics(Core2SafeDiagnosticsEvent(
            request_id=str(uuid.uuid4()),
            intent="conversation",
            scope="validation_safe_failure",
            gateways_used=[],
            model_called=False,
            profile_gateway_called=False,
            profile_gateway_result="not_called",
            profile_current_school_state="not_applicable",
            deterministic_profile_hit=False,
            profile_reason_codes=[],
        ))
        raise HTTPException(status_code=500, detail="XiaoLe Core request failed") from exc
