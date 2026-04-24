from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.schemas.auth import LoginRequest, TokenResponse, UserRead
from app.services.auth_service import authenticate_user


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    return TokenResponse(access_token=authenticate_user(db, payload.username, payload.password))


@router.get("/me", response_model=UserRead)
def me(current_user=Depends(get_current_user)) -> UserRead:
    role_code = current_user.role_code
    mode = "management" if role_code in {"coach", "admin"} else "training"
    return UserRead(
        id=current_user.id,
        username=current_user.username,
        display_name=current_user.display_name,
        role_code=role_code,
        team_id=current_user.team_id,
        mode=mode,
        can_manage_system=role_code in {"coach", "admin"},
        can_switch_athletes=role_code == "training",
        is_active=current_user.is_active,
    )
