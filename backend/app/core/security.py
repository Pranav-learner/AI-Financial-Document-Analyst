"""Security configuration and utilities (Phase 11)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings
from app.models.enums import UserRole

# Reusable role alias and hierarchy
Role = UserRole

ROLE_HIERARCHY: dict[UserRole, set[UserRole]] = {
    UserRole.ADMIN: {UserRole.ADMIN, UserRole.ANALYST, UserRole.VIEWER},
    UserRole.ANALYST: {UserRole.ANALYST, UserRole.VIEWER},
    UserRole.VIEWER: {UserRole.VIEWER},
}

# bcrypt operates on the first 72 *bytes* of the password and raises on longer
# inputs in 4.1+. We truncate explicitly (matching long-standing passlib/bcrypt
# behaviour) so hashing is stable across bcrypt releases. Using the `bcrypt`
# package directly avoids the passlib 1.7.x <-> bcrypt >=4.1 backend break that
# crashed every hash/verify call at runtime (see Phase 12 bug sweep).
_BCRYPT_MAX_BYTES = 72


def _prepare(password: str) -> bytes:
    """Encode and truncate a password to bcrypt's 72-byte working limit."""
    return password.encode("utf-8")[:_BCRYPT_MAX_BYTES]


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(_prepare(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against its hash. Returns False on malformed hashes."""
    try:
        return bcrypt.checkpw(_prepare(plain_password), hashed_password.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_access_token(subject: str | Any, expires_delta: timedelta | None = None) -> str:
    """Issue a signed JWT access token."""
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)

    to_encode = {"exp": expire, "sub": str(subject), "type": "access"}
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_refresh_token(subject: str | Any, expires_delta: timedelta | None = None) -> str:
    """Issue a signed JWT refresh token."""
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days)

    to_encode = {"exp": expire, "sub": str(subject), "type": "refresh"}
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict[str, Any]:
    """Verify and decode a JWT."""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return payload
    except JWTError as e:
        raise ValueError("Could not validate credentials") from e
