"""
Human Review Node — uses LangGraph's `interrupt()` to pause for confirmation.

This is where the graph STOPS execution and waits for the user to respond.
When the user types "y" (or "n"), we resume with `Command(resume=value)`.
"""
from __future__ import annotations

from typing import Any

from langchain_core.runnables import RunnableConfig
from langchain_core.runnables.config import var_child_runnable_config
from langgraph.types import interrupt

from scripts.state import HotelSearchState
from scripts.debug import log_entry, console


def human_review_node(state: HotelSearchState, config: RunnableConfig) -> dict[str, Any]:
    """
    Pause the graph and ask the user to confirm a sensitive action.

    For this demo, we pause before finalizing any booking.
    The interrupt() function yields control back to the chatbot loop.
    """
    params = state.get("search_params")
    tool_history = state.get("tool_history", [])

    # Build a summary of what we'd be confirming
    summary_lines = []
    if params:
        summary_lines.append(f"📍 Location: {params.location}")
        summary_lines.append(f"📅 Dates: {params.check_in} → {params.check_out}")
        summary_lines.append(f"👥 Guests: {params.guests}")
        if params.max_price_per_night:
            summary_lines.append(f"💰 Max price: {params.max_price_per_night} {params.currency}/night")

    if tool_history:
        summary_lines.append(f"🔧 Tools used: {[t['tool_name'] for t in tool_history]}")

    summary = "\n".join(summary_lines)

    # ── INTERRUPT — graph pauses here ───────────────────────
    payload = {
        "question": "Do you want to proceed with this search?",
        "summary": summary,
    }

    console.print(f"\n[bold hot_pink]═══ HUMAN REVIEW REQUIRED ═══[/bold hot_pink]")
    console.print(f"[hot_pink]{summary}[/hot_pink]")

    # Workaround for Python <3.11: LangGraph doesn't propagate the runnable
    # config context variable via async contextvars. We set it manually so
    # that interrupt() -> get_config() can find it.
    token = var_child_runnable_config.set(config)
    try:
        user_response = interrupt(payload)
    finally:
        var_child_runnable_config.reset(token)

    # After resume, user_response contains the answer ("y" or "n")
    approved = str(user_response).strip().lower() in {"y", "yes", "true", "1"}

    update: dict[str, Any] = {
        "human_approved": approved,
        "interrupt_payload": payload,
        "messages": [],  # Don't pollute the chat history
    }

    if not approved:
        update["final_response"] = (
            "❌ Search cancelled by user. Feel free to modify your request and try again."
        )

    return {**update, **log_entry("human_review_node", state, update)}
