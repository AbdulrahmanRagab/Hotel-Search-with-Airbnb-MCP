"""
Input Node — entry point of the graph.

Normalizes the incoming user message and adds metadata.
"""
from __future__ import annotations

import uuid
from typing import Any

from langchain_core.messages import HumanMessage

from scripts.state import HotelSearchState
from scripts.debug import log_entry


async def input_node(state: HotelSearchState) -> dict[str, Any]:
    """
    Normalize incoming input.

    Responsibilities:
    1. Ensure thread_id is set (generate one if missing)
    2. Validate the message exists
    3. Increment step counter
    """
    update: dict[str, Any] = {}

    # Generate thread_id if not present (first turn)
    if not state.get("thread_id"):
        thread_id = str(uuid.uuid4())
        update["thread_id"] = thread_id
        update["session_id"] = thread_id[:8]
    else:
        update["thread_id"] = state["thread_id"]
        update["session_id"] = state.get("session_id", state["thread_id"][:8])

    # Ensure at least one user message exists
    messages = state.get("messages", [])
    if not isinstance(messages[-1], HumanMessage):
        update["error"] = "Last message is not a user message"
        return {**update, **log_entry("input_node", state, update)}

    # Extract user query for downstream nodes
    last_msg = messages[-1]
    update["messages"] = [last_msg]  # Pass through

    return {**update, **log_entry("input_node", state, update)}
