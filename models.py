from datetime import datetime
from pydantic import BaseModel, ConfigDict
from typing import Literal


# ── Resume ──────────────────────────────────────────────────────────────

class Education(BaseModel):
    institution: str = ""
    degree: str = ""
    major: str = ""
    gpa: float | None = None
    year_start: int | None = None
    year_end: int | None = None


class Experience(BaseModel):
    type: Literal["research", "industry", "teaching", "other"] = "other"
    organization: str = ""
    role: str = ""
    duration: str = ""
    highlights: list[str] = []
    relevant_skills: list[str] = []


class Resume(BaseModel):
    model_config = ConfigDict(extra="ignore")
    raw_text: str
    name: str | None = None
    education: list[Education] = []
    experiences: list[Experience] = []
    technical_skills: list[str] = []
    research_interests: list[str] = []
    publications: list[str] = []
    targeted_areas: list[str] = []


# ── Professor / Lab ─────────────────────────────────────────────────────

class PaperSummary(BaseModel):
    model_config = ConfigDict(extra="ignore")
    title: str = ""
    authors: list[str] = []
    year: int | None = None
    venue: str | None = None
    abstract: str | None = None
    url: str | None = None
    tech_stack: list[str] = []


class LabInfo(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str = ""
    url: str | None = None
    description: str = ""


class ProfessorProfile(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str
    title: str = ""
    university: str = ""
    department: str = ""
    homepage_url: str = ""
    research_areas: list[str] = []
    lab: LabInfo = LabInfo()
    recent_papers: list[PaperSummary] = []
    source_urls: list[str] = []


# ── Analysis Results ────────────────────────────────────────────────────

class MatchScore(BaseModel):
    model_config = ConfigDict(extra="ignore")
    professor_name: str
    overall: float = 0.0
    research_interest: float = 0.0
    skill_alignment: float = 0.0
    experience_relevance: float = 0.0
    strengths: list[str] = []
    gaps: list[str] = []


class LabTrend(BaseModel):
    model_config = ConfigDict(extra="ignore")
    professor_name: str
    directions: list[str] = []
    momentum: Literal["rising", "stable", "declining", "unknown"] = "unknown"
    evidence: list[str] = []
    funding_estimate: Literal["well-funded", "moderate", "uncertain", "unknown"] = "unknown"
    funding_evidence: list[str] = []


class OutreachEmail(BaseModel):
    model_config = ConfigDict(extra="ignore")
    professor_name: str
    subject: str = ""
    body_en: str = ""
    body_zh: str = ""
    personalized_details: list[str] = []


# ── Report ──────────────────────────────────────────────────────────────

class ResearchReport(BaseModel):
    model_config = ConfigDict(extra="ignore")
    target_university: str
    target_area: str
    generated_at: datetime = datetime.now()
    resume_summary: Resume | None = None
    professors: list[ProfessorProfile] = []
    scores: list[MatchScore] = []
    trends: list[LabTrend] = []
    emails: list[OutreachEmail] = []
    summary: str = ""
    raw_sources: list[str] = []
