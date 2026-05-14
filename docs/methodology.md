# Methodology & Clinical Benchmarks

All thresholds used in the analysis pipeline are centralised in
`src/health_dashboard/benchmarks.py` and cited below with the original source.

## Cardiovascular

### Resting Heart Rate
| Classification | Range | Source |
|---|---|---|
| Athletic | < 60 bpm | Standard cardiology consensus |
| Excellent | 60–69 bpm | — |
| Normal | 70–79 bpm | — |
| Elevated | ≥ 80 bpm | — |

### Heart Rate Variability (SDNN)
Wearable SDNN tends to be lower than 24h Holter SDNN.  Percentiles below are
for males <30 years adapted from Shaffer & Ginsberg 2017 normative data.

| Percentile | Value |
|---|---|
| 25th | 40 ms |
| 50th (median) | 55 ms |
| 75th | 65 ms |

**Sources:**
- Umetani K, et al. *J Am Coll Cardiol.* 1998;31(3):593-601.
- Shaffer F, Ginsberg JP. *Front Public Health.* 2017;5:258.

### VO₂max
Cooper Institute norms for males aged 20–29:

| Classification | Range |
|---|---|
| Poor | < 36 mL/kg/min |
| Below Average | 36–42 |
| Average | 42–46 |
| Good | 46–50 |
| Excellent | 50–56 |
| Elite | ≥ 56 |

**Source:** The Cooper Institute. *FITNESSGRAM/ACTIVITYGRAM Reference Guide* (4th ed.), 2010.

### Maximum Heart Rate
- **Tanaka 2001**: 208 − 0.7 × age — preferred formula, more accurate for all ages.
- **Fox 1971**: 220 − age — legacy formula, still common.

**Source:** Tanaka H, et al. *J Am Coll Cardiol.* 2001;37(1):153-156.

### Heart Rate Recovery (1 min post-exercise)
- ≤ 12 bpm: **abnormal** — associated with 2× mortality risk.
- 12–18 bpm: **moderate**.
- > 18 bpm: **good**.

**Source:** Cole CR, et al. *N Engl J Med.* 1999;341(18):1351-1357.

---

## Sleep

| Metric | Target | Source |
|---|---|---|
| Duration | 7–9 h | Hirshkowitz et al. *Sleep Health* 2015 (NSF); Watson et al. *JCSM* 2015 (AASM) |
| Deep (N3) | 13–23% of TST | AASM scoring manual |
| REM | 20–25% of TST | AASM scoring manual |
| Efficiency | > 85% | Standard clinical threshold |

---

## Environmental Audio

**Source:** World Health Organization. *Guidelines for Community Noise.* WHO, Geneva, 1999.

| Level | Risk |
|---|---|
| < 70 dB(A) | Safe for chronic exposure |
| 85 dB(A) | Hearing risk if > 40h/week |
| 100 dB(A) | Hearing risk after 15 minutes |

---

## Gait

| Metric | Threshold | Source |
|---|---|---|
| Walking speed | > 1.0 m/s (healthy aging) | Studenski et al. *JAMA* 2011;305(1):50-58 |
| Double support | 20–30% of gait cycle | Clinical gait analysis norms |
| Step asymmetry | < 3% (clinically relevant above) | Clinical gait analysis norms |

---

## BMI

**Source:** WHO. *Obesity: preventing and managing the global epidemic.* WHO Technical Report Series 894, 2000.

| Classification | BMI |
|---|---|
| Underweight | < 18.5 |
| Normal | 18.5–24.9 |
| Overweight | 25.0–29.9 |
| Obese | ≥ 30.0 |
