"""
Persist Node — terminal node that logs the conversation summary.

Note: actual persistence is handled by the LangGraph checkpointer
(Auto-saved after every node). This node is for logging only.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from scripts.state import HotelSearchState
from scripts.debug import log_entry, console


async def persist_node(state: HotelSearchState) -> dict[str, Any]:
    """
    Final node — logs a conversation summary.

    Real persistence is handled by AsyncPostgresSaver automatically.
    """
    debug_log = state.get("debug_log", [])
    timings = {}
    for entry in debug_log:
        # We could store per-node timings in debug_log if we want
        pass

    console.print(f"\n[bold green]═══ CONVERSATION PERSISTED ═══[/bold green]")
    console.print(f"[dim]Thread: {state.get('thread_id', '?')}[/dim]")
    console.print(f"[dim]Steps: {len(debug_log)}[/dim]")
    console.print(f"[dim]Final response length: {len(state.get('final_response', '') or '')} chars[/dim]")

    # Just increment step for the debug log
    return log_entry("persist_node", state, {"status": "persisted"})
