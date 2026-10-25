"""Password hashing and JWT session auth.

Hard rules (Agents.md -> Secrets): secrets live only in .env, never
hardcoded, never logged. JWT_SECRET_KEY follows the same rule as
PORTKEY_API_KEY — read from the environment, never committed, never
printed.

Password handling: bcrypt only. Never store, log, or return a plaintext
password. `User.password_hash` is never included in any API response model.
"""

from __future__ import annotations

import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from backend.db import User, get_db

JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days
PASSWORD_RESET_TOKEN_EXPIRE_MINUTES = 60  # 1 hour

_bearer_scheme = HTTPBearer(auto_error=False)


def _jwt_secret() -> str:
    secret = os.environ.get("JWT_SECRET_KEY")
    if not secret:
        raise RuntimeError(
            "JWT_SECRET_KEY is not set. Add it to your local .env file "
            "(never commit it or hardcode it — see Agents.md -> Secrets)."
        )
    return secret


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def create_access_token(user_id: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, _jwt_secret(), algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> int:
    try:
        payload = jwt.decode(token, _jwt_secret(), algorithms=[JWT_ALGORITHM])
        return int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired session"
        ) from exc


def utcnow_naive() -> datetime:
    """Naive UTC "now" — use this (not datetime.now(timezone.utc)) for anything
    compared against a value loaded back from a plain SQLite DateTime column.

    SQLite/SQLAlchemy's plain DateTime column drops tzinfo on round-trip
    (confirmed empirically: a stored tz-aware value comes back naive), so
    mixing naive and tz-aware datetimes in a comparison raises TypeError.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


def generate_password_reset_token() -> tuple[str, str, datetime]:
    """Returns (raw_token, token_hash, expires_at). Only the hash is ever stored."""
    raw_token = secrets.token_urlsafe(32)
    token_hash = hash_reset_token(raw_token)
    expires_at = utcnow_naive() + timedelta(minutes=PASSWORD_RESET_TOKEN_EXPIRE_MINUTES)
    return raw_token, token_hash, expires_at


def hash_reset_token(raw_token: str) -> str:
    # sha256, not bcrypt: this is a high-entropy random token, not a human-chosen
    # password, so there's no brute-force-guessing risk to slow down against.
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    user_id = decode_access_token(credentials.credentials)
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user
