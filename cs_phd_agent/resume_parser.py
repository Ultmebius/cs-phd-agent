from pathlib import Path

from cs_phd_agent.models import Resume


def parse_resume(path: str | Path) -> Resume:
    """Extract raw text from a PDF resume.

    Tries pdfplumber first (best CJK / layout support), falls back to
    pypdf.  Only populates ``raw_text`` — Claude handles semantic parsing
    later in the pipeline.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Resume not found: {path}")

    text = _try_pdfplumber(path)
    if not text or not text.strip():
        text = _try_pypdf(path)

    if not text or not text.strip():
        raise ValueError(
            f"Could not extract any text from {path.name}. "
            "Try converting to a plain-text file and passing it directly."
        )

    return Resume(raw_text=text.strip())


def _try_pdfplumber(path: Path) -> str | None:
    try:
        import pdfplumber
    except ImportError:
        return None
    try:
        with pdfplumber.open(path) as pdf:
            return "\n".join(
                page.extract_text() or "" for page in pdf.pages
            )
    except Exception:
        return None


def _try_pypdf(path: Path) -> str | None:
    try:
        from pypdf import PdfReader
    except ImportError:
        return None
    try:
        reader = PdfReader(path)
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception:
        return None
