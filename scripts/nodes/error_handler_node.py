"""
Error Handler Node — terminal failure handler.

Reached when validation fails too many times or a tool errors out.
Provides a friendly error message and stops the graph.
"""
from __future__ import annotations

from typing import Any

from scripts.state import HotelSearchState
from scripts.debug import log_entry, console


async def error_handler_node(state: HotelSearchState) -> dict[str, Any]:
    """
    Handle unrecoverable errors gracefully.

    Returns:
        final_response: friendly error message
        error: original error string
    """
    error = state.get("error", "Unknown error")
    retry_count = state.get("retry_count", 0)
    user_intent = state.get("user_intent", "")

    console.print(f"\n[red bold]═══ ERROR HANDLER ═══[/red bold]")
    console.print(f"[red]Error: {error}[/red]")
    console.print(f"[dim]Retry count: {retry_count}[/dim]")

    # Build a helpful response based on the type of error
    if "check_in" in error.lower() or "check_out" in error.lower() or "date" in error.lower():
        message = (
            "❌ There was an issue with the dates you provided. "
            "Please make sure check-out is after check-in and both dates are in the future.\n\n"
            "Try again like: *'Find hotels in Paris from July 1 to July 5'*"
        )
    elif "location" in error.lower():
        message = (
            "❌ I couldn't understand the location. "
            "Please specify a city, neighborhood, or address.\n\n"
            "Try: *'Hotels in Tokyo, Japan'*"
        )
    elif "guests" in error.lower():
        message = (
            "❌ The number of guests must be between 1 and 20."
        )
    else:
        message = (
            f"❌ Something went wrong: {error}\n\n"
            "Please rephrase your request and try again."
        )

    update = {
        "final_response": message,
        "error": error,
        "is_valid": False,
    }

    return {**update, **log_entry("error_handler_node", state, update)}
