"""
Gradio Web UI for Hotel Search AI Assistant.

Usage:
    python gradio_app.py
"""
from __future__ import annotations

import logging
import uuid
from typing import Any

import gradio as gr
from langchain_core.messages import HumanMessage
from langgraph.types import Command

from scripts.graph import build_graph_with_memory

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

graph = build_graph_with_memory()

_INITIAL_STATE: dict[str, Any] = {
    "step": 0,
    "retry_count": 0,
    "is_valid": False,
    "user_intent": "",
    "available_tools": ["airbnb_search", "web_search", "get_weather", "format_results"],
    "debug_log": [],
    "pending_tool_calls": [],
    "tool_history": [],
    "results": [],
    "human_approved": None,
    "interrupt_payload": None,
}


def _new_session() -> dict[str, Any]:
    thread_id = str(uuid.uuid4())
    return {
        "thread_id": thread_id,
        "config": {"configurable": {"thread_id": thread_id}},
    }


async def _run_turn(
    message: str,
    session: dict[str, Any],
) -> str:
    thread_id = session["thread_id"]
    config = session["config"]

    initial_state: dict[str, Any] = {
        **_INITIAL_STATE,
        "messages": [HumanMessage(content=message)],
        "thread_id": thread_id,
        "session_id": thread_id[:8],
    }

    result = await graph.ainvoke(initial_state, config=config)

    while "__interrupt__" in result:
        logger.info("Auto-approving human review interrupt")
        result = await graph.ainvoke(Command(resume="y"), config=config)

    return result.get("final_response") or "I couldn't generate a response."


async def respond(
    message: str,
    history: list[list[str]],
    session: dict[str, Any],
) -> str:
    if not message.strip():
        return ""

    if not session:
        session.clear()
        session.update(_new_session())

    try:
        return await _run_turn(message, session)
    except Exception as e:
        logger.exception("Error processing message")
        return f"❌ **Error**: {e}"


session_state = gr.State({})

chat = gr.ChatInterface(
    fn=respond,
    additional_inputs=[session_state],
    title="🏨 Hotel Search AI Assistant",
    description="Find hotels on Airbnb using natural language. Powered by LangGraph + Groq.",
    examples=[
        ["Find hotels in Paris from July 1st to 3rd for 2 guests"],
        ["Show me budget hotels in Dubai near the beach"],
        ["Find luxury apartments in London for next weekend"],
    ],
)


if __name__ == "__main__":
    chat.launch(server_name="0.0.0.0", server_port=7860)
