from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import unauthorized
from app.core.security import decode_access_token
from app.models import User


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
optional_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def _normalize_role(role_code: str | None) -> str:
    return (role_code or "").strip().lower()


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    user_id = decode_access_token(token)
    if not user_id:
        raise unauthorized()
    try:
        resolved_user_id = int(user_id)
    except (TypeError, ValueError):
        raise unauthorized() from None
    user = db.query(User).filter(User.id == resolved_user_id, User.is_active.is_(True)).first()
    if not user:
        raise unauthorized()
    return user


def get_optional_current_user(
    token: str | None = Depends(optional_oauth2_scheme),
    db: Session = Depends(get_db),
) -> User | None:
    if not token:
        return None
    user_id = decode_access_token(token)
    if not user_id:
        return None
    try:
        resolved_user_id = int(user_id)
    except (TypeError, ValueError):
        return None
    return db.query(User).filter(User.id == resolved_user_id, User.is_active.is_(True)).first()


def require_roles(*allowed_roles: str):
    normalized_roles = {_normalize_role(role) for role in allowed_roles if _normalize_role(role)}

    def dependency(current_user: User = Depends(get_current_user)) -> User:
        current_role = _normalize_role(current_user.role_code)
        if normalized_roles and current_role != "admin" and current_role not in normalized_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
        return current_user

    return dependency
