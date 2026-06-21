from __future__ import annotations

from langchain_core.tools import BaseTool

from scripts.tools.airbnb_tool import airbnb_search
from scripts.tools.format_results_tool import format_results
from scripts.tools.weather_tool import get_weather
from scripts.tools.web_search_tool import web_search

ALL_TOOLS: list[BaseTool] = [
    airbnb_search,
    web_search,
    get_weather,
    format_results,
]

TOOL_MAP: dict[str, BaseTool] = {t.name: t for t in ALL_TOOLS}
