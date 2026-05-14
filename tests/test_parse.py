"""Tests for parse.py — XML parsing and data filtering."""

from __future__ import annotations

import textwrap
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

import pytest

from health_dashboard.parse import (
    WATCH_CUTOFF,
    HealthRecord,
    SleepRecord,
    _after_cutoff,
    _parse_float,
)


class TestAfterCutoff:
    def test_before_cutoff(self) -> None:
        assert _after_cutoff("2025-11-30 12:00:00 +0000") is False

    def test_on_cutoff(self) -> None:
        assert _after_cutoff("2025-12-01 00:00:00 +0000") is True

    def test_after_cutoff(self) -> None:
        assert _after_cutoff("2026-01-15 08:30:00 +0000") is True

    def test_none(self) -> None:
        assert _after_cutoff(None) is False

    def test_invalid_format(self) -> None:
        assert _after_cutoff("not-a-date") is False


class TestParseFloat:
    def test_valid(self) -> None:
        assert _parse_float("3.14") == pytest.approx(3.14)

    def test_none(self) -> None:
        assert _parse_float(None) is None

    def test_invalid(self) -> None:
        assert _parse_float("abc") is None


class TestHealthRecord:
    def test_valid_record(self) -> None:
        r = HealthRecord(
            record_type="resting_heart_rate",
            source_name="Apple Watch",
            start_date="2026-01-01 08:00:00 +0000",  # type: ignore[arg-type]
            end_date="2026-01-01 08:05:00 +0000",    # type: ignore[arg-type]
            value=55.0,
            unit="count/min",
        )
        assert r.value == 55.0
        assert r.start_date.tzinfo is not None


class TestSleepRecord:
    def test_duration(self) -> None:
        r = SleepRecord(
            source_name="Apple Watch",
            start_date="2026-01-01 23:00:00 +0000",  # type: ignore[arg-type]
            end_date="2026-01-02 07:00:00 +0000",    # type: ignore[arg-type]
            value="HKCategoryValueSleepAnalysisAsleepDeep",
        )
        assert r.duration_hours == pytest.approx(8.0)

    def test_invalid_stage_rejected(self) -> None:
        with pytest.raises(Exception):
            SleepRecord(
                source_name="Watch",
                start_date="2026-01-01 23:00:00 +0000",  # type: ignore[arg-type]
                end_date="2026-01-02 07:00:00 +0000",    # type: ignore[arg-type]
                value="HKCategoryValueSleepAnalysisUnknown",  # type: ignore[arg-type]
            )
