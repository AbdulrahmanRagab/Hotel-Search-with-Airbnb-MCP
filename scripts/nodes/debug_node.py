"""
Debug Node — a no-op pass-through that just records the current state.

Useful as a checkpoint marker in the graph flow.
"""
from __future__ import annotations

from typing import Any

from scripts.state import HotelSearchState
from scripts.debug import log_entry


async def debug_node(state: HotelSearchState) -> dict[str, Any]:
    """
    Pass-through node that just records debug info.

    Acts as a labeled checkpoint in the graph execution.
    """
    return log_entry("debug_node", state, {"debug_passthrough": True})
