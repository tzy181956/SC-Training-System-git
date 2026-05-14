from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings


# Use PBKDF2-SHA256 to avoid Windows passlib+bcrypt backend compatibility issues in V1.
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
settings = get_settings()
ALGORITHM = "HS256"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    # Keep the auth service interface stable while swapping the underlying hash scheme.
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    # Hash demo and app passwords with a backend that does not require bcrypt runtime support.
    return pwd_context.hash(password)


def create_access_token(subject: str, *, token_version: int = 1) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    return jwt.encode({"sub": subject, "ver": int(token_version or 1), "exp": expire}, settings.secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> str | None:
    payload = decode_access_token_payload(token)
    if not payload:
        return None
    return payload.get("sub")


def decode_access_token_payload(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
    except JWTError:
        return None
    return payload
