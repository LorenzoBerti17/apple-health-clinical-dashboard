# Apple Health Clinical Dashboard

> Reproducible Python pipeline that ingests an Apple Health export, classifies
> the wearer's data against peer-reviewed clinical benchmarks, and renders a
> single self-contained HTML dashboard.

[![Live demo](https://img.shields.io/badge/live%20demo-GitHub%20Pages-6c8ff8?style=flat-square)](https://lorenzoberti17.github.io/apple-health-clinical-dashboard/) &nbsp;
[![Tests](https://img.shields.io/badge/tests-70%20passing-34d399?style=flat-square)](tests/) &nbsp;
[![License](https://img.shields.io/badge/license-MIT-8b92b8?style=flat-square)](LICENSE)

**Live demo (synthetic data):** https://lorenzoberti17.github.io/apple-health-clinical-dashboard/

---

## The problem

Apple Health's built-in summary lists the same number ten times in ten places,
classifies almost nothing, and asks no questions. As a wearer you end up with
a 500 MB XML file, no idea whether your HRV of 39 ms means you are recovering
or overtrained, and no way to tell whether your VO₂max trend is statistically
real or two months of luck. This project rebuilds the read-side of Apple
Health as a defensible, citable, reproducible analysis.

## The dataset

| | |
|---|---|
| **Source** | Apple Watch (acquired Dec 2025), iPhone fallback ignored |
| **Time window** | 2025-12-01 → 2026-05-01 (151 days) |
| **Raw records parsed** | 563,481 |
| **Sleep records** | 3,740 (143 tracked nights) |
| **Workouts** | 45 runs |
| **Unique signal types** | 36 |

Records prior to 2025-12-01 are filtered out at parse time — they originate
from the iPhone-only era and would contaminate the cardio, sleep and gait
metrics that are watch-exclusive.

## Methodology

Every clinical threshold lives in [`benchmarks.py`](src/health_dashboard/benchmarks.py)
with the originating paper, so the codepath from `value → classification` is
auditable. Full reference list in [`docs/methodology.md`](docs/methodology.md).

| Domain | Threshold(s) used | Source |
|---|---|---|
| Resting HR | < 60 / 60–70 / 70–80 / ≥ 80 bpm | Cardiology consensus |
| HRV (SDNN) | p25 = 40 ms, p50 = 55 ms, p75 = 65 ms (male <30y) | Umetani et al. *J Am Coll Cardiol* 1998; Shaffer & Ginsberg *Front Public Health* 2017 |
| VO₂max | poor < 36 < below avg < 42 < avg < 46 < good < 50 < excellent < 56 ≤ elite | Cooper Institute, 2010 (male 20–29) |
| HR max | 208 − 0.7 × age (preferred over 220 − age) | Tanaka et al. *J Am Coll Cardiol* 2001 |
| HR Recovery (1 min) | ≤ 12 bpm abnormal; > 18 bpm good | Cole et al. *N Engl J Med* 1999 |
| Sleep duration | 7–9 h optimal | Hirshkowitz et al. *Sleep Health* 2015 (NSF); Watson et al. *JCSM* 2015 (AASM) |
| Sleep efficiency | > 85 % | Standard clinical threshold |
| Audio exposure | < 70 dB safe, 85 dB risk > 40h/wk, 100 dB risk > 15 min | WHO *Community Noise Guidelines* 1999 |
| Walking speed | > 1.0 m/s = healthy aging marker | Studenski et al. *JAMA* 2011 |
| BMI | < 18.5 / 25 / 30 | WHO Technical Report 894, 2000 |

### Statistical methods

- **Trend analysis.** Each daily-aggregated series (RHR, HRV, steps) is fit
  with ordinary least squares (`scipy.stats.linregress`). The dashboard
  reports the slope per month plus the p-value so the user can tell whether a
  drift is signal or noise.
- **Correlations.** Pairwise Pearson r across day-aligned signals (e.g. HRV
  vs. RHR), with a minimum-n threshold of 10 to avoid spurious correlations
  on sparse series.
- **Rolling means.** 7-day rolling for noisy daily signals (RHR, HRV, audio,
  walking speed) in the front-end visualisations; the underlying statistics
  always use raw daily aggregates.

### Wire format quirks worth knowing

Validating the pipeline against real export data surfaced several traps that
the Apple Health documentation does not mention:

1. **Cumulative metrics are sub-daily.** `step_count`, `active_energy` and
   `exercise_time` arrive as many small increments per day. Naïve daily mean
   gives 96 steps/day — daily sum gives 12,400. Trivial bug but easy to ship.
2. **`walking_speed` is in km/h, not m/s.** The Apple sample value 4.6
   km/h ≈ 1.28 m/s falls within Studenski's healthy-aging band; without
   conversion the dashboard would flag the wearer as a sub-second sprinter.
3. **`walking_double_support` and `walking_asymmetry` are fractions despite
   the unit literally being `"%"`.** A value of 0.30 must be multiplied by
   100. We caught this when a healthy 24-year-old appeared to spend 2,498 %
   of his gait in double support.
4. **Workout distance moved.** Older watchOS exposed `totalDistance` as an
   attribute on `<Workout>`; current watchOS (10+) emits it inside a
   `<WorkoutStatistics>` child. The parser handles both.
5. **Indoor runs (treadmill) are tagged `Outdoor Run`.** Distance is then
   nonsensical (0.1–0.4 km in 40 minutes). The pace estimator filters
   workouts with distance < 0.5 km and clamps to a physiologically plausible
   2.5–12.0 min/km band.

## Architecture

```
data/export.xml ─► parse.py (lxml.iterparse, streaming, constant memory)
                       │
                       ▼
                  Pydantic records ─► analyze.py ─► HealthReport (dataclass)
                                                         │
                                                         ▼
                                        render.py ─► dashboard/index.html
                                                    (Jinja2 + Chart.js)
```

The parser streams the export with `lxml.etree.iterparse`, clearing each
`<Record>` element after consumption so peak memory stays flat regardless of
export size. On a 559 MB raw XML this stays well under 200 MB resident.

The `HealthReport` is a tree of frozen dataclasses; serialising it to JSON
for the Jinja2 template is one recursive `dataclasses.asdict` call. The
front-end is intentionally dependency-light — vanilla JS + Chart.js, no
build step, deploys as a static folder.

## Test coverage

70 tests covering: every benchmark threshold including boundary cases, the
cutoff-date filter, unit conversion edge cases, and an end-to-end synthetic
build that asserts every domain in the report is populated with values inside
clinically plausible bands.

## Reproduce

```bash
# clone & install
git clone https://github.com/LorenzoBerti17/apple-health-clinical-dashboard.git
cd apple-health-clinical-dashboard
uv sync --extra dev

# 70 tests, ~1 second
uv run pytest

# build the public demo (synthetic data)
uv run python scripts/build_demo.py
# → demo/index.html

# build from your own export
# 1. export from iPhone: Settings → Health → ⋯ → Export All Health Data
# 2. drop the zip at data/export.zip   (gitignored, never committed)
uv run python scripts/build_personal.py
# → out/personal/index.html
```

## Tech stack

| Layer | Tooling |
|---|---|
| Parsing | Python 3.12, `lxml.iterparse`, Pydantic |
| Analysis | pandas, NumPy, SciPy |
| Templating | Jinja2 |
| Front-end | Chart.js 4.x, vanilla JS, no build step |
| Tooling | uv, ruff, mypy (strict), pytest + coverage |
| CI/CD | GitHub Actions → GitHub Pages |

## License

MIT — see [LICENSE](LICENSE).
