"""Growth percentile / z-score calculation from official CDC and WHO growth chart data.

Standard LMS formula used by both CDC and WHO growth charts:

    Z = (((X / M) ** L) - 1) / (L * S)      if L != 0
    Z = ln(X / M) / S                       if L == 0

Percentile = Phi(Z) * 100, where Phi is the standard normal CDF.

Per data/growth/README.md: use the WHO charts for ages 0-2 years and the CDC
charts from age 2 onward. This module computes from the official LMS data
files downloaded verbatim into data/growth/ (see that README for exact
source files/URLs) — it does not hardcode any growth figures itself.
"""

from __future__ import annotations

import argparse
import csv
import math
from dataclasses import dataclass
from pathlib import Path
from statistics import NormalDist
from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "growth"

Sex = Literal["male", "female"]
Measurement = Literal[
    "weight_for_age",
    "length_or_stature_for_age",
    "head_circumference_for_age",
    "bmi_for_age",
    "weight_for_length_or_stature",
]

_NORMAL = NormalDist()
LOW_PERCENTILE_Z = _NORMAL.inv_cdf(0.03)  # z-score at the 3rd percentile (~ -1.8808)
HIGH_PERCENTILE_Z = _NORMAL.inv_cdf(0.97)  # z-score at the 97th percentile (~ +1.8808)


def lms_zscore(x: float, l: float, m: float, s: float) -> float:
    """Standard LMS z-score formula used by CDC and WHO growth charts."""
    if abs(l) < 1e-9:
        return math.log(x / m) / s
    return ((x / m) ** l - 1) / (l * s)


def zscore_to_percentile(z: float) -> float:
    """Convert a z-score to a percentile (0-100) via the standard normal CDF."""
    return _NORMAL.cdf(z) * 100


@dataclass
class LMSRow:
    x: float
    l: float
    m: float
    s: float


