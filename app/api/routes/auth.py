from fastapi import APIRouter, Depends
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.errors import AppError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.schemas.auth import LoginRequest, RefreshRequest, RegisterRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse)
async def register(payload: RegisterRequest, session: AsyncSession = Depends(get_session)) -> TokenResponse:
    result = await session.execute(select(User).where(User.email == payload.email))
    existing = result.scalar_one_or_none()
    if existing:
        raise AppError("email_taken", "Email already registered", status_code=409)

    user = User(email=payload.email, password_hash=hash_password(payload.password))
    session.add(user)
    await session.commit()

    access = create_access_token(str(user.id))
    refresh = create_refresh_token(str(user.id))
    return TokenResponse(access_token=access, refresh_token=refresh)


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, session: AsyncSession = Depends(get_session)) -> TokenResponse:
    result = await session.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise AppError("invalid_credentials", "Invalid email or password", status_code=401)

    access = create_access_token(str(user.id))
    refresh = create_refresh_token(str(user.id))
    return TokenResponse(access_token=access, refresh_token=refresh)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(payload: RefreshRequest) -> TokenResponse:
    try:
        token_data = decode_token(payload.refresh_token, refresh=True)
    except JWTError as exc:
        raise AppError("invalid_token", "Invalid refresh token", status_code=401) from exc
    if token_data.get("type") != "refresh":
        raise AppError("invalid_token", "Invalid refresh token", status_code=401)

    subject = token_data.get("sub")
    if not subject:
        raise AppError("invalid_token", "Invalid refresh token", status_code=401)

    access = create_access_token(subject)
    refresh = create_refresh_token(subject)
    return TokenResponse(access_token=access, refresh_token=refresh)
