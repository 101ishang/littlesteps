"""Tests for backend/growth_percentiles.py.

Validates the LMS math itself, chart selection (WHO <24mo / CDC >=24mo),
and known reference points: the M value at a given age/sex should always
compute to (very close to) the 50th percentile, since M is defined as the
median in the LMS model.
"""

import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.growth_percentiles import (
    GrowthInput,
    calculate_growth_percentile,
    lms_zscore,
    zscore_to_percentile,
)


def test_lms_zscore_at_median_is_zero():
    # When x == M, the z-score should be 0 regardless of L (as long as L != 0 edge case for log path too).
    assert lms_zscore(10.0, l=1.5, m=10.0, s=0.1) == pytest.approx(0.0, abs=1e-9)
    assert lms_zscore(10.0, l=0.0, m=10.0, s=0.1) == pytest.approx(0.0, abs=1e-9)


def test_zscore_to_percentile_midpoint():
    assert zscore_to_percentile(0.0) == pytest.approx(50.0, abs=1e-6)


def test_who_weight_for_age_median_is_50th_percentile():
    # WHO boys weight-for-age at 0 months: M = 3.3464 (see data/growth/who/...).
    data = GrowthInput(sex="male", measurement="weight_for_age", age_months=0, value=3.3464)
    result = calculate_growth_percentile(data)
    assert result.chart_source == "who_weight_for_age"
    assert result.percentile == pytest.approx(50.0, abs=0.5)
    assert result.flag is None


def test_cdc_weight_for_age_used_at_24_months_and_above():
    data = GrowthInput(sex="female", measurement="weight_for_age", age_months=24, value=12.0)
    result = calculate_growth_percentile(data)
    assert result.chart_source == "cdc_weight_for_age"


def test_who_used_below_24_months_for_length():
    data = GrowthInput(sex="male", measurement="length_or_stature_for_age", age_months=12, value=75.0)
    result = calculate_growth_percentile(data)
    assert result.chart_source == "who_length_for_age"


def test_cdc_used_at_and_above_24_months_for_stature():
    data = GrowthInput(sex="male", measurement="length_or_stature_for_age", age_months=24, value=87.0)
    result = calculate_growth_percentile(data)
    assert result.chart_source == "cdc_stature_for_age"


def test_very_low_weight_flags_below_3rd_percentile():
    # A tiny value well below the median should flag low.
    data = GrowthInput(sex="male", measurement="weight_for_age", age_months=12, value=0.5)
    result = calculate_growth_percentile(data)
    assert result.flag == "below_3rd_percentile"
    assert result.percentile < 3


def test_very_high_weight_flags_above_97th_percentile():
    data = GrowthInput(sex="male", measurement="weight_for_age", age_months=12, value=50.0)
    result = calculate_growth_percentile(data)
    assert result.flag == "above_97th_percentile"
    assert result.percentile > 97


def test_bmi_under_24_months_is_rejected():
    data = GrowthInput(sex="male", measurement="bmi_for_age", age_months=12, value=16.0)
    with pytest.raises(ValueError):
        calculate_growth_percentile(data)


def test_weight_for_length_requires_recumbent_flag():
    with pytest.raises(ValidationError):
        GrowthInput(
            sex="male",
            measurement="weight_for_length_or_stature",
            length_or_stature_cm=70.0,
            value=8.0,
        )


def test_weight_for_length_recumbent_uses_who():
    data = GrowthInput(
        sex="female",
        measurement="weight_for_length_or_stature",
        length_or_stature_cm=70.0,
        recumbent=True,
        value=8.5,
    )
    result = calculate_growth_percentile(data)
    assert result.chart_source == "who_weight_for_length"


def test_weight_for_stature_non_recumbent_uses_cdc():
    data = GrowthInput(
        sex="female",
        measurement="weight_for_length_or_stature",
        length_or_stature_cm=90.0,
        recumbent=False,
        value=13.0,
    )
    result = calculate_growth_percentile(data)
    assert result.chart_source == "cdc_weight_for_stature"


def test_out_of_range_age_clamps_to_edge_and_flags_it():
    # 25 years old is far beyond any chart; should clamp to the oldest row, not crash.
    data = GrowthInput(sex="male", measurement="weight_for_age", age_months=300, value=70.0)
    result = calculate_growth_percentile(data)
    assert result.out_of_chart_range is True


def test_head_circumference_beyond_36_months_raises_at_calculation():
    # age_months=48 alone is valid Pydantic input; the 36-month chart limit
    # is enforced during chart selection in calculate_growth_percentile, not construction.
    data = GrowthInput(sex="male", measurement="head_circumference_for_age", age_months=48, value=50.0)
    with pytest.raises(ValueError):
        calculate_growth_percentile(data)
