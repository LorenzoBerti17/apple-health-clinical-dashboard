"""
Build dashboard from personal Apple Health export.

Reads data/export.zip (or data/export.xml) — gitignored, never committed.
Output goes to out/personal/index.html — also gitignored.

Usage:
    uv run python scripts/build_personal.py
    uv run python scripts/build_personal.py --input data/my_export.zip
"""

from __future__ import annotations

import argparse
from pathlib import Path

from health_dashboard.analyze import build_report
from health_dashboard.parse import parse_export
from health_dashboard.render import render_dashboard

ROOT = Path(__file__).parent.parent
DEFAULT_INPUT = ROOT / "data" / "export.zip"
OUTPUT = ROOT / "out" / "personal" / "index.html"
TEMPLATE_DIR = ROOT / "dashboard"


def main() -> None:
    parser = argparse.ArgumentParser(description="Build personal health dashboard")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--age", type=int, default=24)
    args = parser.parse_args()

    source: Path = args.input
    if not source.exists():
        print(f"Error: {source} not found.")
        print("Place your Apple Health export at data/export.zip (gitignored).")
        raise SystemExit(1)

    print(f"Parsing {source}…")
    health, sleep, workouts = parse_export(source)
    print(
        f"  {len(health)} health records, {len(sleep)} sleep records, "
        f"{len(workouts)} workouts (post 2025-12-01)"
    )

    print("Building report…")
    report = build_report(health, sleep, workouts, age=args.age)

    print(f"Rendering to {OUTPUT}…")
    render_dashboard(report, OUTPUT, template_dir=TEMPLATE_DIR)
    print(f"Done. Open: file://{OUTPUT.resolve()}")


if __name__ == "__main__":
    main()
