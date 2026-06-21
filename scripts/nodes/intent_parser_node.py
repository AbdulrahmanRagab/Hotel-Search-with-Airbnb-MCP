"""
Intent Parser Node — uses LLM to extract structured SearchParams from user message.

This is the most complex node — it bridges natural language ↔ structured data.
"""
from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq

from scripts.config.settings import settings
from scripts.state import HotelSearchState, SearchParams
from scripts.prompts.prompt_builder import build_prompt
from scripts.debug import log_entry, show_prompt, show_error
from scripts.json_utils import _extract_json

_llm_instance = None


def _get_llm() -> ChatGroq:
    global _llm_instance
    if _llm_instance is None:
        _llm_instance = ChatGroq(
            model=settings.llm_model,
            temperature=0.0,
            api_key=settings.groq_api_key or None,
            #base_url=settings.openai_base_url or None,  
            model_kwargs={"response_format": {"type": "json_object"}},  
        )
    return _llm_instance


async def intent_parser_node(state: HotelSearchState) -> dict[str, Any]:
    """
    Extract structured search parameters from the latest user message.

    Uses:
    - Jinja2-rendered prompt with JSON schema injected
    - LLM with low temperature for deterministic output
    - Pydantic validation of the result

    Updates state with:
    - search_params: SearchParams | None
    - user_intent: str
    - is_valid: bool
    - error: str | None
    """
    messages = state.get("messages", [])
    if not messages:
        update = {"error": "No messages to parse", "is_valid": False}
        return {**update, **log_entry("intent_parser_node", state, update)}

    last_msg = messages[-1]
    user_message = last_msg.content if hasattr(last_msg, "content") else str(last_msg)

    # Build context from recent messages
    context_messages = []
    for msg in messages[-5:]:
        role = "user" if "Human" in type(msg).__name__ else "assistant"
        context_messages.append({"role": role, "content": str(msg.content)[:200]})

    # ── Build dynamic prompt with JSON schema ───────────────
    json_schema = json.dumps(SearchParams.model_json_schema(), indent=2)

    system_prompt = build_prompt(
        "intent_parser.j2",
        user_message=user_message,
        json_schema=json_schema,
        context_messages=context_messages,
    )

    show_prompt("Intent Parser (system)", system_prompt)

    # ── Call LLM ────────────────────────────────────────────
    try:
        llm = _get_llm()
        response = await llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Extract search params from: {user_message}"),
        ])

        # ── Parse JSON response ─────────────────────────────
        parsed = _extract_json(response.content)
        raw_params = parsed.get("search_params", {})
        intent = parsed.get("intent", "search")
        reasoning = parsed.get("reasoning", "")

        # ── Validate with Pydantic ──────────────────────────
        search_params = SearchParams(**raw_params)

        update: dict[str, Any] = {
            "search_params": search_params,
            "user_intent": intent,
            "is_valid": True,
            "error": None,
        }

    except json.JSONDecodeError as e:
        show_error(e, {"user_message": user_message})
        update = {
            "error": f"Failed to parse LLM JSON response: {e}",
            "is_valid": False,
            "search_params": None,
            "user_intent": "clarify",
        }

    except Exception as e:
        show_error(e, {"node": "intent_parser_node"})
        update = {
            "error": f"Validation failed: {e}",
            "is_valid": False,
            "search_params": None,
            "user_intent": "clarify",
        }

    return {**update, **log_entry("intent_parser_node", state, update)}
