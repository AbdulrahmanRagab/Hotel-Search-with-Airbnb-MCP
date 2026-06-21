from __future__ import annotations

import logging
from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from scripts.nodes import (
    debug_node,
    error_handler_node,
    human_review_node,
    input_node,
    intent_parser_node,
    persist_node,
    response_node,
    tool_call_node,
    tool_executor_node,
    validator_node,
)
from scripts.state import HotelSearchState

logger = logging.getLogger(__name__)


MAX_RETRIES = 3


def build_graph_with_memory():
    graph = _build_base_graph()
    return graph.compile(checkpointer=MemorySaver())


async def build_graph_with_postgres(postgres_url_or_pool: Any) -> StateGraph:
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

    if isinstance(postgres_url_or_pool, str):
        from psycopg_pool import AsyncConnectionPool
        pool = AsyncConnectionPool(conninfo=postgres_url_or_pool, max_size=10, open=False)
        await pool.open()
        checkpointer = AsyncPostgresSaver(pool)
    else:
        checkpointer = AsyncPostgresSaver(postgres_url_or_pool)

    await checkpointer.setup()
    graph = _build_base_graph()
    return graph.compile(checkpointer=checkpointer)



def _build_base_graph() -> StateGraph:
    workflow = StateGraph(HotelSearchState)

    workflow.add_node("input", input_node)
    workflow.add_node("intent_parser", intent_parser_node)
    workflow.add_node("validator", validator_node)
    workflow.add_node("tool_call", tool_call_node)
    workflow.add_node("tool_executor", tool_executor_node)
    workflow.add_node("response", response_node)
    workflow.add_node("human_review", human_review_node)
    workflow.add_node("error_handler", error_handler_node)
    workflow.add_node("persist", persist_node)
    workflow.add_node("debug", debug_node)

    workflow.set_entry_point("input")

    workflow.add_conditional_edges(
        "input",
        _route_after_input,
        {"intent_parser": "intent_parser", "error_handler": "error_handler"},
    )

    workflow.add_edge("intent_parser", "validator")

    workflow.add_conditional_edges(
        "validator",
        _route_after_validation,
        {
            "tool_call": "tool_call",
            "intent_parser": "intent_parser",
            "error_handler": "error_handler",
        },
    )

    workflow.add_conditional_edges(
        "tool_call",
        _route_after_tool_call,
        {
            "response": "response",
            "tool_executor": "tool_executor",
            "human_review": "human_review",
            "error_handler": "error_handler",
        },
    )

    workflow.add_edge("tool_executor", "tool_call")
    workflow.add_edge("response", "human_review")

    workflow.add_conditional_edges(
        "human_review",
        _route_after_review,
        {"persist": "persist", "END": END},
    )

    workflow.add_edge("error_handler", END)
    workflow.add_edge("persist", END)
    workflow.add_edge("debug", "intent_parser")

    return workflow


def _route_after_input(state: HotelSearchState) -> str:
    if state.get("error"):
        return "error_handler"
    return "intent_parser"


def _route_after_validation(state: HotelSearchState) -> str:
    if state.get("is_valid"):
        return "tool_call"
    retry = state.get("retry_count", 0)
    if retry >= MAX_RETRIES:
        return "error_handler"
    return "intent_parser"


def _route_after_tool_call(state: HotelSearchState) -> str:
    pending = state.get("pending_tool_calls", [])
    if pending:
        return "tool_executor"
    if state.get("error"):
        return "error_handler"
    return "response"


def _route_after_review(state: HotelSearchState) -> str:
    if state.get("human_approved"):
        return "persist"
    return END
