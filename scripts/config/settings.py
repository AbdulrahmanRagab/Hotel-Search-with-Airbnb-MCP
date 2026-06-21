"""
Pydantic BaseSettings — typed configuration loaded from .env.

Why pydantic-settings?
- Auto-validates types (no more `os.getenv("FOO")` returning str when you need int)
- Auto-loads from .env file
- Single source of truth for all config
- IDE autocomplete works
"""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from .env + environment variables."""

    # ── LLM API Keys ────────────────────────────────────────
    groq_api_key: str = ""
    llm_model: str = "llama-3.3-70b-versatile"
    llm_temperature: float = 0.0

    # ── Tool API Keys ───────────────────────────────────────
    tavily_api_key: str = ""
    openweather_api_key: str = "mock"

    # ── MCP Servers ─────────────────────────────────────────
    mcp_servers: str = "airbnb:stdio://airbnb-mcp"

    # ── Database ────────────────────────────────────────────
    postgres_url: str = "postgresql://user:pass@localhost:5432/hotel_db"
    checkpointer: str = "memory"   # "memory" or "postgres"

    # ── Debug ───────────────────────────────────────────────
    debug_mode: bool = True
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def mcp_server_pairs(self) -> list[tuple[str, str]]:
        """Parse MCP_SERVERS env var into list of (name, url) tuples."""
        pairs = []
        for entry in self.mcp_servers.split(","):
            entry = entry.strip()
            if not entry:
                continue
            if ":" in entry:
                name, url = entry.split(":", 1)
                pairs.append((name.strip(), url.strip()))
        return pairs


# Singleton — import this everywhere
settings = Settings()
