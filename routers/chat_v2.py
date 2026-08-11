from fastapi import APIRouter, Depends, HTTPException

from auth import get_current_user
from xiaole_core.errors import ConversationAccessDenied
from xiaole_core.schemas import BrainRequest, BrainResponse


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
        raise HTTPException(status_code=500, detail="XiaoLe Core request failed") from exc
