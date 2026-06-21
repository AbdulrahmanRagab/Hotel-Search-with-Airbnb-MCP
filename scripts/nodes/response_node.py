"""
Response Node — synthesizes a final user-facing response from tool results.

Uses Jinja2 prompt template + LLM to turn raw tool outputs into
a friendly, formatted answer.
"""
from __future__ import annotations

import time
from datetime import datetime
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq

from scripts.config.settings import settings
from scripts.state import HotelSearchState
from scripts.prompts.prompt_builder import build_prompt
from scripts.debug import log_entry, show_prompt

_llm_instance = None


def _get_llm() -> ChatGroq:
    global _llm_instance
    if _llm_instance is None:
        _llm_instance = ChatGroq(
            model=settings.llm_model,
            temperature=0.7,
            api_key=settings.groq_api_key or None,
        )
    return _llm_instance


async def response_node(state: HotelSearchState) -> dict[str, Any]:
    """
    Synthesize the final response from tool results.

    Returns:
        final_response: str (markdown-formatted answer)
        messages: [AI response]
    """
    tool_history = state.get("tool_history", [])
    user_query = state.get("messages", [])[-1].content if state.get("messages") else ""

    # ── Build the synthesis prompt ──────────────────────────
    prompt = build_prompt(
        "response_formatter.j2",
        user_query=user_query,
        tool_results=tool_history,
    )

    show_prompt("Response Formatter", prompt)

    # ── Call LLM ────────────────────────────────────────────
    llm = _get_llm()
    response = await llm.ainvoke([
        SystemMessage(content="You are a friendly hotel search assistant."),
        HumanMessage(content=prompt),
    ])

    update = {
        "final_response": response.content,
        "messages": [response],
    }

    return {**update, **log_entry("response_node", state, update)}
