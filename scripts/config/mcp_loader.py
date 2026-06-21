"""
MCP configuration loader — parses MCP server definitions.

Supports two formats:
1. Environment variable (MCP_SERVERS=airbnb:stdio://...,weather:http://...)
2. JSON file (mcp_config.json in this directory)
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from scripts.config.settings import settings

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent / "mcp_config.json"


def load_mcp_config(path: str | Path | None = None) -> dict[str, Any]:
    """
    Load MCP configuration.

    Priority:
    1. Explicit `path` argument
    2. JSON file at default location
    3. Environment variable MCP_SERVERS
    4. Empty dict (no MCP servers)

    Returns:
        Dict like:
        {
            "servers": [
                {"name": "airbnb", "url": "stdio://airbnb-mcp", "transport": "stdio"},
                ...
            ]
        }
    """
    # Try JSON file first
    config_path = Path(path) if path else DEFAULT_CONFIG_PATH
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                file_config = json.load(f)
            logger.info("Loaded MCP config from %s", config_path)
            return file_config
        except json.JSONDecodeError as e:
            logger.warning("Invalid JSON in %s: %s", config_path, e)

    # Fall back to env var
    pairs = settings.mcp_server_pairs
    if pairs:
        logger.info("Loaded %d MCP server(s) from environment", len(pairs))
        return {
            "servers": [
                {
                    "name": name,
                    "url": url,
                    "transport": "stdio" if url.startswith("stdio://") else "http",
                }
                for name, url in pairs
            ]
        }

    logger.info("No MCP servers configured")
    return {"servers": []}


def get_mcp_server(name: str) -> dict[str, Any] | None:
    """Get a specific MCP server config by name."""
    config = load_mcp_config()
    for server in config.get("servers", []):
        if server.get("name") == name:
            return server
    return None
