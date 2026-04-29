"""Render a ResearchReport to markdown (via Jinja2) and JSON."""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, PackageLoader, select_autoescape

from cs_phd_agent.models import ResearchReport


def render_report(report: ResearchReport, output_dir: Path) -> Path:
    """Write report as .md (Jinja2 template) and .json.

    Returns the path to the markdown file.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = report.generated_at.strftime("%Y%m%d_%H%M%S")
    slug = _slugify(report.target_university)[:60]

    # Markdown
    env = Environment(
        loader=PackageLoader("cs_phd_agent", "templates"),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = env.get_template("report.md.j2")
    md_content = template.render(report=report)

    md_path = output_dir / f"report_{slug}_{timestamp}.md"
    md_path.write_text(md_content, encoding="utf-8")
    print(f"  📄 Report: {md_path}")

    # JSON
    json_path = md_path.with_suffix(".json")
    json_path.write_text(report.model_dump_json(indent=2, exclude_none=True), encoding="utf-8")
    print(f"  📊 Data:   {json_path}")

    return md_path


def _slugify(text: str) -> str:
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in text).strip("_").lower()
