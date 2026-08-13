from fastapi import APIRouter, Depends, HTTPException
from auth import get_current_user
from xiaole_home.models import HomeViewModel

router=APIRouter(tags=["home-v2"])

def get_home_service():
    from xiaole_home.dependencies import build_home_service
    return build_home_service()

@router.get("/v2/home", response_model=HomeViewModel)
def home_v2(current_user: str=Depends(get_current_user), service=Depends(get_home_service)):
    try: return service.get(current_user)
    except Exception as exc: raise HTTPException(status_code=500,detail="XiaoLe Home request failed") from exc
