import uuid

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.errors import AppError
from app.core.security import decode_token
from app.models.user import User

security = HTTPBearer(auto_error=False)


async def get_current_user(
    session: AsyncSession = Depends(get_session),
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> User:
    if credentials is None:
        raise AppError("auth_required", "Authentication required", status_code=401)

    token = credentials.credentials
    try:
        payload = decode_token(token)
    except JWTError as exc:
        raise AppError("invalid_token", "Invalid access token", status_code=401) from exc
    if payload.get("type") != "access":
        raise AppError("invalid_token", "Invalid access token", status_code=401)

    try:
        user_id = uuid.UUID(payload.get("sub", ""))
    except ValueError as exc:
        raise AppError("invalid_token", "Invalid access token", status_code=401) from exc

    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise AppError("user_not_found", "User not found", status_code=401)

    return user
