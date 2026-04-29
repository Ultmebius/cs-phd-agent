"""Three-step Claude reasoning chain:

1. Extract structured professor profiles from raw web data
2. Compute technical match scores (resume vs professor)
3. Generate personalized bilingual outreach emails
"""

from __future__ import annotations

import json
import re

import anthropic
from tenacity import retry, stop_after_attempt, wait_exponential

from cs_phd_agent.config import Settings
from cs_phd_agent.models import (
    LabTrend,
    MatchScore,
    OutreachEmail,
    ProfessorProfile,
    Resume,
)


SYSTEM_EXTRACT = """You are an AI research analyst specializing in CS academia. Your job is to extract structured professor profiles from raw web page content and search results.

Rules:
- Only include information explicitly stated in the source text.
- If a field cannot be determined, leave it as an empty string / empty list.
- Extract papers from the last 3 years (2024-2026) when available.
- Classify research areas into standard CS subfields (e.g. "NLP", "Computer Vision", "ML Systems").
- Return ONLY valid JSON matching the requested schema — no explanation, no markdown."""

SYSTEM_MATCH = """You are a CS PhD admissions consultant. Your job is to honestly evaluate the technical match between an applicant's background and a professor's research.

Rules:
- Score honestly (0-100). If the match is weak, say so. Chinese applicants often overstate their fit — correct for this.
- Identify concrete research connections, not generic alignment.
- Be specific about technical skills the applicant has (or lacks).
- Return ONLY valid JSON — no explanation, no markdown."""

SYSTEM_EMAIL = """You are a professional academic writing assistant. Your job is to write highly personalized outreach emails (套磁信) for PhD applicants.

Rules:
- Reference specific papers or projects from the professor.
- Connect the applicant's background concretely to the professor's work.
- Be specific and genuine — no generic praise or templates.
- Keep the English body to 300-400 words.
- Provide a Chinese translation of the body as well.
- Use an appropriate academic tone — respectful but confident.
- Return ONLY valid JSON — no explanation, no markdown."""


class Analyzer:
    """Claude-powered reasoning engine for the 3-step analysis chain."""

    def __init__(self, settings: Settings) -> None:
        kwargs = {"api_key": settings.anthropic_api_key}
        if settings.anthropic_base_url:
            kwargs["base_url"] = settings.anthropic_base_url
        self._client = anthropic.Anthropic(**kwargs)
        self._model = settings.anthropic_model

    # ── Step 1: Extract professor profiles ──────────────────────────────

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=10))
    def extract_professors(self, raw_data: dict) -> list[ProfessorProfile]:
        """Parse raw Tavily output into structured ProfessorProfile objects."""
        snapshot = _summarize_raw_data(raw_data)
        prompt = (
            "Extract professor profiles from the following web research data "
            f"for {raw_data.get('university', 'the university')} "
            f"in the area of {raw_data.get('area', 'CS')}.\n\n"
            f"{snapshot}\n\n"
            'Return a JSON object with a single key "professors" whose value '
            "is a list of objects matching this schema:\n"
            "{\n"
            '  "name": str, "title": str, "university": str, '
            '"department": str, "homepage_url": str,\n'
            '  "research_areas": [str],\n'
            '  "lab": {"name": str, "url": str | null, "description": str},\n'
            '  "recent_papers": [{"title": str, "authors": [str], '
            '"year": int | null, "venue": str | null,\n'
            '    "abstract": str | null, "url": str | null, '
            '"tech_stack": [str]}],\n'
            '  "source_urls": [str]\n'
            "}"
        )

        resp = self._client.messages.create(
            model=self._model,
            max_tokens=4000,
            system=SYSTEM_EXTRACT,
            messages=[{"role": "user", "content": prompt}],
        )
        data = _parse_json(resp)
        return [ProfessorProfile(**p) for p in data.get("professors", [])]

    # ── Step 2: Match scoring ───────────────────────────────────────────

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=10))
    def analyze_match(
        self,
        resume: Resume | None,
        professor: ProfessorProfile,
        lab_research: str,
    ) -> tuple[MatchScore, LabTrend]:
        """Score technical fit between a resume and a professor."""
        resume_text = resume.raw_text if resume else "(no resume provided)"
        prof_json = professor.model_dump_json(indent=2)

        prompt = (
            "Evaluate the technical match between this applicant and professor.\n\n"
            f"--- APPLICANT RESUME ---\n{resume_text}\n\n"
            f"--- PROFESSOR PROFILE ---\n{prof_json}\n\n"
            f"--- LAB RESEARCH ---\n{lab_research}\n\n"
            "Return a JSON object with TWO keys:\n"
            '"match": {\n'
            '  "professor_name": str, "overall": float (0-100),\n'
            '  "research_interest": float (0-100),\n'
            '  "skill_alignment": float (0-100),\n'
            '  "experience_relevance": float (0-100),\n'
            '  "strengths": [str], "gaps": [str]\n'
            "}\n"
            '"trend": {\n'
            '  "professor_name": str,\n'
            '  "directions": [str],\n'
            '  "momentum": "rising" | "stable" | "declining" | "unknown",\n'
            '  "evidence": [str],\n'
            '  "funding_estimate": "well-funded" | "moderate" | "uncertain" | "unknown",\n'
            '  "funding_evidence": [str]\n'
            "}"
        )

        resp = self._client.messages.create(
            model=self._model,
            max_tokens=3000,
            system=SYSTEM_MATCH,
            messages=[{"role": "user", "content": prompt}],
        )
        data = _parse_json(resp)
        match_data = data.get("match", {})
        trend_data = data.get("trend", {})
        return MatchScore(**match_data), LabTrend(**trend_data)

    # ── Step 3: Email generation ───────────────────────────────────────

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=10))
    def generate_emails(
        self,
        resume: Resume | None,
        professors: list[ProfessorProfile],
        matches: list[MatchScore],
    ) -> list[OutreachEmail]:
        """Generate personalized bilingual outreach emails."""
        if not resume:
            return []

        emails: list[OutreachEmail] = []
        for prof, match in zip(professors, matches):
            emails.append(self._generate_one_email(resume, prof, match))
        return emails

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=10))
    def _generate_one_email(
        self,
        resume: Resume,
        professor: ProfessorProfile,
        match: MatchScore,
    ) -> OutreachEmail:
        prof_json = professor.model_dump_json(indent=2)
        resume_text = resume.raw_text

        prompt = (
            "Write a personalized outreach email from this PhD applicant "
            "to the professor.\n\n"
            f"--- APPLICANT RESUME ---\n{resume_text}\n\n"
            f"--- PROFESSOR PROFILE ---\n{prof_json}\n\n"
            f"--- MATCH SCORE ---\n{match.model_dump_json(indent=2)}\n\n"
            "Return a JSON object:\n"
            "{\n"
            '  "professor_name": str,\n'
            '  "subject": str (email subject line in English),\n'
            '  "body_en": str (300-400 word email body in English),\n'
            '  "body_zh": str (Chinese translation of the body),\n'
            '  "personalized_details": [str] (list of specific references '
            "that make this email personalized)\n"
            "}"
        )

        resp = self._client.messages.create(
            model=self._model,
            max_tokens=3000,
            system=SYSTEM_EMAIL,
            messages=[{"role": "user", "content": prompt}],
        )
        data = _parse_json(resp)
        return OutreachEmail(**data)


