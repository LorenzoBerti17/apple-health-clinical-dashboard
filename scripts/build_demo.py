"""
Build the public demo dashboard using synthetic data.

Output: demo/index.html  (committed to the repo for GitHub Pages)

Usage:
    uv run python scripts/build_demo.py
"""

from __future__ import annotations

from pathlib import Path

from health_dashboard.analyze import build_report
from health_dashboard.render import render_dashboard
from health_dashboard.synthetic import generate_demo_data

ROOT = Path(__file__).parent.parent
OUTPUT = ROOT / "demo" / "index.html"
TEMPLATE_DIR = ROOT / "dashboard"


def main() -> None:
    print("Generating synthetic data…")
    health, sleep, workouts = generate_demo_data()
    print(f"  {len(health)} health records, {len(sleep)} sleep records, {len(workouts)} workouts")

    print("Building report…")
    report = build_report(health, sleep, workouts, age=24)

    print(f"Rendering to {OUTPUT}…")
    render_dashboard(report, OUTPUT, template_dir=TEMPLATE_DIR)
    print("Done.")


if __name__ == "__main__":
    main()
