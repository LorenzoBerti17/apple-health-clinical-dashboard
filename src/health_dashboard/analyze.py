"""
Clinical analysis of Apple Health records.

Takes the parsed records from parse.py and produces a structured HealthReport
with per-domain statistics, classifications, linear trends, and correlations.
All thresholds are imported from benchmarks.py.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats

from health_dashboard.benchmarks import (
    AUDIO,
    DAILY_STEPS_GOAL,
    GAIT,
    HRR,
    HRV_MALE_UNDER30,
    RHR,
    SLEEP,
    VO2MAX_MALE_20_29,
    hr_max_tanaka,
)
from health_dashboard.parse import HealthRecord, SleepRecord, WorkoutRecord


# ---------------------------------------------------------------------------
# Helper types
# ---------------------------------------------------------------------------


@dataclass
class TrendResult:
    slope_per_day: float
    r_squared: float
    p_value: float
    n: int

    @property
    def is_significant(self) -> bool:
        return self.p_value < 0.05


@dataclass
class CardioStats:
    rhr_mean: float
    rhr_classification: str
    rhr_trend: TrendResult | None
    hrv_mean: float
    hrv_classification: str
    hrv_trend: TrendResult | None
    vo2max_latest: float | None
    vo2max_classification: str | None
    hr_recovery_mean: float | None
    hr_recovery_classification: str | None
    hr_max_tanaka: float


@dataclass
class SleepStats:
    mean_duration_h: float
    duration_classification: str
    mean_efficiency_pct: float
    efficiency_classification: str
    mean_deep_pct: float
    mean_rem_pct: float
    mean_awake_pct: float
    duration_trend: TrendResult | None
    n_nights: int


@dataclass
class ActivityStats:
    mean_daily_steps: float
    steps_goal_pct: float
    mean_active_energy_kcal: float
    mean_exercise_min: float
    total_distance_km: float
    steps_trend: TrendResult | None


@dataclass
class RunningStats:
    n_runs: int
    total_distance_km: float
    mean_pace_min_per_km: float | None
    mean_cadence_spm: float | None
    mean_power_w: float | None
    mean_ground_contact_ms: float | None
    mean_vertical_osc_cm: float | None
    longest_run_km: float | None


@dataclass
class AudioStats:
    mean_env_db: float
    env_classification: str
    mean_headphone_db: float | None
    headphone_classification: str | None
    pct_time_above_safe: float


@dataclass
class GaitStats:
    mean_walking_speed_ms: float
    speed_classification: str
    mean_double_support_pct: float | None
    mean_asymmetry_pct: float | None
    mean_step_length_m: float | None


@dataclass
class BodyStats:
    weight_kg: float | None
    height_m: float | None
    bmi: float | None
    body_fat_pct: float | None


@dataclass
class Correlations:
    hrv_vs_sleep_duration: float | None
    hrv_vs_rhr: float | None
    steps_vs_active_energy: float | None


@dataclass
class TimeSeries:
    """Daily-aggregated arrays used by the front-end charts."""

    labels: list[str] = field(default_factory=list)
    rhr: list[float | None] = field(default_factory=list)
    hrv: list[float | None] = field(default_factory=list)
    steps: list[float | None] = field(default_factory=list)
    active_energy: list[float | None] = field(default_factory=list)
    audio: list[float | None] = field(default_factory=list)
    sleep_duration: list[float | None] = field(default_factory=list)
    walking_speed: list[float | None] = field(default_factory=list)
    vo2max_dates: list[str] = field(default_factory=list)
    vo2max_values: list[float] = field(default_factory=list)
    run_dates: list[str] = field(default_factory=list)
    run_distances: list[float] = field(default_factory=list)
    run_paces: list[float] = field(default_factory=list)


@dataclass
class HealthReport:
    generated_at: datetime
    date_range_start: datetime
    date_range_end: datetime
    n_total_records: int
    cardio: CardioStats | None
    sleep: SleepStats | None
    activity: ActivityStats | None
    running: RunningStats | None
    audio: AudioStats | None
    gait: GaitStats | None
    body: BodyStats | None
    correlations: Correlations
    series: TimeSeries = field(default_factory=TimeSeries)
    age: int = 24


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _filter(records: list[HealthRecord], rtype: str) -> pd.DataFrame:
    """Return a DataFrame of records matching a single record_type."""
    rows = [
        {"date": r.start_date, "value": r.value, "unit": r.unit}
        for r in records
        if r.record_type == rtype
    ]
    df = pd.DataFrame(rows)
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"], utc=True)
        df = df.sort_values("date").reset_index(drop=True)
    return df


def _daily_mean(df: pd.DataFrame) -> pd.Series:  # type: ignore[type-arg]
    """Aggregate to calendar-day means (UTC)."""
    if df.empty:
        return pd.Series(dtype=float)
    df = df.copy()
    df["day"] = df["date"].dt.normalize()
    return df.groupby("day")["value"].mean()


def _daily_sum(df: pd.DataFrame) -> pd.Series:  # type: ignore[type-arg]
    """Aggregate to calendar-day sums (UTC) — for cumulative metrics like steps, kcal."""
    if df.empty:
        return pd.Series(dtype=float)
    df = df.copy()
    df["day"] = df["date"].dt.normalize()
    return df.groupby("day")["value"].sum()


# Unit conversion helpers — Apple Health sometimes uses km/hr and cm where
# clinical norms expect m/s and m.
def _kmh_to_ms(v: float) -> float:
    return v / 3.6


def _cm_to_m(v: float) -> float:
    return v / 100.0


def _linear_trend(series: pd.Series) -> TrendResult | None:  # type: ignore[type-arg]
    """Fit OLS trend over time; returns None if too few points."""
    s = series.dropna()
    if len(s) < 5:
        return None
    x = np.arange(len(s), dtype=float)
    slope, _intercept, r, p, _se = stats.linregress(x, s.values)
    return TrendResult(
        slope_per_day=float(slope),
        r_squared=float(r**2),
        p_value=float(p),
        n=len(s),
    )


def _pearson(a: pd.Series, b: pd.Series) -> float | None:  # type: ignore[type-arg]
    """Pearson r between two series aligned by index; None if too few points."""
    merged = pd.concat([a, b], axis=1).dropna()
    if len(merged) < 10:
        return None
    r, _ = stats.pearsonr(merged.iloc[:, 0], merged.iloc[:, 1])
    return float(r)


# ---------------------------------------------------------------------------
# Domain analyzers
# ---------------------------------------------------------------------------


def _analyze_cardio(records: list[HealthRecord], age: int) -> CardioStats | None:
    rhr_df = _filter(records, "resting_heart_rate")
    hrv_df = _filter(records, "hrv_sdnn")

    if rhr_df.empty and hrv_df.empty:
        return None

    rhr_daily = _daily_mean(rhr_df)
    hrv_daily = _daily_mean(hrv_df)

    rhr_mean = float(rhr_daily.mean()) if not rhr_daily.empty else 0.0
    hrv_mean = float(hrv_daily.mean()) if not hrv_daily.empty else 0.0

    vo2_df = _filter(records, "vo2_max")
    vo2_latest: float | None = float(vo2_df["value"].iloc[-1]) if not vo2_df.empty else None

    hrr_df = _filter(records, "hr_recovery")
    hrr_mean: float | None = float(hrr_df["value"].mean()) if not hrr_df.empty else None

    return CardioStats(
        rhr_mean=rhr_mean,
        rhr_classification=RHR.classify(rhr_mean),
        rhr_trend=_linear_trend(rhr_daily),
        hrv_mean=hrv_mean,
        hrv_classification=HRV_MALE_UNDER30.classify(hrv_mean),
        hrv_trend=_linear_trend(hrv_daily),
        vo2max_latest=vo2_latest,
        vo2max_classification=VO2MAX_MALE_20_29.classify(vo2_latest) if vo2_latest else None,
        hr_recovery_mean=hrr_mean,
        hr_recovery_classification=HRR.classify(hrr_mean) if hrr_mean else None,
        hr_max_tanaka=hr_max_tanaka(age),
    )


def _analyze_sleep(sleep_records: list[SleepRecord]) -> SleepStats | None:
    if not sleep_records:
        return None

    df = pd.DataFrame(
        [
            {
                "date": r.start_date,
                "end": r.end_date,
                "value": r.value,
                "duration_h": r.duration_hours,
            }
            for r in sleep_records
        ]
    )
    df["date"] = pd.to_datetime(df["date"], utc=True)
    df["end"] = pd.to_datetime(df["end"], utc=True)
    df["night"] = (df["date"] - timedelta(hours=12)).dt.normalize()

    asleep_stages = {
        "HKCategoryValueSleepAnalysisAsleepCore",
        "HKCategoryValueSleepAnalysisAsleepDeep",
        "HKCategoryValueSleepAnalysisAsleepREM",
        "HKCategoryValueSleepAnalysisAsleep",
    }
    deep_stage = "HKCategoryValueSleepAnalysisAsleepDeep"
    rem_stage = "HKCategoryValueSleepAnalysisAsleepREM"
    awake_stage = "HKCategoryValueSleepAnalysisAwake"

    nights = []
    for night, grp in df.groupby("night"):
        total_asleep = grp.loc[grp["value"].isin(asleep_stages), "duration_h"].sum()
        total_deep = grp.loc[grp["value"] == deep_stage, "duration_h"].sum()
        total_rem = grp.loc[grp["value"] == rem_stage, "duration_h"].sum()
        total_awake = grp.loc[grp["value"] == awake_stage, "duration_h"].sum()
        in_bed = total_asleep + total_awake

        if total_asleep < 1.0:
            continue

        efficiency = (total_asleep / in_bed * 100) if in_bed > 0 else 0.0
        deep_pct = (total_deep / total_asleep * 100) if total_asleep > 0 else 0.0
        rem_pct = (total_rem / total_asleep * 100) if total_asleep > 0 else 0.0
        awake_pct = (total_awake / in_bed * 100) if in_bed > 0 else 0.0

        nights.append(
            {
                "night": night,
                "duration_h": total_asleep,
                "efficiency": efficiency,
                "deep_pct": deep_pct,
                "rem_pct": rem_pct,
                "awake_pct": awake_pct,
            }
        )

    if not nights:
        return None

    ndf = pd.DataFrame(nights).set_index("night").sort_index()
    mean_dur = float(ndf["duration_h"].mean())

    return SleepStats(
        mean_duration_h=mean_dur,
        duration_classification=SLEEP.classify_duration(mean_dur),
        mean_efficiency_pct=float(ndf["efficiency"].mean()),
        efficiency_classification=SLEEP.classify_efficiency(float(ndf["efficiency"].mean())),
        mean_deep_pct=float(ndf["deep_pct"].mean()),
        mean_rem_pct=float(ndf["rem_pct"].mean()),
        mean_awake_pct=float(ndf["awake_pct"].mean()),
        duration_trend=_linear_trend(ndf["duration_h"]),
        n_nights=len(ndf),
    )


def _analyze_activity(records: list[HealthRecord]) -> ActivityStats | None:
    steps_df = _filter(records, "step_count")
    energy_df = _filter(records, "active_energy")
    exercise_df = _filter(records, "exercise_time")
    distance_df = _filter(records, "distance_walk_run")

    if steps_df.empty:
        return None

    # Cumulative metrics: Apple Health stores sub-daily samples that must be
    # SUMMED per day (not averaged) to recover the daily total.
    steps_daily = _daily_sum(steps_df)
    energy_daily = _daily_sum(energy_df) if not energy_df.empty else pd.Series(dtype=float)
    exercise_daily = _daily_sum(exercise_df) if not exercise_df.empty else pd.Series(dtype=float)

    mean_steps = float(steps_daily.mean())

    return ActivityStats(
        mean_daily_steps=mean_steps,
        steps_goal_pct=mean_steps / DAILY_STEPS_GOAL * 100,
        mean_active_energy_kcal=float(energy_daily.mean()) if not energy_daily.empty else 0.0,
        mean_exercise_min=float(exercise_daily.mean()) if not exercise_daily.empty else 0.0,
        total_distance_km=float(distance_df["value"].sum()) if not distance_df.empty else 0.0,
        steps_trend=_linear_trend(steps_daily),
    )


def _analyze_running(workouts: list[WorkoutRecord]) -> RunningStats | None:
    runs = [
        w for w in workouts
        if "Running" in w.workout_type or "running" in w.workout_type.lower()
    ]
    if not runs:
        return None

    distances = [r.total_distance_km for r in runs if r.total_distance_km is not None]
    energies = [r.total_energy_kcal for r in runs if r.total_energy_kcal is not None]

    total_dist = sum(distances)
    longest = max(distances) if distances else None

    # Pace: min/km from duration and distance.
    # Filter out short/indoor runs without reliable GPS (<0.5 km) which would
    # otherwise produce nonsensical pace values.
    paces = []
    for r in runs:
        if r.total_distance_km and r.total_distance_km > 0.5:
            pace = r.duration_min / r.total_distance_km
            if 2.5 < pace < 12.0:  # plausible human running pace band
                paces.append(pace)
    mean_pace = float(np.mean(paces)) if paces else None

    return RunningStats(
        n_runs=len(runs),
        total_distance_km=total_dist,
        mean_pace_min_per_km=mean_pace,
        mean_cadence_spm=None,   # populated from health records if available
        mean_power_w=None,
        mean_ground_contact_ms=None,
        mean_vertical_osc_cm=None,
        longest_run_km=longest,
    )


def _analyze_audio(records: list[HealthRecord]) -> AudioStats | None:
    env_df = _filter(records, "audio_exposure")
    hp_df = _filter(records, "headphone_audio")

    if env_df.empty:
        return None

    env_mean = float(env_df["value"].mean())
    hp_mean = float(hp_df["value"].mean()) if not hp_df.empty else None
    pct_above = float((env_df["value"] > AUDIO.safe_chronic).mean() * 100)

    return AudioStats(
        mean_env_db=env_mean,
        env_classification=AUDIO.classify(env_mean),
        mean_headphone_db=hp_mean,
        headphone_classification=AUDIO.classify(hp_mean) if hp_mean else None,
        pct_time_above_safe=pct_above,
    )


def _analyze_gait(records: list[HealthRecord]) -> GaitStats | None:
    speed_df = _filter(records, "walking_speed")
    if speed_df.empty:
        return None

    ds_df = _filter(records, "walking_double_support")
    asym_df = _filter(records, "walking_asymmetry")
    step_df = _filter(records, "walking_step_length")

    # Apple Watch reports walking_speed in km/hr — convert to m/s for the
    # Studenski clinical threshold (>1.0 m/s).
    raw_speed = float(speed_df["value"].mean())
    speed_unit = str(speed_df["unit"].iloc[0]) if not speed_df.empty else ""
    mean_speed = _kmh_to_ms(raw_speed) if "km/hr" in speed_unit or "km/h" in speed_unit else raw_speed

    # walking_step_length is reported in cm by Apple Health.
    step_length_m: float | None = None
    if not step_df.empty:
        raw_step = float(step_df["value"].mean())
        step_unit = str(step_df["unit"].iloc[0])
        step_length_m = _cm_to_m(raw_step) if step_unit == "cm" else raw_step

    # Apple Health reports walking_double_support and walking_asymmetry as
    # fractions (0–1) despite the unit being labelled "%". Multiply by 100 to
    # express as percentages, which is the clinical convention.
    ds_pct = float(ds_df["value"].mean()) * 100 if not ds_df.empty else None
    asym_pct = float(asym_df["value"].mean()) * 100 if not asym_df.empty else None

    return GaitStats(
        mean_walking_speed_ms=mean_speed,
        speed_classification=GAIT.classify_speed(mean_speed),
        mean_double_support_pct=ds_pct,
        mean_asymmetry_pct=asym_pct,
        mean_step_length_m=step_length_m,
    )


def _analyze_body(records: list[HealthRecord]) -> BodyStats:
    weight_df = _filter(records, "body_mass")
    height_df = _filter(records, "height")
    fat_df = _filter(records, "body_fat")

    weight = float(weight_df["value"].iloc[-1]) if not weight_df.empty else None
    height = float(height_df["value"].iloc[-1]) if not height_df.empty else None
    fat = float(fat_df["value"].iloc[-1]) if not fat_df.empty else None

    bmi: float | None = None
    if weight and height and height > 0:
        bmi = weight / (height**2)

    return BodyStats(weight_kg=weight, height_m=height, bmi=bmi, body_fat_pct=fat)


def _analyze_correlations(
    records: list[HealthRecord],
    sleep: SleepStats | None,
) -> Correlations:
    hrv_daily = _daily_mean(_filter(records, "hrv_sdnn"))
    rhr_daily = _daily_mean(_filter(records, "resting_heart_rate"))
    steps_daily = _daily_mean(_filter(records, "step_count"))
    energy_daily = _daily_mean(_filter(records, "active_energy"))

    return Correlations(
        hrv_vs_rhr=_pearson(hrv_daily, rhr_daily),
        hrv_vs_sleep_duration=None,   # requires night-level HRV, not implemented yet
        steps_vs_active_energy=_pearson(steps_daily, energy_daily),
    )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def _build_series(
    health_records: list[HealthRecord],
    sleep_records: list[SleepRecord],
    workout_records: list[WorkoutRecord],
) -> TimeSeries:
    """Build daily time-series arrays for the front-end charts."""
    series = TimeSeries()

    # Calendar-day union of all daily-aggregable metrics
    rhr_d = _daily_mean(_filter(health_records, "resting_heart_rate"))
    hrv_d = _daily_mean(_filter(health_records, "hrv_sdnn"))
    steps_d = _daily_sum(_filter(health_records, "step_count"))
    energy_d = _daily_sum(_filter(health_records, "active_energy"))
    audio_d = _daily_mean(_filter(health_records, "audio_exposure"))

    speed_df = _filter(health_records, "walking_speed")
    if not speed_df.empty and "km/hr" in str(speed_df["unit"].iloc[0]):
        speed_df = speed_df.copy()
        speed_df["value"] = speed_df["value"] / 3.6
    speed_d = _daily_mean(speed_df)

    # Sleep duration per night
    sleep_d = pd.Series(dtype=float)
    if sleep_records:
        sdf = pd.DataFrame(
            [
                {"night": (r.start_date - timedelta(hours=12)), "value": r.value, "h": r.duration_hours}
                for r in sleep_records
            ]
        )
        sdf["night"] = pd.to_datetime(sdf["night"], utc=True).dt.normalize()
        asleep_stages = {
            "HKCategoryValueSleepAnalysisAsleepCore",
            "HKCategoryValueSleepAnalysisAsleepDeep",
            "HKCategoryValueSleepAnalysisAsleepREM",
            "HKCategoryValueSleepAnalysisAsleep",
        }
        sleep_d = (
            sdf[sdf["value"].isin(asleep_stages)]
            .groupby("night")["h"]
            .sum()
        )

    # Union of all calendar days
    all_days = sorted(
        set(rhr_d.index) | set(hrv_d.index) | set(steps_d.index)
        | set(energy_d.index) | set(audio_d.index) | set(speed_d.index)
        | set(sleep_d.index)
    )

    series.labels = [d.strftime("%Y-%m-%d") for d in all_days]

    def _align(s: pd.Series) -> list[float | None]:  # type: ignore[type-arg]
        return [float(s.get(d)) if d in s.index and pd.notna(s.get(d)) else None for d in all_days]

    series.rhr = _align(rhr_d)
    series.hrv = _align(hrv_d)
    series.steps = _align(steps_d)
    series.active_energy = _align(energy_d)
    series.audio = _align(audio_d)
    series.walking_speed = _align(speed_d)
    series.sleep_duration = _align(sleep_d)

    # VO2max — only on measurement days, not interpolated
    vo2_df = _filter(health_records, "vo2_max")
    if not vo2_df.empty:
        series.vo2max_dates = [d.strftime("%Y-%m-%d") for d in vo2_df["date"]]
        series.vo2max_values = [float(v) for v in vo2_df["value"]]

    # Runs sequence
    runs = [w for w in workout_records if "Running" in w.workout_type]
    for r in runs:
        if r.total_distance_km and r.total_distance_km > 0.5:
            series.run_dates.append(r.start_date.strftime("%Y-%m-%d"))
            series.run_distances.append(r.total_distance_km)
            pace = r.duration_min / r.total_distance_km
            series.run_paces.append(pace if 2.5 < pace < 12.0 else None)  # type: ignore[arg-type]

    return series


def build_report(
    health_records: list[HealthRecord],
    sleep_records: list[SleepRecord],
    workout_records: list[WorkoutRecord],
    age: int = 24,
) -> HealthReport:
    """Build a HealthReport from parsed Apple Health data."""
    all_dates = [r.start_date for r in health_records] + [r.start_date for r in sleep_records]
    if all_dates:
        date_start = min(all_dates)
        date_end = max(all_dates)
    else:
        now = datetime.now()
        date_start = date_end = now

    return HealthReport(
        generated_at=datetime.now(),
        date_range_start=date_start,
        date_range_end=date_end,
        n_total_records=len(health_records) + len(sleep_records) + len(workout_records),
        cardio=_analyze_cardio(health_records, age),
        sleep=_analyze_sleep(sleep_records),
        activity=_analyze_activity(health_records),
        running=_analyze_running(workout_records),
        audio=_analyze_audio(health_records),
        gait=_analyze_gait(health_records),
        body=_analyze_body(health_records),
        correlations=_analyze_correlations(health_records, None),
        series=_build_series(health_records, sleep_records, workout_records),
        age=age,
    )


def report_to_dict(report: HealthReport) -> dict[str, Any]:
    """Serialize HealthReport to a JSON-compatible dict for the Jinja2 template."""
    import dataclasses

    def _convert(obj: Any) -> Any:
        if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
            return {k: _convert(v) for k, v in dataclasses.asdict(obj).items()}  # type: ignore[arg-type]
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, float) and (obj != obj):  # NaN
            return None
        return obj

    return _convert(report)  # type: ignore[return-value]
