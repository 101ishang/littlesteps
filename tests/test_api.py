"""Tests for the auth + children + screening-history API (backend/main.py).

Uses an isolated in-memory SQLite database per test (never the real
data/app.db) and a throwaway JWT secret, so these tests never touch real
user data or secrets.
"""

import os
import sys
from pathlib import Path

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-do-not-use-in-production")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import backend.main as main_module
from backend.agents import AIExplanationOutcome, FALLBACK_EXPLANATION
from backend.db import Base, get_db
from backend.main import app

# These endpoint tests exercise HTTP/DB behavior, not the LLM itself (that's
# tests/test_agents.py, via FunctionModel) — stub out the real Portkey call so
# this suite stays fast, free, and network-independent, per Agents.md -> Testing.
_STUB_AI_OUTCOME = AIExplanationOutcome(
    explanation=FALLBACK_EXPLANATION,
    used_fallback=True,
    safety_passed=None,
    safety_reason="stubbed for tests",
    input_tokens=42,
    output_tokens=17,
    model="gpt-6-luna",
)


@pytest.fixture(autouse=True)
def _stub_generate_explanation(monkeypatch):
    async def _fake_generate_explanation(result, child_nickname, age_label):
        return _STUB_AI_OUTCOME

    monkeypatch.setattr(main_module, "generate_explanation", _fake_generate_explanation)


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def signup(client, email="parent@example.com", password="correcthorsebattery"):
    return client.post("/api/auth/signup", json={"email": email, "password": password})


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_signup_and_login_roundtrip(client):
    r = signup(client)
    assert r.status_code == 201
    token = r.json()["access_token"]
    assert token

    r2 = client.post(
        "/api/auth/login", json={"email": "parent@example.com", "password": "correcthorsebattery"}
    )
    assert r2.status_code == 200
    assert r2.json()["access_token"]


def test_duplicate_email_is_rejected(client):
    signup(client)
    r = signup(client)
    assert r.status_code == 409


def test_wrong_password_is_rejected(client):
    signup(client)
    r = client.post("/api/auth/login", json={"email": "parent@example.com", "password": "wrongpassword"})
    assert r.status_code == 401


def test_short_password_is_rejected(client):
    r = signup(client, password="short")
    assert r.status_code == 422


def test_me_requires_auth(client):
    assert client.get("/api/auth/me").status_code == 401


def test_me_returns_no_password_field(client):
    token = signup(client).json()["access_token"]
    r = client.get("/api/auth/me", headers=auth_headers(token))
    assert r.status_code == 200
    body = r.json()
    assert body["email"] == "parent@example.com"
    assert "password" not in body
    assert "password_hash" not in body


def test_children_require_auth(client):
    assert client.get("/api/children").status_code == 401
    assert (
        client.post("/api/children", json={"nickname": "Kid", "date_of_birth": "2026-01-01"}).status_code
        == 401
    )


def test_create_and_list_own_child(client):
    token = signup(client).json()["access_token"]
    r = client.post(
        "/api/children",
        json={"nickname": "Maya", "date_of_birth": "2026-01-01", "gestational_age_weeks": 40},
        headers=auth_headers(token),
    )
    assert r.status_code == 201
    child = r.json()
    assert child["nickname"] == "Maya"

    r2 = client.get("/api/children", headers=auth_headers(token))
    assert r2.status_code == 200
    assert len(r2.json()) == 1


def test_user_cannot_access_another_users_child(client):
    token_a = signup(client, email="a@example.com").json()["access_token"]
    token_b = signup(client, email="b@example.com").json()["access_token"]

    child = client.post(
        "/api/children",
        json={"nickname": "Maya", "date_of_birth": "2026-01-01"},
        headers=auth_headers(token_a),
    ).json()

    r = client.post(
        f"/api/children/{child['id']}/screenings",
        json={"age_label": "9 months", "answers": []},
        headers=auth_headers(token_b),
    )
    assert r.status_code == 404


def test_submit_screening_persists_history_and_anonymized_analytics(client):
    token = signup(client).json()["access_token"]
    child = client.post(
        "/api/children",
        json={"nickname": "Maya", "date_of_birth": "2026-01-01"},
        headers=auth_headers(token),
    ).json()

    r = client.post(
        f"/api/children/{child['id']}/screenings",
        json={
            "age_label": "9 months",
            "answers": [
                {
                    "milestone_id": "9mo.lc.1",
                    "domain": "language_communication",
                    "text": "Makes a lot of different sounds",
                    "answer": "not_yet",
                }
            ],
        },
        headers=auth_headers(token),
    )
    assert r.status_code == 201
    body = r.json()
    assert body["result"]["band"] == "worth_watching"
    assert body["ai"]["used_fallback"] is True  # stubbed in this suite — see _stub_generate_explanation

    history = client.get(f"/api/children/{child['id']}/screenings", headers=auth_headers(token)).json()
    assert len(history) == 1
    assert history[0]["band"] == "worth_watching"
    assert history[0]["flagged_count"] == 1
    assert history[0]["ai_used_fallback"] is True

    summary = client.get("/api/analytics/summary").json()
    assert summary["total_screenings"] == 1
    assert summary["by_age_and_band"][0]["age_label"] == "9 months"
    assert summary["tokenomics"]["runs_with_ai_explanation"] == 1
    assert summary["tokenomics"]["total_input_tokens"] == 42


def test_analytics_summary_never_includes_identifiers(client):
    token = signup(client).json()["access_token"]
    child = client.post(
        "/api/children",
        json={"nickname": "Maya", "date_of_birth": "2026-01-01"},
        headers=auth_headers(token),
    ).json()
    client.post(
        f"/api/children/{child['id']}/screenings",
        json={"age_label": "9 months", "answers": []},
        headers=auth_headers(token),
    )

    summary = client.get("/api/analytics/summary").json()
    dumped = str(summary)
    assert "parent@example.com" not in dumped
    assert "Maya" not in dumped
    assert "child_id" not in dumped
    assert "user_id" not in dumped
    for row in summary["by_age_and_band"]:
        assert set(row.keys()) == {"age_label", "band", "count"}
