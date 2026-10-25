"""Deterministic red-flag rules engine.

Hard rule 2 (Agents.md): red flags come ONLY from this file + data/milestones.json.
An LLM agent may extract answers, explain results, and chat — it must never add,
remove, or downgrade a flag that this module computes.

NOTE on thresholds: the banding logic below (how many "not yet"/"not sure" answers
tip a session from "Doing well" into "Worth watching" or "Talk to your doctor soon")
is a draft heuristic for this prototype, not a clinically validated scoring system.
Per Agents.md -> "Milestone content & clinical review", this must be reviewed and
signed off by a pediatric professional before any real use.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
MILESTONES_PATH = DATA_DIR / "milestones.json"

Answer = Literal["yes", "sometimes", "not_yet", "not_sure"]
Band = Literal["doing_well", "worth_watching", "talk_to_doctor_soon"]

BAND_LABELS: dict[Band, str] = {
    "doing_well": "Doing well",
    "worth_watching": "Worth watching",
    "talk_to_doctor_soon": "Talk to your doctor soon",
}

DISCLAIMER = (
    "This is a screening aid, not a medical diagnosis. Only a doctor can diagnose a "
    "developmental condition — if anything here concerns you, trust that instinct and "
    "reach out to your child's doctor."
)


class MilestoneAnswer(BaseModel):
    milestone_id: str
    domain: str
    text: str
    answer: Answer
    regression: bool = False  # parent indicates the child used to do this and stopped


class ScreeningResult(BaseModel):
    band: Band
    band_label: str
    flagged: list[MilestoneAnswer]
    regression_detected: bool
    home_tips: list[str]
    next_step: str
    disclaimer: str = DISCLAIMER


_milestones_cache: dict | None = None


def _load_milestones() -> dict:
    global _milestones_cache
    if _milestones_cache is None:
        with MILESTONES_PATH.open(encoding="utf-8") as f:
            _milestones_cache = json.load(f)
    return _milestones_cache


def list_age_labels() -> list[str]:
    return [a["age_label"] for a in _load_milestones()["ages"]]


def get_age_entry(age_label: str) -> dict:
    for age in _load_milestones()["ages"]:
        if age["age_label"] == age_label:
            return age
    raise ValueError(f"No milestone data for age_label={age_label!r}")


def score_screening(answers: list[MilestoneAnswer]) -> ScreeningResult:
    """Apply the (draft, pending clinical review) flagging rules to a set of answers."""
    flagged = [a for a in answers if a.answer in ("not_yet", "not_sure")]
    regression = any(a.regression for a in answers)

    # Hard rule 5: regression is always high-priority, regardless of age or how
    # many other milestones were met.
    if regression:
        band: Band = "talk_to_doctor_soon"
    elif len(flagged) >= 2:
        band = "talk_to_doctor_soon"
    elif len(flagged) == 1:
        band = "worth_watching"
    else:
        band = "doing_well"

    return ScreeningResult(
        band=band,
        band_label=BAND_LABELS[band],
        flagged=flagged,
        regression_detected=regression,
        home_tips=_home_tips_for(band),
        next_step=_next_step_for(band),
    )


def _home_tips_for(band: Band) -> list[str]:
    if band == "doing_well":
        return [
            "Keep reading, talking, and playing with your child every day — it's one of the best ways to support development.",
            "Celebrate the new things your child is learning to do.",
        ]
    if band == "worth_watching":
        return [
            "Keep practicing the skill(s) your child hasn't shown yet through everyday play.",
            "Check back on this in a few weeks to see if anything has changed.",
            "Mention it at your next well-child visit.",
        ]
    return [
        "Write down what you've noticed so it's easy to describe to the doctor.",
        "Don't wait for the next scheduled visit — call and ask about developmental screening soon.",
    ]


def _next_step_for(band: Band) -> str:
    if band == "doing_well":
        return "No action needed right now — keep an eye on new milestones as they come up."
    if band == "worth_watching":
        return "Mention this at your child's next well-child visit."
    return "Call your child's doctor soon and ask about a developmental screening."
