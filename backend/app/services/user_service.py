from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session, joinedload

from app.core.exceptions import bad_request, not_found
from app.core.security import get_password_hash
from app.models import Sport, User
from app.services import content_change_log_service
from app.services.access_control_service import normalize_role_code


ALLOWED_ROLE_CODES = {"admin", "coach"}
MIN_PASSWORD_LENGTH = 8


def list_users(db: Session) -> list[User]:
    return (
        db.query(User)
        .options(joinedload(User.sport))
        .order_by(User.role_code.asc(), User.display_name.asc(), User.username.asc())
        .all()
    )


def get_user(db: Session, user_id: int) -> User:
    user = (
        db.query(User)
        .options(joinedload(User.sport))
        .filter(User.id == user_id)
        .first()
    )
    if not user:
        raise not_found("用户不存在")
    return user


def create_user(
    db: Session,
    *,
    username: str,
    display_name: str,
    role_code: str,
    password: str,
    sport_id: int | None = None,
    is_active: bool = True,
    actor_name: str | None = None,
    allow_sportless_role: bool = False,
) -> User:
    normalized_username = _normalize_username(username)
    normalized_display_name = _normalize_display_name(display_name)
    normalized_role_code = _normalize_role_or_raise(role_code)
    _validate_password(password)
    normalized_sport_id = _resolve_sport_id(
        db,
        role_code=normalized_role_code,
        sport_id=sport_id,
        allow_sportless_role=allow_sportless_role,
    )

    existing = db.query(User).filter(User.username == normalized_username).first()
    if existing:
        raise bad_request("用户名已存在")

    user = User(
        username=normalized_username,
        display_name=normalized_display_name,
        role_code=normalized_role_code,
        password_hash=get_password_hash(password),
        sport_id=normalized_sport_id,
        team_id=None,
        is_active=is_active,
    )
    db.add(user)
    db.flush()

    content_change_log_service.log_content_change(
        db,
        action_type="create",
        object_type="user",
        object_id=user.id,
        object_label=user.display_name,
        actor_name=actor_name,
        team_id=None,
        summary=f"新建账号“{user.display_name}”",
        after_snapshot=_serialize_user(user),
    )
    db.commit()
    return get_user(db, user.id)


def update_user(
    db: Session,
    *,
    user_id: int,
    display_name: str | None = None,
    role_code: str | None = None,
    sport_id: int | None = None,
    is_active: bool | None = None,
    actor_name: str | None = None,
    acting_user: User,
) -> User:
    user = get_user(db, user_id)
    before_snapshot = _serialize_user(user)

    next_role_code = _normalize_role_or_raise(role_code) if role_code is not None else normalize_role_code(user.role_code)
    next_display_name = _normalize_display_name(display_name) if display_name is not None else user.display_name
    next_is_active = is_active if is_active is not None else user.is_active
    requested_sport_id = sport_id if role_code is not None or sport_id is not None else user.sport_id

    _ensure_admin_update_allowed(db, user=user, acting_user=acting_user, next_role_code=next_role_code, next_is_active=next_is_active)
    next_sport_id = _resolve_sport_id(
        db,
        role_code=next_role_code,
        sport_id=requested_sport_id,
        allow_sportless_role=False,
    )
    should_revoke_tokens = next_role_code != normalize_role_code(user.role_code) or next_is_active != user.is_active

    user.display_name = next_display_name
    user.role_code = next_role_code
    user.sport_id = next_sport_id
    user.team_id = None
    user.is_active = next_is_active
    if should_revoke_tokens:
        _increment_token_version(user)
    db.flush()

    content_change_log_service.log_content_change(
        db,
        action_type="update",
        object_type="user",
        object_id=user.id,
        object_label=user.display_name,
        actor_name=actor_name,
        team_id=None,
        summary=f"更新账号“{user.display_name}”",
        before_snapshot=before_snapshot,
        after_snapshot=_serialize_user(user),
    )
    db.commit()
    return get_user(db, user.id)


def reset_password(
    db: Session,
    *,
    user_id: int,
    password: str,
    actor_name: str | None = None,
) -> User:
    user = get_user(db, user_id)
    _validate_password(password)

    before_snapshot = {"password_updated": False}
    user.password_hash = get_password_hash(password)
    user.password_changed_at = datetime.now(timezone.utc)
    _increment_token_version(user)
    db.flush()
    content_change_log_service.log_content_change(
        db,
        action_type="reset_password",
        object_type="user",
        object_id=user.id,
        object_label=user.display_name,
        actor_name=actor_name,
        team_id=None,
        summary=f"重置账号“{user.display_name}”密码",
        before_snapshot=before_snapshot,
        after_snapshot={"password_updated": True},
    )
    db.commit()
    return get_user(db, user.id)


def count_active_admins(db: Session) -> int:
    return db.query(User).filter(User.role_code == "admin", User.is_active.is_(True)).count()


def _normalize_username(value: str) -> str:
    normalized = (value or "").strip()
    if not normalized:
        raise bad_request("用户名不能为空")
    return normalized


def _normalize_display_name(value: str | None) -> str:
    normalized = (value or "").strip()
    if not normalized:
        raise bad_request("显示名称不能为空")
    return normalized


def _normalize_role_or_raise(role_code: str) -> str:
    normalized = normalize_role_code(role_code)
    if normalized not in ALLOWED_ROLE_CODES:
        raise bad_request("角色类型不受支持")
    return normalized


def _validate_password(password: str) -> None:
    if len(password or "") < MIN_PASSWORD_LENGTH:
        raise bad_request(f"密码长度不能少于 {MIN_PASSWORD_LENGTH} 位")


def _resolve_sport_id(
    db: Session,
    *,
    role_code: str,
    sport_id: int | None,
    allow_sportless_role: bool,
) -> int | None:
    if role_code == "admin":
        return None

    if sport_id is None:
        if allow_sportless_role:
            return None
        raise bad_request("教练账号必须绑定项目")

    sport = db.query(Sport).filter(Sport.id == sport_id).first()
    if not sport:
        raise bad_request("绑定项目不存在，请先刷新后重试")
    return sport.id


def _ensure_admin_update_allowed(
    db: Session,
    *,
    user: User,
    acting_user: User,
    next_role_code: str,
    next_is_active: bool,
) -> None:
    current_role_code = normalize_role_code(user.role_code)
    current_user_role = normalize_role_code(acting_user.role_code)

    if user.id == acting_user.id and current_user_role == "admin":
        if next_role_code != "admin":
            raise bad_request("当前登录的管理员不能把自己改成非管理员")
        if not next_is_active:
            raise bad_request("当前登录的管理员不能停用自己")

    if current_role_code != "admin" or (next_role_code == "admin" and next_is_active):
        return

    if count_active_admins(db) <= 1:
        if next_role_code != "admin":
            raise bad_request("不能移除最后一个启用中的管理员")
        if not next_is_active:
            raise bad_request("不能停用最后一个启用中的管理员")


def _serialize_user(user: User) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "display_name": user.display_name,
        "role_code": normalize_role_code(user.role_code),
        "sport_id": user.sport_id,
        "is_active": user.is_active,
    }


def _increment_token_version(user: User) -> None:
    user.token_version = int(user.token_version or 1) + 1
