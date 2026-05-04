from typing import cast

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.core.database import get_db
from app.models import User
from app.schemas.user import UserCreate, UserManagementRead, UserPasswordResetPayload, UserRoleCode, UserUpdate
from app.services import user_service


router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserManagementRead])
def list_users(db: Session = Depends(get_db), current_user: User = Depends(require_roles("admin"))):
    _ = current_user
    return [_to_user_read(user) for user in user_service.list_users(db)]


@router.post("", response_model=UserManagementRead, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    user = user_service.create_user(
        db,
        username=payload.username,
        display_name=payload.display_name,
        role_code=payload.role_code,
        password=payload.password,
        team_id=payload.team_id,
        is_active=payload.is_active,
        actor_name=current_user.display_name,
        allow_teamless_role=False,
    )
    return _to_user_read(user)


@router.patch("/{user_id}", response_model=UserManagementRead)
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    user = user_service.update_user(
        db,
        user_id=user_id,
        display_name=payload.display_name,
        role_code=payload.role_code,
        team_id=payload.team_id,
        is_active=payload.is_active,
        actor_name=current_user.display_name,
        acting_user=current_user,
    )
    return _to_user_read(user)


@router.post("/{user_id}/reset-password", response_model=UserManagementRead)
def reset_user_password(
    user_id: int,
    payload: UserPasswordResetPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    user = user_service.reset_password(
        db,
        user_id=user_id,
        password=payload.password,
        actor_name=current_user.display_name,
    )
    return _to_user_read(user)


def _to_user_read(user: User) -> UserManagementRead:
    return UserManagementRead(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        role_code=cast(UserRoleCode, (user.role_code or "").strip().lower()),
        team_id=user.team_id,
        team_name=user.team.name if user.team else None,
        is_active=user.is_active,
    )
