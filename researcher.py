"""Web research via Tavily — discover professors, extract pages, find
papers, and research lab trends."""

from __future__ import annotations

from tavily import TavilyClient
from tenacity import retry, stop_after_attempt, wait_exponential

from cs_phd_agent.config import Settings


class WebResearcher:
    """Orchestrates Tavily calls for each university."""

    def __init__(self, settings: Settings) -> None:
        self._client = TavilyClient(api_key=settings.tavily_api_key)
        self._max_retries = settings.max_retries

    # ── public orchestration ────────────────────────────────────────────

    def research_university(self, university: str, area: str, deep: bool = False) -> dict:
        """Full research pipeline for one university.

        Returns a dict with keys:
          professors   — list of raw search results (dicts)
          profiles     — extracted page content (list[str])
          papers       — list of paper search results (dicts)
          lab_research — list of lab research texts (list[str])
          source_urls  — all URLs collected (list[str])
        """
        result: dict = {
            "university": university,
            "area": area,
            "professors": [],
            "profiles": [],
            "papers": [],
            "lab_research": [],
            "source_urls": [],
        }

        # Phase 1: find professor homepages
        prof_results = self._search_professors(university, area)
        result["professors"] = prof_results
        prof_urls = [r["url"] for r in prof_results if r.get("url")]
        result["source_urls"].extend(prof_urls)

        # Phase 2: extract full page content
        if prof_urls:
            extracted = self._extract_pages(prof_urls)
            for item in (extracted.get("results") or []):
                content = item.get("content", "")
                if content:
                    result["profiles"].append(content)

        # Phase 3: for each professor found, search their recent papers
        for prof in prof_results[:self._max_retries]:  # limit to retry-count profs
            prof_name = prof.get("title", "").replace(" - ", " ").split(" |")[0].strip()
            if not prof_name:
                continue
            papers = self._search_recent_papers(prof_name, university)
            result["papers"].extend(papers)
            result["source_urls"].extend(
                p["url"] for p in papers if p.get("url")
            )

            # Phase 4: deep lab research (if deep flag or first few profs)
            if deep or len(result["lab_research"]) < 3:
                lab_text = self._research_lab(prof_name, university, area)
                if lab_text:
                    result["lab_research"].append({
                        "professor": prof_name,
                        "text": lab_text,
                    })

        # Deduplicate URLs
        result["source_urls"] = list(dict.fromkeys(result["source_urls"]))
        return result

    # ── private Tavily wrappers ─────────────────────────────────────────

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=10))
    def _search_professors(self, university: str, area: str) -> list[dict]:
        resp = self._client.search(
            query=f"CS faculty {university} {area} professor homepage research",
            search_depth="advanced",
            max_results=10,
            include_raw_content=True,
        )
        return (resp.get("results") or [])

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=10))
    def _extract_pages(self, urls: list[str]) -> dict:
        return self._client.extract(
            urls=urls,
            extract_depth="advanced",
        )

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=10))
    def _search_recent_papers(self, professor_name: str, university: str) -> list[dict]:
        resp = self._client.search(
            query=f"{professor_name} {university} publications 2024 2025 2026",
            search_depth="advanced",
            max_results=5,
            include_raw_content=True,
        )
        return (resp.get("results") or [])

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, max=10))
    def _research_lab(self, professor_name: str, university: str, area: str) -> str:
        from tavily import TavilyClient
        # research() is a top-level function, not a client method in v0.7.x
        resp = self._client.search(
            query=f"{professor_name} lab {university} research trends funding {area}",
            search_depth="advanced",
            max_results=5,
            include_raw_content=True,
        )
        parts = []
        for r in (resp.get("results") or []):
            content = r.get("raw_content") or r.get("content") or ""
            if content:
                parts.append(content)
        return "\n\n".join(parts) if parts else ""
