"""Tests for analyze.py — report building from parsed data."""

from __future__ import annotations

import pytest

from health_dashboard.analyze import build_report
from health_dashboard.synthetic import generate_demo_data


@pytest.fixture(scope="module")
def demo_report():  # type: ignore[no-untyped-def]
    health, sleep, workouts = generate_demo_data(seed=42)
    return build_report(health, sleep, workouts, age=24)


class TestReportStructure:
    def test_report_not_none(self, demo_report) -> None:  # type: ignore[no-untyped-def]
        assert demo_report is not None

    def test_cardio_present(self, demo_report) -> None:  # type: ignore[no-untyped-def]
        assert demo_report.cardio is not None

    def test_sleep_present(self, demo_report) -> None:  # type: ignore[no-untyped-def]
        assert demo_report.sleep is not None

    def test_activity_present(self, demo_report) -> None:  # type: ignore[no-untyped-def]
        assert demo_report.activity is not None

    def test_running_present(self, demo_report) -> None:  # type: ignore[no-untyped-def]
        assert demo_report.running is not None

    def test_total_records_positive(self, demo_report) -> None:  # type: ignore[no-untyped-def]
        assert demo_report.n_total_records > 0


class TestCardioValues:
    def test_rhr_in_range(self, demo_report) -> None:  # type: ignore[no-untyped-def]
        c = demo_report.cardio
        assert c is not None
        assert 40 <= c.rhr_mean <= 100

    def test_hrv_in_range(self, demo_report) -> None:  # type: ignore[no-untyped-def]
        c = demo_report.cardio
        assert c is not None
        assert 10 <= c.hrv_mean <= 150

    def test_vo2_in_range(self, demo_report) -> None:  # type: ignore[no-untyped-def]
        c = demo_report.cardio
        assert c is not None
        assert c.vo2max_latest is not None
        assert 30 <= c.vo2max_latest <= 80

    def test_hrmax_tanaka_24(self, demo_report) -> None:  # type: ignore[no-untyped-def]
        c = demo_report.cardio
        assert c is not None
        assert c.hr_max_tanaka == pytest.approx(208 - 0.7 * 24)


class TestSleepValues:
    def test_duration_plausible(self, demo_report) -> None:  # type: ignore[no-untyped-def]
        s = demo_report.sleep
        assert s is not None
        assert 4 <= s.mean_duration_h <= 12

    def test_efficiency_pct(self, demo_report) -> None:  # type: ignore[no-untyped-def]
        s = demo_report.sleep
        assert s is not None
        assert 50 <= s.mean_efficiency_pct <= 100

    def test_stages_sum_near_100(self, demo_report) -> None:  # type: ignore[no-untyped-def]
        s = demo_report.sleep
        assert s is not None
        total = s.mean_deep_pct + s.mean_rem_pct
        # Deep + REM should be < 100% (core takes the rest)
        assert total < 100


class TestActivityValues:
    def test_steps_positive(self, demo_report) -> None:  # type: ignore[no-untyped-def]
        a = demo_report.activity
        assert a is not None
        assert a.mean_daily_steps > 0

    def test_steps_goal_pct(self, demo_report) -> None:  # type: ignore[no-untyped-def]
        a = demo_report.activity
        assert a is not None
        assert a.steps_goal_pct > 0


class TestRunningValues:
    def test_n_runs_positive(self, demo_report) -> None:  # type: ignore[no-untyped-def]
        r = demo_report.running
        assert r is not None
        assert r.n_runs > 0

    def test_pace_reasonable(self, demo_report) -> None:  # type: ignore[no-untyped-def]
        r = demo_report.running
        assert r is not None
        assert r.mean_pace_min_per_km is not None
        assert 3.0 <= r.mean_pace_min_per_km <= 10.0
