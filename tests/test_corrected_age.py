"""Tests for backend/corrected_age.py.

Covers: full-term, premature within the correction window, premature past
the 24-month cutoff, and the 37-week boundary itself.
"""

import sys
from datetime import date
from pathlib import Path

import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.corrected_age import CorrectedAgeInput, calculate_corrected_age


def test_full_term_infant_no_correction():
    data = CorrectedAgeInput(
        date_of_birth=date(2026, 1, 1),
        gestational_age_weeks=40,
        as_of_date=date(2026, 7, 1),
    )
    result = calculate_corrected_age(data)
    assert result.is_premature is False
    assert result.weeks_premature == 0
    assert result.correction_applies is False
    assert result.corrected_age_days == result.chronological_age_days


def test_37_weeks_is_not_premature():
    data = CorrectedAgeInput(
        date_of_birth=date(2026, 1, 1),
        gestational_age_weeks=37,
        as_of_date=date(2026, 4, 1),
    )
    result = calculate_corrected_age(data)
    assert result.is_premature is False
    assert result.correction_applies is False


def test_premature_infant_within_correction_window():
    # Born at 32 weeks -> 8 weeks premature; 6 months chronological age.
    data = CorrectedAgeInput(
        date_of_birth=date(2026, 1, 1),
        gestational_age_weeks=32,
        as_of_date=date(2026, 7, 1),
    )
    result = calculate_corrected_age(data)
    assert result.is_premature is True
    assert result.weeks_premature == 8
    assert result.correction_applies is True
    assert result.corrected_age_days == result.chronological_age_days - 8 * 7
    assert result.corrected_age_months < result.chronological_age_months


def test_premature_infant_past_24_month_cutoff():
    # Born at 28 weeks, but the child is now 3 years old -> no correction.
    data = CorrectedAgeInput(
        date_of_birth=date(2023, 1, 1),
        gestational_age_weeks=28,
        as_of_date=date(2026, 1, 1),
    )
    result = calculate_corrected_age(data)
    assert result.is_premature is True
    assert result.correction_applies is False
    assert result.corrected_age_days == result.chronological_age_days


def test_corrected_age_never_goes_negative():
    # Born extremely premature, very shortly after birth.
    data = CorrectedAgeInput(
        date_of_birth=date(2026, 1, 1),
        gestational_age_weeks=24,
        as_of_date=date(2026, 1, 15),
    )
    result = calculate_corrected_age(data)
    assert result.corrected_age_days >= 0


def test_as_of_date_before_birth_is_rejected():
    with pytest.raises(ValidationError):
        CorrectedAgeInput(
            date_of_birth=date(2026, 1, 1),
            gestational_age_weeks=40,
            as_of_date=date(2025, 1, 1),
        )


def test_gestational_age_out_of_range_is_rejected():
    with pytest.raises(ValidationError):
        CorrectedAgeInput(
            date_of_birth=date(2026, 1, 1),
            gestational_age_weeks=10,
            as_of_date=date(2026, 7, 1),
        )