# ── Helpers ─────────────────────────────────────────────────────────────

def _summarize_raw_data(data: dict) -> str:
    """Build a concise text snapshot from the raw Tavily dict for Claude."""
    lines: list[str] = []
    lines.append(f"University: {data.get('university', '')}")
    lines.append(f"Area: {data.get('area', '')}")
    lines.append("")

    professors = data.get("professors", [])
    lines.append(f"--- Professor search results ({len(professors)} found) ---")
    for p in professors[:8]:
        title = p.get("title", "?")
        url = p.get("url", "")
        snippet = (p.get("content") or "")[:300]
        lines.append(f"  • {title}")
        lines.append(f"    URL: {url}")
        if snippet:
            lines.append(f"    Snippet: {snippet}")
        lines.append("")

    profiles = data.get("profiles", [])
    if profiles:
        lines.append(f"--- Extracted page content ({len(profiles)} pages) ---")
        for i, content in enumerate(profiles[:3]):
            lines.append(f"  [Page {i + 1}] {content[:2000]}")
            lines.append("")

    papers = data.get("papers", [])
    if papers:
        lines.append(f"--- Paper search results ({len(papers)} found) ---")
        for p in papers[:10]:
            content = (p.get("content") or "")[:300]
            lines.append(f"  • {p.get('title', '?')}")
            if content:
                lines.append(f"    {content}")
        lines.append("")

    lab = data.get("lab_research", [])
    if lab:
        lines.append(f"--- Lab research ({len(lab)} entries) ---")
        for entry in lab[:3]:
            lines.append(f"  [{entry.get('professor', '?')}]")
            lines.append(f"  {(entry.get('text') or '')[:2000]}")
            lines.append("")

    return "\n".join(lines)


def _parse_json(response: anthropic.types.Message) -> dict:
    """Extract a JSON dict from a Claude response, with fallback."""
    text = response.content[0].text

    # Direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try extracting from markdown code fences
    m = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass

    # Last resort: find first { ... } block
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not parse JSON from Claude response:\n{text[:500]}")
