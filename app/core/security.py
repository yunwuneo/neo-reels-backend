from datetime import datetime, timedelta, timezone
from typing import Any

from jose import jwt
from passlib.context import CryptContext

from app.core.config import get_settings

settings = get_settings()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def _create_token(subject: str, expires_minutes: int, secret_key: str, token_type: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
    to_encode: dict[str, Any] = {"sub": subject, "exp": expire, "type": token_type}
    return jwt.encode(to_encode, secret_key, algorithm="HS256")


def create_access_token(subject: str) -> str:
    return _create_token(
        subject=subject,
        expires_minutes=settings.access_token_expire_minutes,
        secret_key=settings.jwt_secret_key,
        token_type="access",
    )


def create_refresh_token(subject: str) -> str:
    return _create_token(
        subject=subject,
        expires_minutes=settings.refresh_token_expire_minutes,
        secret_key=settings.jwt_refresh_secret_key,
        token_type="refresh",
    )


def decode_token(token: str, refresh: bool = False) -> dict[str, Any]:
    secret = settings.jwt_refresh_secret_key if refresh else settings.jwt_secret_key
    return jwt.decode(token, secret, algorithms=["HS256"])
