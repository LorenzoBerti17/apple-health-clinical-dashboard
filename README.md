# Apple Health Clinical Dashboard

Reproducible Python pipeline that turns an Apple Health export into a
self-contained clinical dashboard, with every threshold backed by a
peer-reviewed source.

> **Demo (synthetic data):** _to be deployed on GitHub Pages_
>
> Personal data is never committed — see `.gitignore`.

---

## What it does

1. **Parse** — streams `export.xml` with `lxml.iterparse` (constant memory).
2. **Analyze** — computes per-domain clinical statistics, OLS trends and Pearson correlations across cardio, sleep, activity, running, audio and gait.
3. **Render** — produces a single-file HTML dashboard (Chart.js, dark theme, mobile-friendly).

All clinical thresholds — RHR, HRV (Umetani, Shaffer & Ginsberg), VO₂max (Cooper), HR max (Tanaka 2001), HR Recovery (Cole NEJM 1999), sleep (NSF/AASM), environmental audio (WHO 1999), gait (Studenski JAMA 2011), BMI (WHO) — are centralised in `src/health_dashboard/benchmarks.py` with full citations. See [docs/methodology.md](docs/methodology.md).

## Quick start

```bash
uv sync --extra dev
uv run pytest                          # 70 tests
uv run python scripts/build_demo.py    # → demo/index.html (synthetic)
```

For personal data:

```bash
# place your Apple Health export at data/export.zip (gitignored)
uv run python scripts/build_personal.py
# → out/personal/index.html
```

## Stack

Python 3.12 · uv · lxml · pandas · numpy · scipy · pydantic · Jinja2 · Chart.js 4

## License

MIT
