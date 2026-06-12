"""Authentication endpoints (Phase 11)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_active_user, get_db
from app.models.user import User
from app.schemas.auth import Token, TokenRefresh, UserOut, UserRegister
from app.services.auth_service import AuthService
from app.services.rate_limiter import RateLimitCheck

router = APIRouter()


@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    dependencies=[Depends(RateLimitCheck(limit=5, window_seconds=60, scope="user"))],
)
async def register(
    payload: UserRegister,
    db: AsyncSession = Depends(get_db),
) -> UserOut:
    user = await AuthService.register_user(
        db=db,
        email=payload.email,
        password=payload.password,
        role=payload.role,
    )
    return UserOut.model_validate(user)


@router.post(
    "/login",
    response_model=Token,
    summary="Login user and issue JWT tokens (supports OAuth2 Password Flow)",
    dependencies=[Depends(RateLimitCheck(limit=5, window_seconds=60, scope="user"))],
)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
) -> Token:
    user = await AuthService.authenticate_user(
        db=db,
        email=form_data.username,
        password=form_data.password,
    )
    tokens = await AuthService.login_user(db=db, user=user)
    return Token(**tokens)


@router.post(
    "/refresh",
    response_model=Token,
    summary="Refresh access and refresh tokens (rotates refresh token)",
)
async def refresh(
    payload: TokenRefresh,
    db: AsyncSession = Depends(get_db),
) -> Token:
    tokens = await AuthService.refresh_session(db=db, refresh_token_str=payload.refresh_token)
    return Token(**tokens)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke refresh token and logout",
)
async def logout(
    payload: TokenRefresh,
    db: AsyncSession = Depends(get_db),
) -> None:
    await AuthService.revoke_session(db=db, refresh_token_str=payload.refresh_token)


@router.get(
    "/me",
    response_model=UserOut,
    summary="Get current active user details",
)
async def get_me(
    current_user: User = Depends(get_active_user),
) -> UserOut:
    return UserOut.model_validate(current_user)
