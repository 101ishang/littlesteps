# Growth chart data

Official percentile/LMS data files, downloaded verbatim (not transcribed or edited) from the U.S. government sources named below. These are **not milestone checklists** — they're curve-fitting parameters (L, M, S + percentile columns) used to compute a child's percentile for weight, length/stature, head circumference, and BMI, given their age/sex and a measurement.

## `cdc/` — CDC growth charts, ages 2–20 years (and birth–36 months)

Source: https://www.cdc.gov/growthcharts/cdc-data-files.htm (CDC/NCHS, unchanged since original 2000 release; BMI extension added later — see `bmiagerev.csv`).

| File | Measurement | Age range |
|---|---|---|
| `wtage.csv` | Weight-for-age | 2–20 years |
| `statage.csv` | Stature-for-age | 2–20 years |
| `bmiagerev.csv` | BMI-for-age | 2–20 years |
| `wtageinf.csv` | Weight-for-age | Birth–36 months |
| `lenageinf.csv` | Length-for-age (recumbent) | Birth–36 months |
| `wtleninf.csv` | Weight-for-recumbent-length | Birth–36 months |
| `hcageinf.csv` | Head circumference-for-age | Birth–36 months |
| `wtstat.csv` | Weight-for-stature | — |

Each file covers both sexes (`Sex` column: 1 = male, 2 = female) by single month of age (or length/stature, for the two length/stature-indexed files).

## `who/` — WHO growth charts, birth–24 months

Source: https://www.cdc.gov/growthcharts/who-data-files.htm (CDC-hosted copy of WHO child growth standards). CDC/AAP guidance is to use the WHO charts for ages 0–2 and the CDC charts from age 2 onward.

| File | Measurement |
|---|---|
| `WHO-{Boys,Girls}-Weight-for-age-Percentiles.csv` | Weight-for-age |
| `WHO-{Boys,Girls}-Length-for-age-Percentiles.csv` | Length-for-age |
| `WHO-{Boys,Girls}-Weight-for-length-Percentiles.csv` | Weight-for-length |
| `WHO-{Boys,Girls}-Head-Circumference-for-age-Percentiles.csv` | Head circumference-for-age |

## How this should be used

This is reference data for a percentile/z-score calculation (e.g. via the L/M/S columns), not something to paste into the UI as-is. `backend/rules.py` (or a dedicated growth module) should compute a child's percentile from these tables rather than hardcoding thresholds — standard red flags to encode include: measurement below the 3rd or above the 97th percentile, or a significant percentile-line crossing over time. Confirm exact thresholds with a pediatric professional per the "Milestone content & clinical review" gate in `Agents.md` before using this in any real screening.
