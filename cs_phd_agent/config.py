import os
from functools import cached_property
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class Settings:
    """Read configuration from environment variables.  No .env required —
    export env vars directly or cp .env.example .env.
    """

    @cached_property
    def tavily_api_key(self) -> str:
        val = os.environ.get("TAVILY_API_KEY", "")
        if not val:
            raise ValueError(
                "TAVILY_API_KEY not set. "
                "Copy .env.example → .env and add your key, or export it."
            )
        return val

    @cached_property
    def anthropic_api_key(self) -> str:
        val = os.environ.get("ANTHROPIC_API_KEY", "")
        if not val:
            raise ValueError(
                "ANTHROPIC_API_KEY not set. "
                "Copy .env.example → .env and add your key, or export it."
            )
        return val

    @cached_property
    def anthropic_base_url(self) -> str | None:
        return os.environ.get("ANTHROPIC_BASE_URL") or None

    @cached_property
    def anthropic_model(self) -> str:
        return os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")

    @cached_property
    def max_retries(self) -> int:
        return int(os.environ.get("MAX_RETRIES", "3"))

    @cached_property
    def output_dir(self) -> Path:
        return Path(os.environ.get("OUTPUT_DIR", "./output"))

    @cached_property
    def top_k_professors(self) -> int:
        return int(os.environ.get("TOP_K_PROFESSORS", "5"))
