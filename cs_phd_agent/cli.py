"""CLI entry point for cs-phd-agent."""

from __future__ import annotations

import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from cs_phd_agent.main import CSPhDAgent

console = Console()


@click.command()
@click.argument("universities", nargs=-1, required=True)
@click.option("--area", "-a", required=True, help="Research area / subfield")
@click.option("--resume", "-r", type=click.Path(exists=True), help="Path to CV (PDF)")
@click.option("--deep", is_flag=True, help="Deep research mode (more Tavily calls)")
@click.option("--output", "-o", default="./output", help="Output directory", show_default=True)
def main(
    universities: tuple[str, ...],
    area: str,
    resume: str | None,
    deep: bool,
    output: str,
) -> None:
    """CS PhD Application Research Agent.

    Research professors, labs, and find your best-fit programs at top
    universities. Provide target school names and a research area.

    Example:

        cs-phd-agent Stanford MIT --area NLP --resume ./cv.pdf
    """
    # ── Run pipeline ───────────────────────────────────────────────────
    console.print(f"\n[bold]🔬 CS PhD Research Agent[/bold]")
    console.print(f"   Universities: {', '.join(universities)}")
    console.print(f"   Area:         {area}")
    if resume:
        console.print(f"   Resume:       {resume}")
    console.print()

    try:
        agent = CSPhDAgent()
        report = agent.run(
            universities=list(universities),
            research_area=area,
            resume_path=Path(resume) if resume else None,
            deep=deep,
            output_dir=Path(output),
        )
    except Exception as exc:
        console.print(f"[red]Error:[/red] {exc}")
        sys.exit(1)

    # ── Print summary ───────────────────────────────────────────────────
    console.print(f"\n[bold green]✓ Research complete![/bold green]")
    console.print(f"   Summary: {report.summary}")
    console.print()

    if report.scores:
        table = Table(title="Match Scores (Top Matches)")
        table.add_column("Professor", style="cyan")
        table.add_column("University")
        table.add_column("Overall", justify="right")
        table.add_column("Interest", justify="right")
        table.add_column("Skills", justify="right")
        table.add_column("Experience", justify="right")

        sorted_scores = sorted(report.scores, key=lambda s: s.overall, reverse=True)
        prof_map = {p.name: p.university for p in report.professors}
        for s in sorted_scores[:5]:
            table.add_row(
                s.professor_name,
                prof_map.get(s.professor_name, ""),
                f"{s.overall:.0f}",
                f"{s.research_interest:.0f}",
                f"{s.skill_alignment:.0f}",
                f"{s.experience_relevance:.0f}",
            )
        console.print(table)

    if report.emails:
        console.print(f"\n[bold]✉️  Outreach emails generated:[/bold] {len(report.emails)}")

    console.print(f"\n[dim]Sources consulted: {len(report.raw_sources)} URLs[/dim]")
