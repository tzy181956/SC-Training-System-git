from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.exceptions import bad_request, unauthorized
from app.core.security import create_access_token, verify_password
from app.models import AuthEventLog, User


GENERIC_LOGIN_FAILURE_DETAIL = "用户名或密码错误"


def authenticate_user(
    db: Session,
    username: str,
    password: str,
    *,
    login_ip: str | None = None,
    user_agent: str | None = None,
) -> str:
    normalized_username = (username or "").strip()
    user = db.query(User).filter(User.username == normalized_username).first()
    if not user:
        _record_auth_event(
            db,
            username=normalized_username,
            user=None,
            success=False,
            login_ip=login_ip,
            user_agent=user_agent,
            failure_reason="user_not_found",
        )
        raise unauthorized(GENERIC_LOGIN_FAILURE_DETAIL)
    if not user.is_active:
        _record_auth_event(
            db,
            username=normalized_username,
            user=user,
            success=False,
            login_ip=login_ip,
            user_agent=user_agent,
            failure_reason="role_disabled",
        )
        raise unauthorized(GENERIC_LOGIN_FAILURE_DETAIL)
    if not verify_password(password, user.password_hash):
        _record_auth_event(
            db,
            username=normalized_username,
            user=user,
            success=False,
            login_ip=login_ip,
            user_agent=user_agent,
            failure_reason="invalid_password",
        )
        raise unauthorized(GENERIC_LOGIN_FAILURE_DETAIL)
    if (user.role_code or "").strip().lower() not in {"admin", "coach"}:
        _record_auth_event(
            db,
            username=normalized_username,
            user=user,
            success=False,
            login_ip=login_ip,
            user_agent=user_agent,
            failure_reason="role_disabled",
        )
        raise unauthorized(GENERIC_LOGIN_FAILURE_DETAIL)
    token = create_access_token(str(user.id), token_version=user.token_version)
    user.last_login_at = datetime.now(timezone.utc)
    user.last_login_ip = login_ip
    _add_auth_event(
        db,
        username=normalized_username,
        user=user,
        success=True,
        login_ip=login_ip,
        user_agent=user_agent,
        failure_reason=None,
    )
    db.commit()
    return token


def verify_current_user_password(user: User, password: str) -> None:
    if not verify_password(password, user.password_hash):
        raise bad_request("密码错误，无法进入管理模式")


def _record_auth_event(
    db: Session,
    *,
    username: str,
    user: User | None,
    success: bool,
    login_ip: str | None,
    user_agent: str | None,
    failure_reason: str | None,
) -> None:
    _add_auth_event(
        db,
        username=username,
        user=user,
        success=success,
        login_ip=login_ip,
        user_agent=user_agent,
        failure_reason=failure_reason,
    )
    db.commit()


def _add_auth_event(
    db: Session,
    *,
    username: str,
    user: User | None,
    success: bool,
    login_ip: str | None,
    user_agent: str | None,
    failure_reason: str | None,
) -> None:
    db.add(
        AuthEventLog(
            username=_trim_required(username, 120),
            user_id=user.id if user else None,
            success=success,
            ip=_trim(login_ip, 45),
            user_agent=_trim(user_agent, 512),
            failure_reason=failure_reason,
        )
    )


def _trim_required(value: str | None, max_length: int) -> str:
    return (value or "").strip()[:max_length]


def _trim(value: str | None, max_length: int) -> str | None:
    if value is None:
        return None
    normalized_value = value.strip()
    if not normalized_value:
        return None
    return normalized_value[:max_length]
