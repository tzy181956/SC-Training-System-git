from sqlalchemy.orm import Session

from app.core.exceptions import unauthorized
from app.core.security import create_access_token, verify_password
from app.models import User


def authenticate_user(db: Session, username: str, password: str) -> str:
    user = db.query(User).filter(User.username == username, User.is_active.is_(True)).first()
    if not user or not verify_password(password, user.password_hash):
        raise unauthorized("用户名或密码错误")
    return create_access_token(str(user.id))
