"""Password hashing and JWT access tokens."""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.config import settings


def hash_password(password: str) -> str:
    """Store only the hash; the plain password is never persisted."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    except ValueError:
        # Malformed hash in the database: treat as a failed login, never a 500.
        return False


def create_access_token(user_id: str) -> str:
    expires = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": str(user_id), "exp": expires}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> str | None:
    """Return the user id in the token, or None if it is invalid or expired."""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError:
        return None
    return payload.get("sub")


# --- password reset tokens ---------------------------------------------

RESET_TOKEN_TTL = timedelta(minutes=30)


def new_reset_token() -> tuple[str, str]:
    """Return (token to send the user, hash to store).

    Only the hash is persisted, so a database dump cannot be turned into
    working reset links.
    """
    token = secrets.token_urlsafe(32)
    return token, hash_reset_token(token)


def hash_reset_token(token: str) -> str:
    # A fast hash is right here: the token is 256 bits of randomness, so it
    # cannot be brute-forced the way a human password could.
    return hashlib.sha256(token.encode()).hexdigest()


def reset_token_expiry() -> datetime:
    return datetime.now(timezone.utc) + RESET_TOKEN_TTL
