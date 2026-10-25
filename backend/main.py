"""FastAPI app wiring the prototype's deterministic pieces together.

This prototype runs without an LLM: milestone content is read straight from
data/milestones.json and flagging comes straight from backend/rules.py, per
Hard rule 2. The PydanticAI agents described in Agents.md (boss/coordinator,
domain workers, screening-report, safety reviewer) would sit in front of
this for the explanation/chat layer — this API is their deterministic
foundation, now with accounts and screening history on top of it.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func
from sqlalchemy.orm import Session

load_dotenv()  # reads AI_finals_project/.env if present; see Agents.md -> Secrets

from backend.agents import generate_explanation
from backend.auth import (
    create_access_token,
    generate_password_reset_token,
    get_current_user,
    hash_password,
    hash_reset_token,
    utcnow_naive,
    verify_password,
)
from backend.corrected_age import CorrectedAgeInput, CorrectedAgeResult, calculate_corrected_age
from backend.db import AnalyticsEvent, Child, PasswordResetToken, ScreeningRecord, User, get_db, init_db
from backend.growth_percentiles import GrowthInput, GrowthResult, calculate_growth_percentile
from backend.rules import get_age_entry, list_age_labels, score_screening
from backend.schemas import (
    AIExplanationOut,
    ChildCreate,
    ChildOut,
    ForgotPasswordRequest,
    LoginRequest,
    MessageResponse,
    ResetPasswordRequest,
    ScreenResponse,
    ScreeningRecordOut,
    ScreeningSubmission,
    SignupRequest,
    TokenResponse,
    UserOut,
)

# No email service is wired up (the course key restricts env vars to
# PORTKEY_API_KEY/OPENAI_API_KEY — see Agents.md -> Secrets), so for this
# prototype the "email" is logged to the server console instead of actually
# sent. The security model is otherwise exactly what a real email-backed flow
# would use (single-use, hashed, expiring token; generic response either way).
# FRONTEND_URL is only used to build that reset link — in production (single
# origin, see the static-file mount below) it should be set to the app's own
# deployed URL; locally it defaults to the Vite dev server.
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173")

FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Imprint — Developmental Screening Aid (prototype API)", lifespan=lifespan)

# Needed for local dev only, where the Vite dev server (5173) and the API
# (8000) are different origins. In production the frontend is served by this
# same app (see the StaticFiles mount at the bottom of this file), so these
# requests are same-origin and CORS doesn't apply to them at all.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL, "http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


@app.post("/api/auth/signup", response_model=TokenResponse, status_code=201)
def signup(req: SignupRequest, db: Session = Depends(get_db)) -> TokenResponse:
    existing = db.query(User).filter(User.email == req.email).first()
    if existing is not None:
        raise HTTPException(status_code=409, detail="An account with this email already exists")
    user = User(email=req.email, password_hash=hash_password(req.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return TokenResponse(access_token=create_access_token(user.id))


@app.post("/api/auth/login", response_model=TokenResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.query(User).filter(User.email == req.email).first()
    if user is None or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    return TokenResponse(access_token=create_access_token(user.id))


@app.get("/api/auth/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


_GENERIC_FORGOT_PASSWORD_MESSAGE = (
    "If an account exists for that email, a password reset link has been sent."
)


@app.post("/api/auth/forgot-password", response_model=MessageResponse)
def forgot_password(req: ForgotPasswordRequest, db: Session = Depends(get_db)) -> MessageResponse:
    """Always returns the same generic message, whether or not the email exists.

    This prevents using this endpoint to check which emails have an account
    (user enumeration) — Hard rule 9 / Agents.md's data-minimization spirit
    applied to auth, not just child data.
    """
    user = db.query(User).filter(User.email == req.email).first()
    if user is not None:
        raw_token, token_hash, expires_at = generate_password_reset_token()
        db.add(PasswordResetToken(user_id=user.id, token_hash=token_hash, expires_at=expires_at))
        db.commit()
        reset_link = f"{FRONTEND_URL}/?reset_token={raw_token}"
        # Stand-in for sending a real email (see this module's FRONTEND_URL comment).
        # print(), not logger.info(): uvicorn's default logging config filters out
        # plain app-level INFO records, and this needs to be unmissable in dev.
        print(f"\n===== PASSWORD RESET (dev mode — this would be emailed) =====\n"
              f"user_id={user.id}\nReset link: {reset_link}\n"
              f"================================================================\n")
    return MessageResponse(message=_GENERIC_FORGOT_PASSWORD_MESSAGE)


@app.post("/api/auth/reset-password", response_model=MessageResponse)
def reset_password(req: ResetPasswordRequest, db: Session = Depends(get_db)) -> MessageResponse:
    token_hash = hash_reset_token(req.token)
    reset_token = db.query(PasswordResetToken).filter(PasswordResetToken.token_hash == token_hash).first()

    invalid = (
        reset_token is None
        or reset_token.used_at is not None
        or reset_token.expires_at < utcnow_naive()
    )
    if invalid:
        raise HTTPException(status_code=400, detail="This reset link is invalid or has expired.")

    user = db.get(User, reset_token.user_id)
    if user is None:
        raise HTTPException(status_code=400, detail="This reset link is invalid or has expired.")

    user.password_hash = hash_password(req.new_password)
    reset_token.used_at = utcnow_naive()
    db.commit()
    return MessageResponse(message="Your password has been reset. You can now log in.")


# ---------------------------------------------------------------------------
# Children
# ---------------------------------------------------------------------------


def _get_owned_child(child_id: int, current_user: User, db: Session) -> Child:
    child = db.get(Child, child_id)
    if child is None or child.user_id != current_user.id:
        # Same 404 whether the child doesn't exist or belongs to someone else,
        # so this endpoint can't be used to probe which child IDs exist.
        raise HTTPException(status_code=404, detail="Child not found")
    return child


@app.post("/api/children", response_model=ChildOut, status_code=201)
def create_child(
    req: ChildCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> Child:
    child = Child(user_id=current_user.id, **req.model_dump())
    db.add(child)
    db.commit()
    db.refresh(child)
    return child


@app.get("/api/children", response_model=list[ChildOut])
def list_children(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[Child]:
    return db.query(Child).filter(Child.user_id == current_user.id).order_by(Child.created_at).all()


# ---------------------------------------------------------------------------
# Milestones / corrected age / growth (unchanged, no auth needed — reference data)
# ---------------------------------------------------------------------------


@app.get("/api/ages")
def api_list_ages() -> list[str]:
    return list_age_labels()


@app.get("/api/milestones/{age_label}")
def api_get_milestones(age_label: str) -> dict:
    try:
        return get_age_entry(age_label)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/corrected-age", response_model=CorrectedAgeResult)
def api_corrected_age(data: CorrectedAgeInput) -> CorrectedAgeResult:
    try:
        return calculate_corrected_age(data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/growth", response_model=GrowthResult)
def api_growth(data: GrowthInput) -> GrowthResult:
    try:
        return calculate_growth_percentile(data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Screenings (tied to a child, kept for trend tracking) + anonymized analytics
# ---------------------------------------------------------------------------


@app.post("/api/children/{child_id}/screenings", response_model=ScreenResponse, status_code=201)
async def submit_screening(
    child_id: int,
    req: ScreeningSubmission,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ScreenResponse:
    child = _get_owned_child(child_id, current_user, db)

    result = score_screening(req.answers)
    ai = await generate_explanation(result, child.nickname, req.age_label)

    db.add(
        ScreeningRecord(
            child_id=child_id,
            age_label=req.age_label,
            corrected_age_months=req.corrected_age_months,
            band=result.band,
            regression_detected=result.regression_detected,
            answers=[a.model_dump() for a in req.answers],
            ai_summary=ai.explanation.summary,
            ai_encouragement=ai.explanation.encouragement,
            ai_used_fallback=ai.used_fallback,
        )
    )
    # Anonymized analytics: deliberately no child_id/user_id/email — see backend/db.py.
    # input_tokens/output_tokens/model/ai_used_fallback are this project's real Tokenomics data.
    db.add(
        AnalyticsEvent(
            event_type="screening_completed",
            age_label=req.age_label,
            band=result.band,
            flagged_count=len(result.flagged),
            regression_detected=result.regression_detected,
            input_tokens=ai.input_tokens,
            output_tokens=ai.output_tokens,
            model=ai.model,
            ai_used_fallback=ai.used_fallback,
        )
    )
    db.commit()
    return ScreenResponse(
        result=result,
        ai=AIExplanationOut(
            summary=ai.explanation.summary,
            encouragement=ai.explanation.encouragement,
            used_fallback=ai.used_fallback,
            safety_passed=ai.safety_passed,
        ),
    )


@app.get("/api/children/{child_id}/screenings", response_model=list[ScreeningRecordOut])
def list_screenings(
    child_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[dict]:
    child = _get_owned_child(child_id, current_user, db)
    return [
        ScreeningRecordOut(
            id=s.id,
            created_at=s.created_at,
            age_label=s.age_label,
            corrected_age_months=s.corrected_age_months,
            band=s.band,
            regression_detected=s.regression_detected,
            flagged_count=sum(1 for a in s.answers if a.get("answer") in ("not_yet", "not_sure")),
            ai_summary=s.ai_summary,
            ai_encouragement=s.ai_encouragement,
            ai_used_fallback=s.ai_used_fallback,
        )
        for s in child.screenings
    ]


@app.get("/api/analytics/summary")
def analytics_summary(db: Session = Depends(get_db)) -> dict:
    """Aggregate-only, anonymized stats — see backend/db.py's AnalyticsEvent docstring.

    Demo endpoint for this prototype; a real deployment would likely restrict
    this to an internal/admin audience, but nothing here can identify a user
    or child since AnalyticsEvent never stores either.
    """
    rows = (
        db.query(AnalyticsEvent.age_label, AnalyticsEvent.band, func.count())
        .group_by(AnalyticsEvent.age_label, AnalyticsEvent.band)
        .all()
    )
    total = db.query(func.count(AnalyticsEvent.id)).scalar() or 0

    ai_calls = db.query(AnalyticsEvent).filter(AnalyticsEvent.input_tokens.isnot(None)).all()
    fallback_count = sum(1 for e in ai_calls if e.ai_used_fallback)
    total_input_tokens = sum(e.input_tokens or 0 for e in ai_calls)
    total_output_tokens = sum(e.output_tokens or 0 for e in ai_calls)

    return {
        "total_screenings": total,
        "by_age_and_band": [
            {"age_label": age_label, "band": band, "count": count} for age_label, band, count in rows
        ],
        "tokenomics": {
            "runs_with_ai_explanation": len(ai_calls),
            "runs_that_used_fallback": fallback_count,
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
            "avg_input_tokens_per_run": round(total_input_tokens / len(ai_calls), 1) if ai_calls else None,
            "avg_output_tokens_per_run": round(total_output_tokens / len(ai_calls), 1) if ai_calls else None,
            "model": ai_calls[0].model if ai_calls else None,
            "note": "Token counts are real, measured per-run totals (explainer + safety-reviewer calls combined). Get $ cost per token from your Portkey dashboard for this model/key rather than an estimate here.",
        },
    }


# ---------------------------------------------------------------------------
# Serve the built frontend (production/deployment only)
# ---------------------------------------------------------------------------
# Registered last so it never shadows the /api/* routes above. Locally, run
# the Vite dev server separately instead (see README.md) — this directory
# only exists after `npm run build`. html=True serves index.html for "/",
# which is all this single-page app needs (it has no other real routes; the
# password-reset link uses a query string on "/", not a separate path).
if FRONTEND_DIST.is_dir():
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
