"""
Streaming XML parser for Apple Health export.xml.

Uses lxml.etree.iterparse to avoid loading the full XML tree into memory.
Only records from WATCH_CUTOFF onwards are returned (Apple Watch data).

Usage:
    from health_dashboard.parse import parse_export
    records = parse_export(Path("data/export.xml"))
"""

from __future__ import annotations

import zipfile
from datetime import date, datetime
from pathlib import Path
from typing import Generator, Literal

from lxml import etree
from pydantic import BaseModel, field_validator

# Only include Apple Watch data (Watch acquired December 2025)
WATCH_CUTOFF: date = date(2025, 12, 1)

# Apple Health XML date format
_DATE_FMT = "%Y-%m-%d %H:%M:%S %z"

# Mapping from Apple Health HKQuantityTypeIdentifier to short names
QUANTITY_TYPE_MAP: dict[str, str] = {
    "HKQuantityTypeIdentifierHeartRate": "heart_rate",
    "HKQuantityTypeIdentifierHeartRateVariabilitySDNN": "hrv_sdnn",
    "HKQuantityTypeIdentifierRestingHeartRate": "resting_heart_rate",
    "HKQuantityTypeIdentifierVO2Max": "vo2_max",
    "HKQuantityTypeIdentifierHeartRateRecoveryOneMinute": "hr_recovery",
    "HKQuantityTypeIdentifierStepCount": "step_count",
    "HKQuantityTypeIdentifierDistanceWalkingRunning": "distance_walk_run",
    "HKQuantityTypeIdentifierDistanceCycling": "distance_cycling",
    "HKQuantityTypeIdentifierActiveEnergyBurned": "active_energy",
    "HKQuantityTypeIdentifierBasalEnergyBurned": "basal_energy",
    "HKQuantityTypeIdentifierAppleExerciseTime": "exercise_time",
    "HKQuantityTypeIdentifierAppleStandTime": "stand_time",
    "HKQuantityTypeIdentifierEnvironmentalAudioExposure": "audio_exposure",
    "HKQuantityTypeIdentifierHeadphoneAudioExposure": "headphone_audio",
    "HKQuantityTypeIdentifierBodyMass": "body_mass",
    "HKQuantityTypeIdentifierHeight": "height",
    "HKQuantityTypeIdentifierBodyMassIndex": "bmi",
    "HKQuantityTypeIdentifierBodyFatPercentage": "body_fat",
    "HKQuantityTypeIdentifierOxygenSaturation": "spo2",
    "HKQuantityTypeIdentifierRespiratoryRate": "respiratory_rate",
    "HKQuantityTypeIdentifierWalkingSpeed": "walking_speed",
    "HKQuantityTypeIdentifierWalkingDoubleSupportPercentage": "walking_double_support",
    "HKQuantityTypeIdentifierWalkingAsymmetryPercentage": "walking_asymmetry",
    "HKQuantityTypeIdentifierWalkingStepLength": "walking_step_length",
    "HKQuantityTypeIdentifierRunningSpeed": "running_speed",
    "HKQuantityTypeIdentifierRunningStrideLength": "running_stride_length",
    "HKQuantityTypeIdentifierRunningGroundContactTime": "running_ground_contact",
    "HKQuantityTypeIdentifierRunningVerticalOscillation": "running_vertical_osc",
    "HKQuantityTypeIdentifierRunningPower": "running_power",
    "HKQuantityTypeIdentifierSleepDurationGoal": "sleep_duration_goal",
}

CategoryType = Literal["sleep", "mindful", "other"]


class HealthRecord(BaseModel):
    """A single quantitative health record."""

    record_type: str        # short name from QUANTITY_TYPE_MAP or raw identifier
    source_name: str
    start_date: datetime
    end_date: datetime
    value: float
    unit: str

    @field_validator("start_date", "end_date", mode="before")
    @classmethod
    def parse_dt(cls, v: str | datetime) -> datetime:
        if isinstance(v, datetime):
            return v
        return datetime.strptime(v, _DATE_FMT)


class SleepRecord(BaseModel):
    """A single sleep analysis record."""

    source_name: str
    start_date: datetime
    end_date: datetime
    # Apple Health category values for sleep
    value: Literal[
        "HKCategoryValueSleepAnalysisInBed",
        "HKCategoryValueSleepAnalysisAsleep",
        "HKCategoryValueSleepAnalysisAwake",
        "HKCategoryValueSleepAnalysisAsleepCore",
        "HKCategoryValueSleepAnalysisAsleepDeep",
        "HKCategoryValueSleepAnalysisAsleepREM",
    ]

    @field_validator("start_date", "end_date", mode="before")
    @classmethod
    def parse_dt(cls, v: str | datetime) -> datetime:
        if isinstance(v, datetime):
            return v
        return datetime.strptime(v, _DATE_FMT)

    @property
    def duration_hours(self) -> float:
        return (self.end_date - self.start_date).total_seconds() / 3600


class WorkoutRecord(BaseModel):
    """A single workout record."""

    workout_type: str
    source_name: str
    start_date: datetime
    end_date: datetime
    duration_min: float
    total_distance_km: float | None
    total_energy_kcal: float | None

    @field_validator("start_date", "end_date", mode="before")
    @classmethod
    def parse_dt(cls, v: str | datetime) -> datetime:
        if isinstance(v, datetime):
            return v
        return datetime.strptime(v, _DATE_FMT)


def _parse_float(s: str | None) -> float | None:
    try:
        return float(s) if s is not None else None
    except ValueError:
        return None


