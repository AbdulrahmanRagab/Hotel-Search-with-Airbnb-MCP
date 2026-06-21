"""
Format Results Tool — custom post-processing for hotel listings.

Sometimes the LLM needs help ranking, filtering, or formatting
raw results from other tools. This tool does that.
"""
from __future__ import annotations

from typing import Any

from langchain_core.tools import tool
from pydantic import Field


@tool
async def format_results(
    results: list[dict[str, Any]] = Field(description="List of raw result dicts"),
    sort_by: str = Field(default="rating", description="Field to sort by: 'rating', 'price', 'distance'"),
    top_n: int = Field(default=3, description="Number of top results to return"),
) -> dict[str, Any]:
    """
    Sort and filter raw search results.

    Useful when you have a long list of hotels and want to show
    only the best ones sorted by rating, price, or distance.
    """
    if not results:
        return {"sorted": [], "total_input": 0, "returned": 0}

    # Determine sort key
    sort_keys = {
        "rating": lambda r: r.get("rating", 0),
        "price": lambda r: r.get("price_per_night", 0),
        "distance": lambda r: r.get("distance_to_center_km", 999),
    }
    key_fn = sort_keys.get(sort_by, sort_keys["rating"])

    # Reverse=True for rating (higher better), False for price/distance (lower better)
    reverse = sort_by == "rating"

    sorted_results = sorted(results, key=key_fn, reverse=reverse)
    top = sorted_results[:top_n]

    return {
        "sorted": top,
        "total_input": len(results),
        "returned": len(top),
        "sort_by": sort_by,
    }
