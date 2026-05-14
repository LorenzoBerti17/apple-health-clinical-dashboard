"""
Clinical benchmark thresholds used throughout the analysis.

Every constant is annotated with its bibliographic source so the methodology
document and README can cite them accurately.  All numeric values are kept here
and imported by analyze.py — never hard-coded elsewhere.

References are in the module-level REFERENCES dict and as inline comments.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

# ---------------------------------------------------------------------------
# Reference registry
# ---------------------------------------------------------------------------

REFERENCES: dict[str, str] = {
    "tanaka2001": (
        "Tanaka H, Monahan KD, Seals DR. Age-predicted maximal heart rate revisited. "
        "J Am Coll Cardiol. 2001;37(1):153-156. doi:10.1016/S0735-1097(00)01054-8"
    ),
    "fox1971": (
        "Fox SM, Naughton JP, Haskell WL. Physical activity and the prevention of "
        "coronary heart disease. Ann Clin Res. 1971;3(6):404-432."
    ),
    "cole1999": (
        "Cole CR, Blackstone EH, Pashkow FJ, et al. Heart-rate recovery immediately "
        "after exercise as a predictor of mortality. "
        "N Engl J Med. 1999;341(18):1351-1357. doi:10.1056/NEJM199910283411804"
    ),
    "umetani1998": (
        "Umetani K, Singer DH, McCraty R, Atkinson M. Twenty-four hour time domain "
        "heart rate variability and heart rate: relations to age and gender over nine "
        "decades. J Am Coll Cardiol. 1998;31(3):593-601. "
        "doi:10.1016/S0735-1097(97)00554-8"
    ),
    "shaffer2017": (
        "Shaffer F, Ginsberg JP. An Overview of Heart Rate Variability Metrics and Norms. "
        "Front Public Health. 2017;5:258. doi:10.3389/fpubh.2017.00258"
    ),
    "nsf2015": (
        "Hirshkowitz M, et al. National Sleep Foundation's sleep time duration "
        "recommendations: methodology and results summary. "
        "Sleep Health. 2015;1(1):40-43. doi:10.1016/j.sleh.2014.12.010"
    ),
    "aasm2017": (
        "Watson NF, et al. Recommended Amount of Sleep for a Healthy Adult: A Joint "
        "Consensus Statement of the AASM and Sleep Research Society. "
        "J Clin Sleep Med. 2015;11(6):591-592. doi:10.5664/jcsm.4758"
    ),
    "who1999_noise": (
        "World Health Organization. Guidelines for Community Noise. WHO, Geneva, 1999. "
        "https://www.who.int/docstore/peh/noise/guidelines2.html"
    ),
    "who_bmi": (
        "World Health Organization. Obesity: preventing and managing the global epidemic. "
        "WHO Technical Report Series 894. Geneva: WHO, 2000."
    ),
    "cooper_vo2": (
        "The Cooper Institute. FITNESSGRAM/ACTIVITYGRAM Reference Guide (4th ed.). "
        "Dallas, TX: The Cooper Institute, 2010."
    ),
    "tudor_locke2011": (
        "Tudor-Locke C, Craig CL, Aoyagi Y, et al. How many steps/day are enough? "
        "For older adults and special populations. Int J Behav Nutr Phys Act. "
        "2011;8:80. doi:10.1186/1479-5868-8-80"
    ),
    "studenski2011": (
        "Studenski S, et al. Gait speed and survival in older adults. "
        "JAMA. 2011;305(1):50-58. doi:10.1001/jama.2010.1923"
    ),
}


# ---------------------------------------------------------------------------
# Dataclasses for typed benchmark categories
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RHRBracket:
    """Resting Heart Rate classification (bpm). Adult, general population."""

    athletic: int = 60       # < athletic → athlete range
    excellent: int = 70      # [60, 70) → excellent
    normal: int = 80         # [70, 80) → normal
    # ≥ 80 → elevated

    citation: str = field(
        default="Standard cardiology consensus; no single landmark paper.",
        compare=False,
        repr=False,
    )

    def classify(self, bpm: float) -> str:
        if bpm < self.athletic:
            return "athletic"
        if bpm < self.excellent:
            return "excellent"
        if bpm < self.normal:
            return "normal"
        return "elevated"


RHR = RHRBracket()


@dataclass(frozen=True)
class HRVPercentiles:
    """
    SDNN percentiles (ms) for males by age group, measured from wearables.

    Source: Umetani et al. 1998 (24h SDNN) adapted for short-term wearable
    measurements.  Wearable SDNN tends to be lower than Holter; values below
    reflect the <30y male cohort from Shaffer & Ginsberg 2017 normative data.
    """

    p25: float  # 25th percentile (ms)
    p50: float  # median (ms)
    p75: float  # 75th percentile (ms)
    citation_keys: tuple[str, ...] = field(default=("umetani1998", "shaffer2017"), compare=False, repr=False)

    def classify(self, sdnn_ms: float) -> str:
        if sdnn_ms >= self.p75:
            return "excellent"
        if sdnn_ms >= self.p50:
            return "good"
        if sdnn_ms >= self.p25:
            return "fair"
        return "low"


# Males <30 years (Apple Watch overnight SDNN proxy)
HRV_MALE_UNDER30 = HRVPercentiles(p25=40.0, p50=55.0, p75=65.0)


@dataclass(frozen=True)
class VO2MaxBracket:
    """
    VO₂max (mL/kg/min) classification for males aged 20-29.

    Source: Cooper Institute normative data (males, 20-29y).
    """

    poor: float = 36.0       # < poor
    below_avg: float = 42.0  # [poor, below_avg)
    average: float = 46.0    # [below_avg, average)
    good: float = 50.0       # [average, good)
    excellent: float = 56.0  # [good, excellent)
    # ≥ excellent → elite

    citation_key: str = field(default="cooper_vo2", compare=False, repr=False)

    def classify(self, vo2: float) -> str:
        if vo2 >= self.excellent:
            return "elite"
        if vo2 >= self.good:
            return "excellent"
        if vo2 >= self.average:
            return "good"
        if vo2 >= self.below_avg:
            return "average"
        if vo2 >= self.poor:
            return "below_average"
        return "poor"


VO2MAX_MALE_20_29 = VO2MaxBracket()


def hr_max_tanaka(age: int) -> float:
    """
    Theoretical maximum HR by Tanaka et al. 2001 formula: 208 − 0.7 × age.

    More accurate than Fox 1971 (220 − age), especially for older adults.
    Ref: tanaka2001
    """
    return 208.0 - 0.7 * age


def hr_max_fox(age: int) -> float:
    """
    Classic Fox 1971 formula: 220 − age. Still widely used but less precise.
    Ref: fox1971
    """
    return 220.0 - age


@dataclass(frozen=True)
class HRRecovery:
    """
    Heart Rate Recovery (HRR) 1 minute post-exercise.

    Cole et al. NEJM 1999: ≤12 bpm drop → abnormal (2× mortality risk).
    >18 bpm → good recovery.
    """

    abnormal_threshold: int = 12   # ≤ this → abnormal
    good_threshold: int = 18       # > this → good

    citation_key: str = field(default="cole1999", compare=False, repr=False)

    def classify(self, hrr1: float) -> str:
        if hrr1 <= self.abnormal_threshold:
            return "abnormal"
        if hrr1 >= self.good_threshold:
            return "good"
        return "moderate"


HRR = HRRecovery()


@dataclass(frozen=True)
class SleepBenchmarks:
    """
    Sleep quality benchmarks.

    Duration: NSF/AASM consensus (Hirshkowitz et al. 2015).
    Stage percentages: AASM scoring manual.
    Efficiency: standard clinical threshold (>85%).
    """

    min_hours: float = 7.0
    max_hours: float = 9.0
    deep_min_pct: float = 13.0   # % of total sleep
    deep_max_pct: float = 23.0
    rem_min_pct: float = 20.0
    rem_max_pct: float = 25.0
    efficiency_min: float = 85.0  # %

    citation_keys: tuple[str, ...] = field(
        default=("nsf2015", "aasm2017"), compare=False, repr=False
    )

    def classify_duration(self, hours: float) -> Literal["short", "optimal", "long"]:
        if hours < self.min_hours:
            return "short"
        if hours > self.max_hours:
            return "long"
        return "optimal"

    def classify_efficiency(self, pct: float) -> Literal["poor", "good"]:
        return "good" if pct >= self.efficiency_min else "poor"


SLEEP = SleepBenchmarks()


@dataclass(frozen=True)
class AudioBenchmarks:
    """
    Environmental noise exposure thresholds.

    WHO 1999 guidelines for community noise:
    - <70 dB: safe for chronic exposure
    - 85 dB: hearing risk if exposed >40h/week
    - 100 dB: hearing risk after 15 minutes
    """

    safe_chronic: float = 70.0    # dB(A) — safe for long-term exposure
    risk_prolonged: float = 85.0  # dB(A) — risk with >40h/week
    risk_short: float = 100.0     # dB(A) — risk after 15 min

    citation_key: str = field(default="who1999_noise", compare=False, repr=False)

    def classify(self, db: float) -> str:
        if db < self.safe_chronic:
            return "safe"
        if db < self.risk_prolonged:
            return "moderate"
        if db < self.risk_short:
            return "high"
        return "dangerous"


AUDIO = AudioBenchmarks()


@dataclass(frozen=True)
class GaitBenchmarks:
    """
    Walking gait benchmarks.

    Walking speed: Studenski et al. JAMA 2011 — >1.0 m/s associated with
    healthy aging.  Double support and asymmetry: clinical gait analysis norms.
    """

    min_walking_speed: float = 1.0    # m/s — below this is a health flag
    double_support_min: float = 20.0  # % of gait cycle
    double_support_max: float = 30.0
    asymmetry_max: float = 3.0        # % — above this is clinically relevant

    citation_key: str = field(default="studenski2011", compare=False, repr=False)

    def classify_speed(self, speed_ms: float) -> Literal["slow", "normal"]:
        return "normal" if speed_ms >= self.min_walking_speed else "slow"


GAIT = GaitBenchmarks()


@dataclass(frozen=True)
class BMIBenchmarks:
    """BMI classification per WHO 2000 technical report."""

    underweight: float = 18.5
    normal_max: float = 25.0
    overweight_max: float = 30.0

    citation_key: str = field(default="who_bmi", compare=False, repr=False)

    def classify(self, bmi: float) -> str:
        if bmi < self.underweight:
            return "underweight"
        if bmi < self.normal_max:
            return "normal"
        if bmi < self.overweight_max:
            return "overweight"
        return "obese"


BMI = BMIBenchmarks()

DAILY_STEPS_GOAL: int = 10_000
"""10,000 steps/day — widely used public health target (Tudor-Locke et al. 2011)."""