def _iter_xml(xml_path: Path) -> Generator[etree._Element, None, None]:
    """Yield Record and Workout elements via iterparse (Workout elements are
    yielded only at their closing tag so any nested WorkoutStatistics children
    are already attached)."""
    context = etree.iterparse(
        str(xml_path),
        events=("end",),
        tag=("Record", "Workout"),
        recover=True,
    )
    for _, elem in context:
        yield elem
        elem.clear()
        while elem.getprevious() is not None:
            parent = elem.getparent()
            if parent is not None:
                del parent[0]
            break


# Apple Health WorkoutStatistics types we care about for distance / energy
_WS_DISTANCE_TYPES = {
    "HKQuantityTypeIdentifierDistanceWalkingRunning",
    "HKQuantityTypeIdentifierDistanceCycling",
    "HKQuantityTypeIdentifierDistanceSwimming",
}
_WS_ENERGY_TYPES = {
    "HKQuantityTypeIdentifierActiveEnergyBurned",
}


def _after_cutoff(dt_str: str | None) -> bool:
    if dt_str is None:
        return False
    try:
        dt = datetime.strptime(dt_str, _DATE_FMT)
        return dt.date() >= WATCH_CUTOFF
    except ValueError:
        return False


def parse_export(
    source: Path,
) -> tuple[list[HealthRecord], list[SleepRecord], list[WorkoutRecord]]:
    """
    Parse Apple Health export.xml (or .zip containing it).

    Returns three lists: health records, sleep records, workout records.
    Only data from WATCH_CUTOFF (2025-12-01) onwards is included.
    """
    xml_path = _resolve_xml(source)

    health_records: list[HealthRecord] = []
    sleep_records: list[SleepRecord] = []
    workout_records: list[WorkoutRecord] = []

    for elem in _iter_xml(xml_path):
        if elem.tag == "Record":
            _handle_record(elem, health_records, sleep_records)
        elif elem.tag == "Workout":
            _handle_workout(elem, workout_records)

    return health_records, sleep_records, workout_records


def _handle_record(
    elem: etree._Element,
    health_out: list[HealthRecord],
    sleep_out: list[SleepRecord],
) -> None:
    type_id: str = elem.get("type", "")
    start: str | None = elem.get("startDate")

    if not _after_cutoff(start):
        return

    if type_id == "HKCategoryTypeIdentifierSleepAnalysis":
        value = elem.get("value", "")
        if value.startswith("HKCategoryValueSleepAnalysis"):
            try:
                sleep_out.append(
                    SleepRecord(
                        source_name=elem.get("sourceName", ""),
                        start_date=elem.get("startDate", ""),  # type: ignore[arg-type]
                        end_date=elem.get("endDate", ""),  # type: ignore[arg-type]
                        value=value,  # type: ignore[arg-type]
                    )
                )
            except Exception:
                pass
        return

    short_name = QUANTITY_TYPE_MAP.get(type_id, type_id)
    raw_value = elem.get("value")
    fval = _parse_float(raw_value)
    if fval is None:
        return

    try:
        health_out.append(
            HealthRecord(
                record_type=short_name,
                source_name=elem.get("sourceName", ""),
                start_date=elem.get("startDate", ""),  # type: ignore[arg-type]
                end_date=elem.get("endDate", ""),  # type: ignore[arg-type]
                value=fval,
                unit=elem.get("unit", ""),
            )
        )
    except Exception:
        pass


def _handle_workout(
    elem: etree._Element,
    out: list[WorkoutRecord],
) -> None:
    start: str | None = elem.get("startDate")
    if not _after_cutoff(start):
        return

    # Legacy: totalDistance / totalEnergyBurned as attributes (older watchOS)
    dist_km = _parse_float(elem.get("totalDistance"))
    energy_kcal = _parse_float(elem.get("totalEnergyBurned"))

    # Modern: WorkoutStatistics children (watchOS 10+).
    if dist_km is None or energy_kcal is None:
        for child in elem.iter("WorkoutStatistics"):
            ws_type = child.get("type", "")
            ws_sum = _parse_float(child.get("sum"))
            ws_unit = child.get("unit", "")
            if ws_sum is None:
                continue
            if dist_km is None and ws_type in _WS_DISTANCE_TYPES:
                dist_km = ws_sum if ws_unit.lower() in ("km", "kilometre") else ws_sum / 1000.0 if ws_unit == "m" else ws_sum
            elif energy_kcal is None and ws_type in _WS_ENERGY_TYPES:
                energy_kcal = ws_sum

    try:
        out.append(
            WorkoutRecord(
                workout_type=elem.get("workoutActivityType", ""),
                source_name=elem.get("sourceName", ""),
                start_date=elem.get("startDate", ""),  # type: ignore[arg-type]
                end_date=elem.get("endDate", ""),  # type: ignore[arg-type]
                duration_min=float(elem.get("duration", 0)),
                total_distance_km=dist_km,
                total_energy_kcal=energy_kcal,
            )
        )
    except Exception:
        pass


def _resolve_xml(source: Path) -> Path:
    """Accept .xml or .zip; if zip, extract export.xml to a temp location."""
    if source.suffix == ".xml":
        return source
    if source.suffix == ".zip":
        import tempfile

        tmp = Path(tempfile.mkdtemp())
        with zipfile.ZipFile(source) as zf:
            # Apple Health zip has apple_health_export/export.xml
            candidates = [n for n in zf.namelist() if n.endswith("export.xml")]
            if not candidates:
                raise FileNotFoundError("No export.xml found in zip archive.")
            zf.extract(candidates[0], tmp)
            return tmp / candidates[0]
    raise ValueError(f"Unsupported file type: {source.suffix!r}. Expected .xml or .zip")
