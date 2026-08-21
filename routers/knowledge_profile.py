from fastapi import APIRouter, Depends, HTTPException

from auth import get_current_user
from xiaole_home.knowledge_profile import map_knowledge_profile


router = APIRouter(tags=["knowledge-profile"])


def get_knowledge_profile_gateway():
    from xiaole_home.dependencies import build_home_service

    return build_home_service().lezhi


@router.get("/v2/knowledge/profile")
def knowledge_profile(
    current_user: str = Depends(get_current_user),
    gateway=Depends(get_knowledge_profile_gateway),
):
    del current_user
    try:
        return map_knowledge_profile(gateway.profile())
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Knowledge Profile unavailable") from exc
