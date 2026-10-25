"""Tests for the forgot-password / reset-password flow (backend/main.py, backend/auth.py).

Uses the same isolated in-memory DB fixture as tests/test_api.py.
"""

import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.auth import hash_reset_token, utcnow_naive
from backend.db import PasswordResetToken, User

from tests.test_api import auth_headers, client, signup  # noqa: F401 (reuse the `client` fixture)


def _get_reset_token_for(db_session, email: str) -> str:
    """Pull the raw reset token the same way a real email would have delivered
    it, by regenerating it directly against the DB (mirrors what the endpoint
    does, since the real token is only ever logged, never returned by the API —
    see backend/main.py's forgot_password)."""
    from backend.auth import generate_password_reset_token

    user = db_session.query(User).filter(User.email == email).first()
    raw_token, token_hash, expires_at = generate_password_reset_token()
    db_session.add(PasswordResetToken(user_id=user.id, token_hash=token_hash, expires_at=expires_at))
    db_session.commit()
    return raw_token


def _db_session_from_client(client):
    # The `client` fixture overrides get_db with an in-memory engine; grab a session from it.
    from backend.db import get_db
    from backend.main import app

    override = app.dependency_overrides[get_db]
    return next(override())


def test_forgot_password_returns_generic_message_for_unknown_email(client):
    r = client.post("/api/auth/forgot-password", json={"email": "nobody@example.com"})
    assert r.status_code == 200
    assert "if an account exists" in r.json()["message"].lower()


def test_forgot_password_returns_same_generic_message_for_known_email(client):
    signup(client, email="parent@example.com")
    r = client.post("/api/auth/forgot-password", json={"email": "parent@example.com"})
    assert r.status_code == 200
    assert "if an account exists" in r.json()["message"].lower()


def test_reset_password_with_valid_token_works_and_old_password_stops_working(client):
    signup(client, email="parent@example.com", password="originalPass123")
    db = _db_session_from_client(client)
    raw_token = _get_reset_token_for(db, "parent@example.com")

    r = client.post(
        "/api/auth/reset-password", json={"token": raw_token, "new_password": "brandNewPass456"}
    )
    assert r.status_code == 200

    old_login = client.post(
        "/api/auth/login", json={"email": "parent@example.com", "password": "originalPass123"}
    )
    assert old_login.status_code == 401

    new_login = client.post(
        "/api/auth/login", json={"email": "parent@example.com", "password": "brandNewPass456"}
    )
    assert new_login.status_code == 200


def test_reset_token_is_single_use(client):
    signup(client, email="parent@example.com", password="originalPass123")
    db = _db_session_from_client(client)
    raw_token = _get_reset_token_for(db, "parent@example.com")

    first = client.post(
        "/api/auth/reset-password", json={"token": raw_token, "new_password": "firstNewPass1"}
    )
    assert first.status_code == 200

    second = client.post(
        "/api/auth/reset-password", json={"token": raw_token, "new_password": "secondNewPass2"}
    )
    assert second.status_code == 400


def test_expired_reset_token_is_rejected(client):
    signup(client, email="parent@example.com")
    db = _db_session_from_client(client)
    user = db.query(User).filter(User.email == "parent@example.com").first()

    raw_token = "expired-token-value"
    db.add(
        PasswordResetToken(
            user_id=user.id,
            token_hash=hash_reset_token(raw_token),
            expires_at=utcnow_naive() - timedelta(minutes=1),
        )
    )
    db.commit()

    r = client.post(
        "/api/auth/reset-password", json={"token": raw_token, "new_password": "somethingNew123"}
    )
    assert r.status_code == 400


def test_garbage_token_is_rejected(client):
    r = client.post(
        "/api/auth/reset-password", json={"token": "not-a-real-token", "new_password": "somethingNew123"}
    )
    assert r.status_code == 400


def test_short_new_password_is_rejected(client):
    r = client.post(
        "/api/auth/reset-password", json={"token": "whatever", "new_password": "short"}
    )
    assert r.status_code == 422
