"""Tests for benchmarks.py — clinical threshold correctness."""

from __future__ import annotations

import pytest

from health_dashboard.benchmarks import (
    AUDIO,
    BMI,
    GAIT,
    HRR,
    HRV_MALE_UNDER30,
    RHR,
    SLEEP,
    VO2MAX_MALE_20_29,
    hr_max_fox,
    hr_max_tanaka,
)


class TestRHR:
    def test_athletic(self) -> None:
        assert RHR.classify(55) == "athletic"

    def test_excellent(self) -> None:
        assert RHR.classify(65) == "excellent"

    def test_normal(self) -> None:
        assert RHR.classify(75) == "normal"

    def test_elevated(self) -> None:
        assert RHR.classify(82) == "elevated"

    def test_boundary_athletic(self) -> None:
        assert RHR.classify(60) == "excellent"  # boundary: 60 is NOT athletic

    def test_boundary_elevated(self) -> None:
        assert RHR.classify(80) == "elevated"   # 80 is elevated


class TestHRV:
    def test_excellent(self) -> None:
        assert HRV_MALE_UNDER30.classify(70) == "excellent"

    def test_good(self) -> None:
        assert HRV_MALE_UNDER30.classify(58) == "good"

    def test_fair(self) -> None:
        assert HRV_MALE_UNDER30.classify(45) == "fair"

    def test_low(self) -> None:
        assert HRV_MALE_UNDER30.classify(30) == "low"

    def test_at_p50(self) -> None:
        assert HRV_MALE_UNDER30.classify(55) == "good"

    def test_at_p25(self) -> None:
        assert HRV_MALE_UNDER30.classify(40) == "fair"


class TestVO2Max:
    def test_elite(self) -> None:
        assert VO2MAX_MALE_20_29.classify(58) == "elite"

    def test_excellent(self) -> None:
        assert VO2MAX_MALE_20_29.classify(52) == "excellent"

    def test_good(self) -> None:
        assert VO2MAX_MALE_20_29.classify(47) == "good"

    def test_average(self) -> None:
        assert VO2MAX_MALE_20_29.classify(43) == "average"

    def test_below_average(self) -> None:
        assert VO2MAX_MALE_20_29.classify(38) == "below_average"

    def test_poor(self) -> None:
        assert VO2MAX_MALE_20_29.classify(30) == "poor"


class TestHRMax:
    def test_tanaka_24(self) -> None:
        assert hr_max_tanaka(24) == pytest.approx(208 - 0.7 * 24)

    def test_fox_24(self) -> None:
        assert hr_max_fox(24) == pytest.approx(196.0)

    def test_tanaka_less_than_fox_for_young(self) -> None:
        # Tanaka gives lower values for young ages vs Fox
        assert hr_max_tanaka(20) < hr_max_fox(20)


class TestHRR:
    def test_abnormal(self) -> None:
        assert HRR.classify(10) == "abnormal"

    def test_moderate(self) -> None:
        assert HRR.classify(15) == "moderate"

    def test_good(self) -> None:
        assert HRR.classify(20) == "good"

    def test_boundary_abnormal(self) -> None:
        assert HRR.classify(12) == "abnormal"  # ≤12 is abnormal

    def test_boundary_good(self) -> None:
        assert HRR.classify(18) == "good"      # ≥18 is good


class TestSleep:
    def test_optimal(self) -> None:
        assert SLEEP.classify_duration(8.0) == "optimal"

    def test_short(self) -> None:
        assert SLEEP.classify_duration(6.5) == "short"

    def test_long(self) -> None:
        assert SLEEP.classify_duration(9.5) == "long"

    def test_efficiency_good(self) -> None:
        assert SLEEP.classify_efficiency(90) == "good"

    def test_efficiency_poor(self) -> None:
        assert SLEEP.classify_efficiency(80) == "poor"


class TestAudio:
    def test_safe(self) -> None:
        assert AUDIO.classify(60) == "safe"

    def test_moderate(self) -> None:
        assert AUDIO.classify(78) == "moderate"

    def test_high(self) -> None:
        assert AUDIO.classify(92) == "high"

    def test_dangerous(self) -> None:
        assert AUDIO.classify(105) == "dangerous"


class TestGait:
    def test_normal_speed(self) -> None:
        assert GAIT.classify_speed(1.2) == "normal"

    def test_slow_speed(self) -> None:
        assert GAIT.classify_speed(0.9) == "slow"

    def test_boundary(self) -> None:
        assert GAIT.classify_speed(1.0) == "normal"


class TestBMI:
    def test_underweight(self) -> None:
        assert BMI.classify(17) == "underweight"

    def test_normal(self) -> None:
        assert BMI.classify(22) == "normal"

    def test_overweight(self) -> None:
        assert BMI.classify(27) == "overweight"

    def test_obese(self) -> None:
        assert BMI.classify(32) == "obese"
