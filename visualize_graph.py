"""
Graph Visualizer — generates a Mermaid diagram of the LangGraph state machine.
"""
from langgraph.graph import StateGraph
from langgraph.checkpoint.memory import MemorySaver


def _passthru(state):
    return {}


def _route_after_input(state):
    return "intent_parser" if not state.get("error") else "error_handler"


def _route_after_validation(state):
    if state.get("is_valid"):
        return "tool_call"
    return "intent_parser" if state.get("retry_count", 0) < 3 else "error_handler"


def _route_after_tool_call(state):
    if state.get("pending_tool_calls"):
        return "tool_executor"
    return "error_handler" if state.get("error") else "response"


def _route_after_review(state):
    return "persist" if state.get("human_approved") else "__end__"


class _State(dict):
    pass


def build_graph():
    workflow = StateGraph(_State)

    workflow.add_node("input", _passthru)
    workflow.add_node("intent_parser", _passthru)
    workflow.add_node("validator", _passthru)
    workflow.add_node("tool_call", _passthru)
    workflow.add_node("tool_executor", _passthru)
    workflow.add_node("response", _passthru)
    workflow.add_node("human_review", _passthru)
    workflow.add_node("error_handler", _passthru)
    workflow.add_node("persist", _passthru)
    workflow.add_node("debug", _passthru)

    workflow.set_entry_point("input")

    workflow.add_conditional_edges(
        "input", _route_after_input,
        {"intent_parser": "intent_parser", "error_handler": "error_handler"},
    )

    workflow.add_edge("intent_parser", "validator")

    workflow.add_conditional_edges(
        "validator", _route_after_validation,
        {"tool_call": "tool_call", "intent_parser": "intent_parser", "error_handler": "error_handler"},
    )

    workflow.add_conditional_edges(
        "tool_call", _route_after_tool_call,
        {"response": "response", "tool_executor": "tool_executor", "human_review": "human_review", "error_handler": "error_handler"},
    )

    workflow.add_edge("tool_executor", "tool_call")
    workflow.add_edge("response", "human_review")

    workflow.add_conditional_edges(
        "human_review", _route_after_review,
        {"persist": "persist", "__end__": "__end__"},
    )

    workflow.add_edge("error_handler", "__end__")
    workflow.add_edge("persist", "__end__")
    workflow.add_edge("debug", "intent_parser")

    return workflow.compile()


def main():
    graph = build_graph()
    mermaid_code = graph.get_graph().draw_mermaid()

    output = f"""# LangGraph State Machine — Mermaid Diagram

```mermaid
{mermaid_code}
```
"""

    with open("graph_diagram.md", "w") as f:
        f.write(output)

    print("Saved to graph_diagram.md")
    print("\n--- ASCII Tree ---")
    print(graph.get_graph().draw_ascii())


if __name__ == "__main__":
    main()
