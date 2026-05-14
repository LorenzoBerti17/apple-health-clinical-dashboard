"""
Generate synthetic Apple Health data for the public demo.

All values are seeded random draws from realistic distributions.
No real personal data is ever used here.

Distributions are calibrated for a healthy 24-year-old male athlete
(VO₂max ~52, RHR ~52, HRV ~58ms) to make the demo visually interesting.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone
from typing import Literal

import numpy as np

from health_dashboard.parse import HealthRecord, SleepRecord, WorkoutRecord

_SEED = 42
_rng = np.random.default_rng(_SEED)

# Demo period: 5 months of Watch data
_START = datetime(2025, 12, 1, tzinfo=timezone.utc)
_END = datetime(2026, 4, 30, tzinfo=timezone.utc)


def _days() -> list[datetime]:
    n = (_END.date() - _START.date()).days + 1
    return [_START + timedelta(days=i) for i in range(n)]


def _ts(day: datetime, hour: int = 8, minute: int = 0) -> datetime:
    return day.replace(hour=hour, minute=minute, second=0, microsecond=0)


def generate_demo_data(
    seed: int = _SEED,
) -> tuple[list[HealthRecord], list[SleepRecord], list[WorkoutRecord]]:
    """Return (health_records, sleep_records, workout_records) for the demo."""
    rng = np.random.default_rng(seed)
    days = _days()
    n = len(days)

    health: list[HealthRecord] = []
    sleep: list[SleepRecord] = []
    workouts: list[WorkoutRecord] = []

    # Slow positive HRV trend over the period (fitness improving)
    hrv_base = 55.0
    hrv_trend = np.linspace(0, 8, n)
    hrv_noise = rng.normal(0, 5, n)

    # Slow negative RHR trend (fitter over time)
    rhr_base = 54.0
    rhr_trend = np.linspace(0, -3, n)
    rhr_noise = rng.normal(0, 3, n)

    # Steps with weekly seasonality
    steps_base = 9500.0
    weekly_pattern = np.tile([1.0, 1.05, 0.95, 1.1, 1.0, 1.3, 1.2], (n // 7) + 1)[:n]

    for i, day in enumerate(days):
        # Resting HR (one per day, morning)
        rhr = float(np.clip(rhr_base + rhr_trend[i] + rhr_noise[i], 42, 72))
        health.append(
            HealthRecord(
                record_type="resting_heart_rate",
                source_name="Apple Watch",
                start_date=_ts(day, 6),
                end_date=_ts(day, 6, 5),
                value=rhr,
                unit="count/min",
            )
        )

        # HRV SDNN (one per day, overnight)
        hrv = float(np.clip(hrv_base + hrv_trend[i] + hrv_noise[i], 20, 120))
        health.append(
            HealthRecord(
                record_type="hrv_sdnn",
                source_name="Apple Watch",
                start_date=_ts(day, 5),
                end_date=_ts(day, 5, 5),
                value=hrv,
                unit="ms",
            )
        )

        # Steps
        steps = float(np.clip(steps_base * weekly_pattern[i] + rng.normal(0, 800), 1000, 25000))
        health.append(
            HealthRecord(
                record_type="step_count",
                source_name="Apple Watch",
                start_date=_ts(day, 0),
                end_date=_ts(day, 23, 59),
                value=steps,
                unit="count",
            )
        )

        # Active energy ~350 kcal base
        energy = float(np.clip(350 * weekly_pattern[i] + rng.normal(0, 50), 100, 900))
        health.append(
            HealthRecord(
                record_type="active_energy",
                source_name="Apple Watch",
                start_date=_ts(day, 0),
                end_date=_ts(day, 23, 59),
                value=energy,
                unit="kcal",
            )
        )

        # Walking speed
        ws = float(np.clip(rng.normal(1.35, 0.08), 1.0, 1.8))
        health.append(
            HealthRecord(
                record_type="walking_speed",
                source_name="Apple Watch",
                start_date=_ts(day, 9),
                end_date=_ts(day, 9, 30),
                value=ws,
                unit="m/s",
            )
        )

        # Audio exposure (mostly safe)
        audio_db = float(np.clip(rng.normal(62, 8), 40, 95))
        health.append(
            HealthRecord(
                record_type="audio_exposure",
                source_name="Apple Watch",
                start_date=_ts(day, 0),
                end_date=_ts(day, 23, 59),
                value=audio_db,
                unit="dBASPL",
            )
        )

        # Walking gait metrics
        health.append(
            HealthRecord(
                record_type="walking_double_support",
                source_name="Apple Watch",
                start_date=_ts(day, 9),
                end_date=_ts(day, 9, 30),
                value=float(np.clip(rng.normal(25, 2), 18, 35)),
                unit="%",
            )
        )
        health.append(
            HealthRecord(
                record_type="walking_asymmetry",
                source_name="Apple Watch",
                start_date=_ts(day, 9),
                end_date=_ts(day, 9, 30),
                value=float(np.clip(rng.normal(1.8, 0.5), 0, 6)),
                unit="%",
            )
        )

        # Sleep (every night)
        sleep_start = day - timedelta(hours=1) + timedelta(hours=int(rng.integers(22, 24)))
        sleep_start = sleep_start.replace(hour=int(rng.integers(22, 24)), minute=int(rng.integers(0, 60)))
        duration_h = float(np.clip(rng.normal(7.5, 0.5), 5.5, 9.5))

        # Deep sleep ~18%, REM ~22%, core ~50%, awake ~10%
        deep_h = duration_h * float(np.clip(rng.normal(0.18, 0.04), 0.08, 0.30))
        rem_h = duration_h * float(np.clip(rng.normal(0.22, 0.04), 0.12, 0.35))
        core_h = duration_h - deep_h - rem_h
        awake_h = duration_h * float(np.clip(rng.normal(0.05, 0.02), 0.01, 0.15))

        stages: list[tuple[str, float]] = [
            ("HKCategoryValueSleepAnalysisAsleepCore", core_h),
            ("HKCategoryValueSleepAnalysisAsleepDeep", deep_h),
            ("HKCategoryValueSleepAnalysisAsleepREM", rem_h),
            ("HKCategoryValueSleepAnalysisAwake", awake_h),
        ]
        cursor = sleep_start
        for stage_val, stage_h in stages:
            end_ts = cursor + timedelta(hours=stage_h)
            sleep.append(
                SleepRecord(
                    source_name="Apple Watch",
                    start_date=cursor,
                    end_date=end_ts,
                    value=stage_val,  # type: ignore[arg-type]
                )
            )
            cursor = end_ts

    # VO2Max — quarterly measurement
    for i in range(0, n, 30):
        day = days[i]
        vo2 = float(np.clip(50.0 + (i / n) * 3 + rng.normal(0, 1.5), 44, 58))
        health.append(
            HealthRecord(
                record_type="vo2_max",
                source_name="Apple Watch",
                start_date=_ts(day, 10),
                end_date=_ts(day, 10, 5),
                value=vo2,
                unit="mL/min·kg",
            )
        )

    # Body metrics — once (stable)
    health.append(
        HealthRecord(
            record_type="body_mass",
            source_name="iPhone",
            start_date=_ts(days[0], 8),
            end_date=_ts(days[0], 8, 1),
            value=72.0,
            unit="kg",
        )
    )
    health.append(
        HealthRecord(
            record_type="height",
            source_name="iPhone",
            start_date=_ts(days[0], 8),
            end_date=_ts(days[0], 8, 1),
            value=1.78,
            unit="m",
        )
    )

    # Running workouts — ~3 per week
    workout_days = [d for i, d in enumerate(days) if i % 3 == 0]
    for wd in workout_days:
        dist_km = float(np.clip(rng.normal(9, 2.5), 3, 25))
        pace = float(np.clip(rng.normal(5.1, 0.4), 3.8, 7.5))  # min/km
        duration_min = dist_km * pace
        workouts.append(
            WorkoutRecord(
                workout_type="HKWorkoutActivityTypeRunning",
                source_name="Apple Watch",
                start_date=_ts(wd, 7),
                end_date=_ts(wd, 7) + timedelta(minutes=duration_min),
                duration_min=duration_min,
                total_distance_km=dist_km,
                total_energy_kcal=float(dist_km * 70),
            )
        )

    return health, sleep, workouts
