"""Pipeline orchestrator — wires resume parsing, web research, Claude
analysis, and report assembly together."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from cs_phd_agent.analyzer import Analyzer
from cs_phd_agent.config import Settings
from cs_phd_agent.models import ResearchReport
from cs_phd_agent.report import render_report
from cs_phd_agent.researcher import WebResearcher
from cs_phd_agent.resume_parser import parse_resume


class CSPhDAgent:
    """Top-level agent.  Orchestrates the full pipeline."""

    def __init__(self) -> None:
        self._settings = Settings()
        self._researcher = WebResearcher(self._settings)
        self._analyzer = Analyzer(self._settings)

    def run(
        self,
        universities: list[str],
        research_area: str,
        resume_path: str | Path | None = None,
        deep: bool = False,
        output_dir: str | Path | None = None,
    ) -> ResearchReport:
        """Execute the full research + analysis pipeline.

        Args:
            universities: List of university names (e.g. ["Stanford", "MIT"]).
            research_area: Research area / subfield (e.g. "NLP").
            resume_path: Optional path to a PDF resume.
            deep: If True, perform deeper lab research (more Tavily calls).
            output_dir: Where to write output files (default: settings).

        Returns:
            A ResearchReport with all findings.
        """
        out_dir = Path(output_dir or self._settings.output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        # ── Phase 0: Parse resume ──────────────────────────────────────
        resume = None
        if resume_path:
            resume = parse_resume(resume_path)

        # ── Phase 1: Web research (per university) ──────────────────────
        all_professors = []
        all_scores = []
        all_trends = []
        all_emails = []
        all_sources: list[str] = []

        for uni in universities:
            raw = self._researcher.research_university(uni, research_area, deep)
            all_sources.extend(raw.get("source_urls", []))

            # Phase 2a: Extract professor profiles
            professors = self._analyzer.extract_professors(raw)
            all_professors.extend(professors)

            # Phase 2b: Match scores + lab trends (per professor)
            lab_map: dict[str, str] = {}
            for entry in raw.get("lab_research", []):
                lab_map[entry.get("professor", "")] = entry.get("text", "")

            for prof in professors:
                lab_text = lab_map.get(prof.name, "")
                score, trend = self._analyzer.analyze_match(
                    resume, prof, lab_text
                )
                all_scores.append(score)
                all_trends.append(trend)

            # Phase 2c: Generate outreach emails
            if resume:
                emails = self._analyzer.generate_emails(
                    resume, professors, all_scores[-len(professors):]
                )
                all_emails.extend(emails)

        # ── Phase 3: Assemble report ────────────────────────────────────
        summary = _build_summary(all_scores, all_trends)

        report = ResearchReport(
            target_university=", ".join(universities),
            target_area=research_area,
            generated_at=datetime.now(),
            resume_summary=resume,
            professors=all_professors,
            scores=all_scores,
            trends=all_trends,
            emails=all_emails,
            summary=summary,
            raw_sources=list(dict.fromkeys(all_sources)),
        )

        # Write outputs
        render_report(report, out_dir)
        return report


def _build_summary(scores, trends) -> str:
    """One-paragraph executive summary from scores and trends."""
    if not scores:
        return "No match scores computed (resume was not provided)."
    top = sorted(scores, key=lambda s: s.overall, reverse=True)
    lines = [
        f"Research complete. Top {len(top)} professor(s) analyzed.",
        f"Best match: {top[0].professor_name} (overall: {top[0].overall:.0f}/100).",
    ]
    for t in trends[:3]:
        lines.append(
            f"{t.professor_name}: momentum={t.momentum}, "
            f"funding={t.funding_estimate}."
        )
    return " ".join(lines)
