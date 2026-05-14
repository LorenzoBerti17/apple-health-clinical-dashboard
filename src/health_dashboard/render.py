"""
Render a HealthReport to a standalone HTML dashboard.

Uses Jinja2 to inject JSON data into the template; Chart.js handles all
visualisation client-side.  The output is a single self-contained HTML file
that works without a web server (file:// or GitHub Pages).
"""

from __future__ import annotations

import json
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from health_dashboard.analyze import HealthReport, report_to_dict

_DASHBOARD_DIR = Path(__file__).parent.parent.parent / "dashboard"


def render_dashboard(
    report: HealthReport,
    output_path: Path,
    template_dir: Path | None = None,
) -> Path:
    """
    Render report to output_path as a standalone HTML file.

    Returns the resolved output path.
    """
    tdir = template_dir or _DASHBOARD_DIR
    env = Environment(
        loader=FileSystemLoader(str(tdir)),
        autoescape=select_autoescape(["html"]),
    )
    template = env.get_template("template.html")

    data = report_to_dict(report)
    html = template.render(
        data_json=json.dumps(data, ensure_ascii=False, default=str),
        report=report,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    return output_path
