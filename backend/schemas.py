"""Pydantic request/response models for auth, children, and screening history.

None of these ever include a password or password_hash field — see
backend/auth.py's module docstring.
"""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, EmailStr, Field

from backend.rules import Band, MilestoneAnswer, ScreeningResult


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, description="At least 8 characters.")


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    email: EmailStr
    created_at: datetime

    model_config = {"from_attributes": True}


class ChildCreate(BaseModel):
    nickname: str = Field(..., min_length=1, max_length=50)
    date_of_birth: date
    gestational_age_weeks: int | None = Field(None, ge=20, le=44)


class ChildOut(BaseModel):
    id: int
    nickname: str
    date_of_birth: date
    gestational_age_weeks: int | None

    model_config = {"from_attributes": True}


class ScreeningSubmission(BaseModel):
    age_label: str
    corrected_age_months: float | None = None
    answers: list[MilestoneAnswer]


class AIExplanationOut(BaseModel):
    """The explainer+safety-reviewer agent pair's output — see backend/agents.py.

    This is supporting prose only; `used_fallback`/`safety_passed` tell the
    frontend (and the report) whether a real LLM explanation was shown or the
    app fell back to safe, non-generated text.
    """

    summary: str
    encouragement: str
    used_fallback: bool
    safety_passed: bool | None


class ScreenResponse(BaseModel):
    result: ScreeningResult
    ai: AIExplanationOut


class ScreeningRecordOut(BaseModel):
    id: int
    created_at: datetime
    age_label: str
    corrected_age_months: float | None
    band: Band
    regression_detected: bool
    flagged_count: int
    ai_summary: str | None
    ai_encouragement: str | None
    ai_used_fallback: bool
