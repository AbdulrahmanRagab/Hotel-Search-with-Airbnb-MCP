from __future__ import annotations

import copy
import logging
from typing import Any

from langchain_core.messages import SystemMessage
from langchain_groq import ChatGroq
from tenacity import retry, stop_after_attempt, wait_exponential

from scripts.config.settings import settings
from scripts.prompts.prompt_builder import build_prompt
from scripts.debug import log_entry, show_error, show_prompt
from scripts.state import HotelSearchState
from scripts.tools import ALL_TOOLS

logger = logging.getLogger(__name__)

_llm_instance = None
_llm_with_tools_instance = None


def _get_llm_with_tools():
    global _llm_instance, _llm_with_tools_instance
    if _llm_with_tools_instance is None:
        _llm_instance = ChatGroq(
            model=settings.llm_model,
            temperature=settings.llm_temperature,
            api_key=settings.groq_api_key or None,
        )
        _llm_with_tools_instance = _llm_instance.bind_tools(ALL_TOOLS)
    return _llm_with_tools_instance


def _safe_get_preferences(params: Any) -> list[str]:
    if params is None:
        return []
    if hasattr(params, "preferences"):
        return params.preferences or []
    if isinstance(params, dict):
        return params.get("preferences", []) or []
    return []


def _safe_get_currency(params: Any) -> str:
    if params is None:
        return "USD"
    if hasattr(params, "currency"):
        return params.currency or "USD"
    if isinstance(params, dict):
        return params.get("currency", "USD") or "USD"
    return "USD"


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    reraise=True,
)
async def _call_llm_with_retry(messages: list) -> Any:
    llm = _get_llm_with_tools()
    return await llm.ainvoke(messages)


async def tool_call_node(state: HotelSearchState) -> dict[str, Any]:
    params = state.get("search_params")
    messages = state.get("messages", [])

    tool_names = [t.name for t in ALL_TOOLS]
    preferences = _safe_get_preferences(params)
    currency = _safe_get_currency(params)

    system_prompt = build_prompt(
        "system.j2",
        currency=currency,
        tool_names=tool_names,
        preferences=preferences,
        extra_instructions=(
            "The user has already provided search parameters. "
            "Call the airbnb_search tool now to fetch listings."
            if params
            else "Ask the user for missing information before searching."
        ),
    )

    show_prompt("Tool Call Decision (system)", system_prompt)

    msgs_to_send = [SystemMessage(content=system_prompt)] + (copy.deepcopy(messages) if messages else [])

    try:
        response = await _call_llm_with_retry(msgs_to_send)
    except Exception as e:
        logger.error("LLM call failed after retries: %s", e)
        show_error(e, {"node": "tool_call_node"})
        return {
            "error": f"LLM call failed: {e}",
            "pending_tool_calls": [],
            **log_entry("tool_call_node", state, {"error": str(e)}),
        }

    tool_calls = getattr(response, "tool_calls", []) or []

    if tool_calls:
        pending = [
            {"id": tc["id"], "name": tc["name"], "args": tc["args"]}
            for tc in tool_calls
        ]
        update: dict[str, Any] = {
            "pending_tool_calls": pending,
            "messages": [response],
        }
    else:
        update = {
            "pending_tool_calls": [],
            "messages": [response],
        }

    return {**update, **log_entry("tool_call_node", state, update)}
