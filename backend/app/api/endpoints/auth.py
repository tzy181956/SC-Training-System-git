from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.schemas.auth import (
    LoginRequest,
    TokenResponse,
    UserRead,
    VerifyPasswordRequest,
    VerifyPasswordResponse,
)
from app.services.auth_service import authenticate_user, verify_current_user_password


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)) -> TokenResponse:
    login_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    return TokenResponse(
        access_token=authenticate_user(
            db,
            payload.username,
            payload.password,
            login_ip=login_ip,
            user_agent=user_agent,
        )
    )


@router.post("/verify-password", response_model=VerifyPasswordResponse)
def verify_password(
    payload: VerifyPasswordRequest,
    current_user=Depends(get_current_user),
) -> VerifyPasswordResponse:
    verify_current_user_password(current_user, payload.password)
    return VerifyPasswordResponse(verified=True)


@router.get("/me", response_model=UserRead)
def me(current_user=Depends(get_current_user)) -> UserRead:
    role_code = (current_user.role_code or "").strip().lower()
    if role_code == "admin":
        mode = "management"
        available_modes = ["management", "training", "monitor"]
    elif role_code == "coach":
        mode = "training"
        available_modes = ["management", "training", "monitor"]
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="当前账号角色已停用，请联系管理员重建账号。")
    can_manage_users = role_code == "admin"
    can_manage_system = role_code in {"coach", "admin"}
    return UserRead(
        id=current_user.id,
        username=current_user.username,
        display_name=current_user.display_name,
        role_code=role_code,
        sport_id=current_user.sport_id,
        sport_name=current_user.sport.name if getattr(current_user, "sport", None) else None,
        mode=mode,
        available_modes=available_modes,
        capabilities=_build_capabilities(
            role_code=role_code,
            available_modes=available_modes,
            can_manage_users=can_manage_users,
            can_manage_system=can_manage_system,
        ),
        can_manage_users=can_manage_users,
        can_manage_system=can_manage_system,
        is_active=current_user.is_active,
    )


def _build_capabilities(
    *,
    role_code: str,
    available_modes: list[str],
    can_manage_users: bool,
    can_manage_system: bool,
) -> dict[str, bool]:
    modes = set(available_modes)
    can_access_management = "management" in modes
    can_access_training = "training" in modes
    can_access_monitor = "monitor" in modes
    can_manage_admin_only = role_code == "admin"
    can_manage_coach_scope = role_code in {"admin", "coach"} and can_access_management

    return {
        "can_manage_users": can_manage_users,
        "can_manage_sports": can_manage_admin_only and can_access_management,
        "can_manage_teams": can_manage_coach_scope,
        "can_manage_athletes": can_manage_coach_scope,
        "can_manage_templates": can_manage_coach_scope,
        "can_manage_backups": can_manage_admin_only and can_access_management,
        "can_manage_test_definitions": can_manage_coach_scope,
        "can_import_test_records": can_manage_coach_scope,
        "can_enter_training": can_access_training,
        "can_view_monitor": can_access_monitor,
        "can_run_maintenance": can_manage_admin_only and can_access_management,
        "manage_users": can_manage_users,
        "manage_system": can_manage_system,
        "access_management": can_access_management,
        "access_training": can_access_training,
        "access_monitor": can_access_monitor,
    }
