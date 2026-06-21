"""
Tool Executor Node — executes the pending tool calls requested by the LLM.
"""
from __future__ import annotations

import time
import logging
from typing import Any

from langchain_core.messages import ToolMessage

from scripts.state import HotelSearchState, ToolCallRecord
from scripts.tools import TOOL_MAP
from scripts.debug import log_entry, show_tool_call, show_error

logger = logging.getLogger(__name__)


async def tool_executor_node(state: HotelSearchState) -> dict[str, Any]:
    """
    Execute all pending tool calls in the state.

    Collects results, wraps them in ToolMessages, records them in tool_history,
    and clears the pending_tool_calls queue.
    """
    pending = state.get("pending_tool_calls", [])
    if not pending:
        update: dict[str, Any] = {"pending_tool_calls": []}
        return {**update, **log_entry("tool_executor_node", state, update)}

    results = []
    tool_messages = []
    tool_history = list(state.get("tool_history", []) or [])

    for call in pending:
        tool_name = call["name"]
        tool_args = call["args"]
        tool_id = call["id"]

        # Get the registered tool
        tool = TOOL_MAP.get(tool_name)
        if not tool:
            error_msg = f"Tool '{tool_name}' not found in available tools"
            logger.error(error_msg)
            results.append({
                "tool": tool_name,
                "error": error_msg,
            })
            tool_messages.append(ToolMessage(
                content=f"Error: {error_msg}",
                tool_call_id=tool_id,
            ))
            record: ToolCallRecord = {
                "tool_name": tool_name,
                "params": tool_args,
                "result": None,
                "error": error_msg,
            }
            tool_history.append(record)
            continue

        start = time.time()
        try:
            # Invoke the tool (supports sync and async langchain tools)
            if hasattr(tool, "ainvoke"):
                result = await tool.ainvoke(tool_args)
            elif hasattr(tool, "invoke"):
                result = tool.invoke(tool_args)
            else:
                result = await tool(**tool_args)

            duration = time.time() - start

            # Render details in terminal debugger
            show_tool_call(
                name=tool_name,
                params=tool_args,
                result=result,
                duration=duration,
            )

            record: ToolCallRecord = {
                "tool_name": tool_name,
                "params": tool_args,
                "result": result,
                "error": None,
            }
            tool_history.append(record)
            results.append({"tool": tool_name, "result": result})

            tool_messages.append(ToolMessage(
                content=str(result),
                tool_call_id=tool_id,
            ))

        except Exception as e:
            duration = time.time() - start
            logger.exception("Error executing tool %s", tool_name)
            show_error(e, {"tool": tool_name, "args": tool_args})

            record: ToolCallRecord = {
                "tool_name": tool_name,
                "params": tool_args,
                "result": None,
                "error": str(e),
            }
            tool_history.append(record)
            tool_messages.append(ToolMessage(
                content=f"Error: {str(e)}",
                tool_call_id=tool_id,
            ))

    update = {
        "pending_tool_calls": [],
        "tool_history": tool_history,
        "messages": tool_messages,
    }

    return {**update, **log_entry("tool_executor_node", state, update)}
