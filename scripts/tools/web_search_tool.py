"""
Web Search Tool — uses Tavily API for general web research.
"""
from __future__ import annotations

import os
from typing import Any

from langchain_core.tools import tool
from pydantic import Field

from scripts.config.settings import settings


@tool
async def web_search(
    query: str = Field(description="Search query"),
    num_results: int = Field(default=3, description="Number of results (1-10)"),
) -> dict[str, Any]:
    """
    Search the web for general information.

    Use this for travel guides, attractions, news about destinations, etc.
    Returns a dict with `results` (title, url, snippet).
    """
    api_key = settings.tavily_api_key or os.getenv("TAVILY_API_KEY")

    if not api_key:
        # Mock results when no key is set
        return {
            "query": query,
            "source": "mock",
            "results": [
                {
                    "title": f"Top 3 things to do in {query}",
                    "url": "https://example.com/guide",
                    "snippet": f"A comprehensive guide to {query}...",
                },
            ],
        }

    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=api_key)
        results = client.search(query, max_results=num_results)
        return {
            "query": query,
            "source": "tavily",
            "results": results.get("results", []),
        }
    except Exception as e:
        return {"query": query, "error": str(e), "results": []}
