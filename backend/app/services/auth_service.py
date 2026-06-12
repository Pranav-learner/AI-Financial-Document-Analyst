"""Authentication and session management services (Phase 11)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthenticationError, DuplicateUserError, NotFoundError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.enums import UserRole
from app.models.refresh_token import RefreshToken
from app.models.user import User


class AuthService:
    @staticmethod
    async def register_user(
        db: AsyncSession,
        email: str,
        password: str,
        role: UserRole = UserRole.VIEWER,
    ) -> User:
        """Register a new user."""
        # Check if user exists
        stmt = select(User).where(User.email == email)
        result = await db.execute(stmt)
        if result.scalar_one_or_none() is not None:
            raise DuplicateUserError(f"User with email {email} already exists.")

        user = User(
            email=email,
            password_hash=hash_password(password),
            role=role,
            is_active=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

    @staticmethod
    async def authenticate_user(
        db: AsyncSession,
        email: str,
        password: str,
    ) -> User:
        """Authenticate a user by email and password."""
        stmt = select(User).where(User.email == email)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if user is None or not user.is_active:
            raise AuthenticationError("Invalid email or password.")

        if not verify_password(password, user.password_hash):
            raise AuthenticationError("Invalid email or password.")

        return user

    @classmethod
    async def login_user(
        db: AsyncSession,
        user: User,
    ) -> dict[str, Any]:
        """Generate tokens and create a new refresh token entry."""
        access_token = create_access_token(subject=user.id)
        refresh_token_str = create_refresh_token(subject=user.id)

        # Set expiration (7 days from now by default)
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)

        token_record = RefreshToken(
            user_id=user.id,
            token=refresh_token_str,
            expires_at=expires_at,
            revoked=False,
        )
        db.add(token_record)
        await db.commit()

        return {
            "access_token": access_token,
            "refresh_token": refresh_token_str,
            "token_type": "bearer",
        }

    @staticmethod
    async def refresh_session(
        db: AsyncSession,
        refresh_token_str: str,
    ) -> dict[str, Any]:
        """Rotate the refresh token and issue a new access token."""
        try:
            payload = decode_token(refresh_token_str)
            if payload.get("type") != "refresh":
                raise AuthenticationError("Invalid token type")
            user_id = payload.get("sub")
        except Exception as e:
            raise AuthenticationError("Invalid refresh token") from e

        # Query token record
        stmt = select(RefreshToken).where(RefreshToken.token == refresh_token_str)
        result = await db.execute(stmt)
        token_record = result.scalar_one_or_none()

        if token_record is None or token_record.revoked:
            raise AuthenticationError("Refresh token has been revoked or is invalid")

        if token_record.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
            raise AuthenticationError("Refresh token has expired")

        # Query user
        stmt_user = select(User).where(User.id == token_record.user_id)
        res_user = await db.execute(stmt_user)
        user = res_user.scalar_one_or_none()

        if user is None or not user.is_active:
            raise AuthenticationError("User is inactive or not found")

        # Revoke the old refresh token
        token_record.revoked = True

        # Generate new pair
        new_access_token = create_access_token(subject=user.id)
        new_refresh_token_str = create_refresh_token(subject=user.id)
        new_expires_at = datetime.now(timezone.utc) + timedelta(days=7)

        new_token_record = RefreshToken(
            user_id=user.id,
            token=new_refresh_token_str,
            expires_at=new_expires_at,
            revoked=False,
        )
        db.add(new_token_record)
        await db.commit()

        return {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token_str,
            "token_type": "bearer",
        }

    @staticmethod
    async def revoke_session(
        db: AsyncSession,
        refresh_token_str: str,
    ) -> None:
        """Revoke a refresh token on logout."""
        stmt = select(RefreshToken).where(RefreshToken.token == refresh_token_str)
        result = await db.execute(stmt)
        token_record = result.scalar_one_or_none()

        if token_record is not None:
            token_record.revoked = True
            await db.commit()