def _load_lms_rows(
    path: Path, x_col: str, sex_col: Optional[str] = None, sex_value: Optional[str] = None
) -> list[LMSRow]:
    rows: list[LMSRow] = []
    with path.open(newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            if sex_col is not None and row.get(sex_col) != sex_value:
                continue
            rows.append(
                LMSRow(x=float(row[x_col]), l=float(row["L"]), m=float(row["M"]), s=float(row["S"]))
            )
    rows.sort(key=lambda r: r.x)
    return rows


def _interpolate(rows: list[LMSRow], x: float) -> tuple[LMSRow, bool]:
    """Linearly interpolate L/M/S at x. Returns (row, out_of_range)."""
    if not rows:
        raise ValueError("No LMS rows available for this chart")
    if x <= rows[0].x:
        return rows[0], x < rows[0].x
    if x >= rows[-1].x:
        return rows[-1], x > rows[-1].x
    for a, b in zip(rows, rows[1:]):
        if a.x <= x <= b.x:
            t = 0.0 if b.x == a.x else (x - a.x) / (b.x - a.x)
            return (
                LMSRow(x=x, l=a.l + t * (b.l - a.l), m=a.m + t * (b.m - a.m), s=a.s + t * (b.s - a.s)),
                False,
            )
    raise ValueError(f"Could not bracket x={x} in chart data")


@dataclass
class ChartRef:
    path: Path
    x_col: str
    x_value: float
    source_label: str
    sex_col: Optional[str] = None
    sex_value: Optional[str] = None


def _select_chart(
    measurement: Measurement,
    sex: Sex,
    age_months: Optional[float],
    length_or_stature_cm: Optional[float],
    recumbent: Optional[bool],
) -> ChartRef:
    sex_name = "Boys" if sex == "male" else "Girls"
    cdc_sex_code = "1" if sex == "male" else "2"

    if measurement == "weight_for_age":
        if age_months is None:
            raise ValueError("age_months is required for weight_for_age")
        if age_months < 24:
            path = DATA_DIR / "who" / f"WHO-{sex_name}-Weight-for-age-Percentiles.csv"
            return ChartRef(path, "Month", age_months, "who_weight_for_age")
        path = DATA_DIR / "cdc" / "wtage.csv"
        return ChartRef(path, "Agemos", age_months, "cdc_weight_for_age", "Sex", cdc_sex_code)

    if measurement == "length_or_stature_for_age":
        if age_months is None:
            raise ValueError("age_months is required for length_or_stature_for_age")
        if age_months < 24:
            path = DATA_DIR / "who" / f"WHO-{sex_name}-Length-for-age-Percentiles.csv"
            return ChartRef(path, "Month", age_months, "who_length_for_age")
        path = DATA_DIR / "cdc" / "statage.csv"
        return ChartRef(path, "Agemos", age_months, "cdc_stature_for_age", "Sex", cdc_sex_code)

    if measurement == "head_circumference_for_age":
        if age_months is None:
            raise ValueError("age_months is required for head_circumference_for_age")
        if age_months < 24:
            path = DATA_DIR / "who" / f"WHO-{sex_name}-Head-Circumference-for-age-Percentiles.csv"
            return ChartRef(path, "Month", age_months, "who_head_circumference_for_age")
        if age_months <= 36:
            path = DATA_DIR / "cdc" / "hcageinf.csv"
            return ChartRef(path, "Agemos", age_months, "cdc_head_circumference_for_age", "Sex", cdc_sex_code)
        raise ValueError(
            "No downloaded head-circumference chart covers ages beyond 36 months "
            "(CDC/WHO head-circumference charts only go to 36 months)"
        )

    if measurement == "bmi_for_age":
        if age_months is None:
            raise ValueError("age_months is required for bmi_for_age")
        if age_months < 24:
            raise ValueError(
                "BMI-for-age is not used under 24 months; use weight_for_length_or_stature instead"
            )
        path = DATA_DIR / "cdc" / "bmiagerev.csv"
        return ChartRef(path, "Agemos", age_months, "cdc_bmi_for_age", "Sex", cdc_sex_code)

    if measurement == "weight_for_length_or_stature":
        if length_or_stature_cm is None or recumbent is None:
            raise ValueError(
                "length_or_stature_cm and recumbent are required for weight_for_length_or_stature"
            )
        if recumbent:
            path = DATA_DIR / "who" / f"WHO-{sex_name}-Weight-for-length-Percentiles.csv"
            return ChartRef(path, "Length", length_or_stature_cm, "who_weight_for_length")
        path = DATA_DIR / "cdc" / "wtstat.csv"
        return ChartRef(path, "Height", length_or_stature_cm, "cdc_weight_for_stature", "Sex", cdc_sex_code)

    raise ValueError(f"Unknown measurement: {measurement}")


class GrowthInput(BaseModel):
    """Input for a growth percentile calculation."""

    sex: Sex
    measurement: Measurement
    value: float = Field(..., description="The measured value: kg for weight, cm for length/stature/head circumference, kg/m^2 for BMI.")
    age_months: Optional[float] = Field(None, ge=0, description="Required for *_for_age measurements.")
    length_or_stature_cm: Optional[float] = Field(None, gt=0, description="Required for weight_for_length_or_stature.")
    recumbent: Optional[bool] = Field(
        None,
        description="For weight_for_length_or_stature: True = recumbent length (WHO, typically <2y), "
        "False = standing stature (CDC). Required for that measurement.",
    )

    @model_validator(mode="after")
    def check_required_fields(self) -> "GrowthInput":
        if self.measurement == "weight_for_length_or_stature":
            if self.length_or_stature_cm is None or self.recumbent is None:
                raise ValueError(
                    "length_or_stature_cm and recumbent are required for weight_for_length_or_stature"
                )
        elif self.age_months is None:
            raise ValueError(f"age_months is required for {self.measurement}")
        return self


class GrowthResult(BaseModel):
    """Result of a growth percentile calculation."""

    measurement: Measurement
    chart_source: str = Field(..., description="Which chart/file this was computed from, e.g. 'who_weight_for_age'.")
    x_value: float = Field(..., description="The age (months) or length/stature (cm) used to look up L/M/S.")
    l: float
    m: float
    s: float
    z_score: float
    percentile: float
    out_of_chart_range: bool = Field(
        ..., description="True if x_value fell outside the chart's data and the nearest edge row was used."
    )
    flag: Optional[Literal["below_3rd_percentile", "above_97th_percentile"]] = None


def calculate_growth_percentile(data: GrowthInput) -> GrowthResult:
    """Compute a z-score and percentile for a growth measurement from official LMS data."""
    chart = _select_chart(
        data.measurement, data.sex, data.age_months, data.length_or_stature_cm, data.recumbent
    )
    rows = _load_lms_rows(chart.path, chart.x_col, chart.sex_col, chart.sex_value)
    lms, out_of_range = _interpolate(rows, chart.x_value)

    z = lms_zscore(data.value, lms.l, lms.m, lms.s)
    percentile = zscore_to_percentile(z)

    flag = None
    if z < LOW_PERCENTILE_Z:
        flag = "below_3rd_percentile"
    elif z > HIGH_PERCENTILE_Z:
        flag = "above_97th_percentile"

    return GrowthResult(
        measurement=data.measurement,
        chart_source=chart.source_label,
        x_value=chart.x_value,
        l=round(lms.l, 6),
        m=round(lms.m, 6),
        s=round(lms.s, 6),
        z_score=round(z, 4),
        percentile=round(percentile, 2),
        out_of_chart_range=out_of_range,
        flag=flag,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute a growth percentile from CDC/WHO LMS data.")
    parser.add_argument("sex", choices=["male", "female"])
    parser.add_argument(
        "measurement",
        choices=[
            "weight_for_age",
            "length_or_stature_for_age",
            "head_circumference_for_age",
            "bmi_for_age",
            "weight_for_length_or_stature",
        ],
    )
    parser.add_argument("value", type=float, help="Measured value (kg, cm, or kg/m^2 depending on measurement)")
    parser.add_argument("--age-months", type=float, default=None)
    parser.add_argument("--length-or-stature-cm", type=float, default=None)
    parser.add_argument(
        "--recumbent",
        type=lambda s: s.lower() in ("1", "true", "yes"),
        default=None,
        help="true/false — required for weight_for_length_or_stature",
    )
    args = parser.parse_args()

    data = GrowthInput(
        sex=args.sex,
        measurement=args.measurement,
        value=args.value,
        age_months=args.age_months,
        length_or_stature_cm=args.length_or_stature_cm,
        recumbent=args.recumbent,
    )
    result = calculate_growth_percentile(data)

    print(f"Chart: {result.chart_source} (x = {result.x_value})")
    print(f"L={result.l}, M={result.m}, S={result.s}")
    print(f"Z-score: {result.z_score}")
    print(f"Percentile: {result.percentile}")
    if result.out_of_chart_range:
        print("WARNING: input was outside the chart's data range; nearest edge values were used.")
    if result.flag:
        print(f"FLAG: {result.flag}")


if __name__ == "__main__":
    main()
