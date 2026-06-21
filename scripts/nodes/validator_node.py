"""
Validator Node — checks SearchParams for completeness and sensibility.

Two-layer validation:
1. Pydantic structural validation (already done in intent_parser)
2. LLM semantic validation (dates make sense, location exists, etc.)
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq

from scripts.config.settings import settings
from scripts.state import HotelSearchState, SearchParams
from scripts.prompts.prompt_builder import build_prompt
from scripts.debug import log_entry, show_error, show_prompt
from scripts.json_utils import _extract_json

_llm_instance = None


def _get_llm() -> ChatGroq:
    global _llm_instance
    if _llm_instance is None:
        _llm_instance = ChatGroq(
            model=settings.llm_model,
            temperature=0.0,
            api_key=settings.groq_api_key or None,
        )
    return _llm_instance


async def validator_node(state: HotelSearchState) -> dict[str, Any]:
    """
    Validate search parameters semantically.

    Returns:
        is_valid: bool
        error: str | None
        retry_count: int (incremented on failure)
    """
    params = state.get("search_params")

    # ── Quick structural checks (no LLM needed) ─────────────
    if params is None:
        update = {
            "is_valid": False,
            "error": "No search_params to validate",
        }
        return {**update, **log_entry("validator_node", state, update)}

    if not isinstance(params, SearchParams):
        try:
            params = SearchParams(**params.model_dump() if hasattr(params, "model_dump") else params)
        except Exception as e:
            update = {
                "is_valid": False,
                "error": f"Invalid params structure: {e}",
                "retry_count": state.get("retry_count", 0) + 1,
            }
            return {**update, **log_entry("validator_node", state, update)}

    # ── Quick date sanity checks ────────────────────────────
    today = date.today()
    issues = []

    if params.check_in < today:
        issues.append(f"check_in ({params.check_in}) is in the past")
    if params.check_out <= params.check_in:
        issues.append(f"check_out ({params.check_out}) must be after check_in ({params.check_in})")

    if issues:
        update = {
            "is_valid": False,
            "error": "; ".join(issues),
            "retry_count": state.get("retry_count", 0) + 1,
        }
        return {**update, **log_entry("validator_node", state, update)}

    # ── LLM semantic validation (validator.j2) ──────────────
    params_dict = params.model_dump()
    for key, val in params_dict.items():
        if isinstance(val, (date, datetime)):
            params_dict[key] = val.isoformat()

    validation_prompt = build_prompt(
        "validator.j2",
        params=params_dict,
    )

    show_prompt("Semantic Parameter Validation (system)", validation_prompt)

    try:
        llm = _get_llm()
        response = await llm.ainvoke([
            SystemMessage(content=validation_prompt),
            HumanMessage(content="Validate the search parameters and return validation JSON."),
        ])

        parsed = _extract_json(response.content)
        is_valid = parsed.get("is_valid", False)
        missing_fields = parsed.get("missing_fields", [])
        invalid_fields = parsed.get("invalid_fields", [])
        clarification = parsed.get("clarification_question", "")

        if not is_valid:
            error_msg = clarification or f"Validation failed. Missing: {missing_fields}. Invalid: {invalid_fields}."
            update = {
                "is_valid": False,
                "error": error_msg,
                "retry_count": state.get("retry_count", 0) + 1,
            }
        else:
            update = {
                "is_valid": True,
                "error": None,
            }

    except Exception as e:
        show_error(e, {"node": "validator_node"})
        update = {
            "is_valid": False,
            "error": f"Semantic validation failed to execute: {e}",
            "retry_count": state.get("retry_count", 0) + 1,
        }

    return {**update, **log_entry("validator_node", state, update)}
