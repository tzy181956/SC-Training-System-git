from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.exceptions import bad_request, unauthorized
from app.core.security import create_access_token, verify_password
from app.models import User


def authenticate_user(db: Session, username: str, password: str, *, login_ip: str | None = None) -> str:
    normalized_username = (username or "").strip()
    user = db.query(User).filter(User.username == normalized_username, User.is_active.is_(True)).first()
    if not user or not verify_password(password, user.password_hash):
        raise unauthorized("用户名或密码错误")
    if (user.role_code or "").strip().lower() not in {"admin", "coach"}:
        raise unauthorized("当前账号角色已停用，请联系管理员重建账号")
    token = create_access_token(str(user.id), token_version=user.token_version)
    user.last_login_at = datetime.now(timezone.utc)
    user.last_login_ip = login_ip
    db.commit()
    return token


def verify_current_user_password(user: User, password: str) -> None:
    if not verify_password(password, user.password_hash):
        raise bad_request("密码错误，无法进入管理模式")
