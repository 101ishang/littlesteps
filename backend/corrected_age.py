"""Corrected (adjusted) age for premature infants.

Hard rule (Agents.md): always use corrected age, not chronological age, for
children born before 37 weeks gestation, until the child turns 2 years old.

AAP/CDC guidance: subtract the number of weeks premature (40 minus
gestational age at birth) from the chronological age, and only while the
child is under 24 months chronological age. At or after 37 weeks gestation,
or once the child reaches 24 months, use chronological age unchanged.
"""

from __future__ import annotations

import argparse
from datetime import date, datetime

from pydantic import BaseModel, Field, model_validator

FULL_TERM_WEEKS = 40
PREMATURE_THRESHOLD_WEEKS = 37  # born before this many weeks counts as premature
CORRECTION_CUTOFF_MONTHS = 24  # stop correcting once the child reaches this age
DAYS_PER_MONTH = 30.4375  # average month length (365.25 / 12)


class CorrectedAgeInput(BaseModel):
    """Input for a corrected-age calculation."""

    date_of_birth: date
    gestational_age_weeks: int = Field(
        ..., ge=20, le=44, description="Gestational age at birth, in completed weeks."
    )
    as_of_date: date = Field(default_factory=date.today)

    @model_validator(mode="after")
    def check_as_of_not_before_birth(self) -> "CorrectedAgeInput":
        if self.as_of_date < self.date_of_birth:
            raise ValueError("as_of_date cannot be before date_of_birth")
        return self


class CorrectedAgeResult(BaseModel):
    """Result of a corrected-age calculation."""

    chronological_age_days: int
    chronological_age_months: float
    is_premature: bool
    weeks_premature: int
    correction_applies: bool
    corrected_age_days: int
    corrected_age_months: float


def calculate_corrected_age(data: CorrectedAgeInput) -> CorrectedAgeResult:
    """Compute a child's corrected age for use with milestone screening."""
    chronological_age_days = (data.as_of_date - data.date_of_birth).days
    chronological_age_months = chronological_age_days / DAYS_PER_MONTH

    is_premature = data.gestational_age_weeks < PREMATURE_THRESHOLD_WEEKS
    weeks_premature = max(FULL_TERM_WEEKS - data.gestational_age_weeks, 0)

    correction_applies = is_premature and chronological_age_months < CORRECTION_CUTOFF_MONTHS

    if correction_applies:
        corrected_age_days = max(chronological_age_days - weeks_premature * 7, 0)
    else:
        corrected_age_days = chronological_age_days

    corrected_age_months = corrected_age_days / DAYS_PER_MONTH

    return CorrectedAgeResult(
        chronological_age_days=chronological_age_days,
        chronological_age_months=round(chronological_age_months, 2),
        is_premature=is_premature,
        weeks_premature=weeks_premature,
        correction_applies=correction_applies,
        corrected_age_days=corrected_age_days,
        corrected_age_months=round(corrected_age_months, 2),
    )


def _parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Calculate a child's corrected (adjusted) age for premature birth."
    )
    parser.add_argument("date_of_birth", type=_parse_date, help="Child's date of birth, YYYY-MM-DD")
    parser.add_argument(
        "gestational_age_weeks",
        type=int,
        help="Gestational age at birth, in completed weeks (e.g. 32)",
    )
    parser.add_argument(
        "--as-of",
        type=_parse_date,
        default=None,
        help="Date to calculate the age as of (default: today), YYYY-MM-DD",
    )
    args = parser.parse_args()

    data = CorrectedAgeInput(
        date_of_birth=args.date_of_birth,
        gestational_age_weeks=args.gestational_age_weeks,
        **({"as_of_date": args.as_of} if args.as_of else {}),
    )
    result = calculate_corrected_age(data)

    print(f"Chronological age: {result.chronological_age_days} days "
          f"({result.chronological_age_months} months)")
    if result.is_premature:
        print(f"Born {result.weeks_premature} weeks premature "
              f"(gestational age: {data.gestational_age_weeks} weeks)")
    else:
        print("Born at or after 37 weeks gestation — not considered premature")

    if result.correction_applies:
        print(f"Corrected age: {result.corrected_age_days} days "
              f"({result.corrected_age_months} months) — use this for milestone screening")
    else:
        print("Corrected age does not apply — use chronological age for milestone screening "
              "(either born at term, or child is 24+ months old)")


if __name__ == "__main__":
    main()
