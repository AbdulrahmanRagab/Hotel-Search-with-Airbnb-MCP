"""
Hotel Search AI — Terminal Chatbot Entry Point.

Features:
- Rich-powered terminal UI
- Slash commands (/help, /debug, /clear, etc.)
- Streaming graph execution with event display
- Human-in-the-loop interrupt handling
- Session persistence (Postgres or memory)

Usage:
    python airbnb_mcp.py                # default mode
    python airbnb_mcp.py --no-debug     # disable debug output
    python airbnb_mcp.py --memory       # use in-memory checkpointer
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any

from langchain_core.messages import HumanMessage
from langgraph.types import Command
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from scripts.config.settings import settings
from scripts.debug import set_debug, console as debug_console
from scripts.graph import build_graph_with_memory, build_graph_with_postgres

logger = logging.getLogger(__name__)

# ============================================================
# 🎨 Banner & Help
# ============================================================

BANNER = """
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║      🏨  Hotel Search AI Assistant (Powered by MCP)  🏨      ║
║                                                              ║
║            Built with LangGraph + LangChain                  ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
"""

HELP_TEXT = """
# 🆘 Available Commands

| Command          | Description                                |
|------------------|--------------------------------------------|
| `/help`          | Show this help                             |
| `/clear`         | Clear conversation (new thread)            |
| `/debug on/off`  | Toggle debug output                        |
| `/state`         | Show last state (if available)             |
| `/history`       | Show full debug trace from last turn       |
| `/memory`        | Use in-memory checkpointer                 |
| `/quit` or `exit`| Exit the chatbot                           |

# 💡 Try These Queries
- "Find hotels in Paris for 2 nights from July 1"
- "What's the weather in Tokyo?"
- "Show me budget hotels in Dubai near the beach"
- "Compare luxury hotels in London for next weekend"
"""


# ============================================================
# 🤖 Chatbot
# ============================================================

class HotelSearchChatbot:
    """Interactive terminal chatbot backed by LangGraph."""

    def __init__(self):
        self.console = Console()
        self.thread_id = str(uuid.uuid4())
        self.config = {"configurable": {"thread_id": self.thread_id}}
        self.use_postgres = settings.checkpointer == "postgres"
        self.pool = None

        # Build the graph
        self._build_graph()

        # Set initial debug mode
        set_debug(settings.debug_mode)

    def _build_graph(self) -> None:
        """Build the graph with the appropriate checkpointer."""
        if self.use_postgres:
            self.console.print(f"[cyan]🔌 Connecting to Postgres: {settings.postgres_url}[/cyan]")
            self.graph = None  # Will be set in async setup
        else:
            self.console.print("[cyan]🧠 Building graph with in-memory checkpointer...[/cyan]")
            self.graph = build_graph_with_memory()
            self.console.print("[green]✓ Graph ready[/green]")

    async def setup_async(self) -> None:
        """Async setup (for Postgres checkpointer)."""
        if self.use_postgres and self.graph is None:
            from psycopg_pool import AsyncConnectionPool
            self.pool = AsyncConnectionPool(conninfo=settings.postgres_url, max_size=10, open=False)
            await self.pool.open()
            self.graph = await build_graph_with_postgres(self.pool)
            self.console.print("[green]✓ Graph ready (Postgres)[/green]")

    async def close_async(self) -> None:
        """Clean up connection pool and other chatbot resources."""
        if self.pool is not None:
            self.console.print("\n[cyan]🔌 Closing Postgres connection pool...[/cyan]")
            await self.pool.close()
            self.pool = None
            self.console.print("[green]✓ Connection pool closed[/green]")

    # ============================================================
    # 🎯 Main loop
    # ============================================================

    async def run(self) -> None:
        try:
            await self.setup_async()
            self._print_banner()

            while True:
                try:
                    user_input = self.console.input("[bold yellow]User:[/bold yellow] ").strip()

                    if not user_input:
                        continue

                    if user_input.startswith("/"):
                        await self._handle_command(user_input)
                        continue

                    if user_input.lower() in {"exit", "quit"}:
                        self._print_goodbye()
                        break

                    # Process the query
                    await self._process_turn(user_input)

                except KeyboardInterrupt:
                    self._print_goodbye()
                    break
                except EOFError:
                    self._print_goodbye()
                    break
                except Exception as e:
                    self.console.print(f"[red bold]Unexpected error: {e}[/red bold]")
                    import traceback
                    self.console.print(traceback.format_exc())
        finally:
            await self.close_async()

    def _print_banner(self) -> None:
        self.console.print(BANNER, style="bold cyan")
        self.console.print(f"[dim]Thread ID:  {self.thread_id}[/dim]")
        self.console.print(f"[dim]Checkpointer: {'Postgres' if self.use_postgres else 'Memory'}[/dim]")
        self.console.print(f"[dim]Debug mode: {'ON 🐛' if settings.debug_mode else 'OFF'}[/dim]")
        self.console.print(f"[dim]Tools: 4 (airbnb_search, web_search, get_weather, format_results)[/dim]")
        self.console.print()

    def _print_goodbye(self) -> None:
        self.console.print()
        self.console.print(Panel(
            "👋 Thanks for using Hotel Search AI! Have a great trip! ✈️",
            border_style="cyan",
        ))

    # ============================================================
    # 🛠️ Command handler
    # ============================================================

    async def _handle_command(self, cmd: str) -> None:
        cmd = cmd.lower().strip()

        if cmd == "/help":
            self.console.print(Markdown(HELP_TEXT))
        elif cmd == "/clear":
            self.thread_id = str(uuid.uuid4())
            self.config = {"configurable": {"thread_id": self.thread_id}}
            self.console.print(f"[green]✓ New conversation (thread: {self.thread_id[:8]})[/green]")
        elif cmd == "/debug on":
            settings.debug_mode = True
            set_debug(True)
            self.console.print("[green]✓ Debug mode ON[/green]")
        elif cmd == "/debug off":
            settings.debug_mode = False
            set_debug(False)
            self.console.print("[yellow]✓ Debug mode OFF[/yellow]")
        elif cmd == "/state":
            try:
                state = await self.graph.aget_state(self.config)
                self._show_state(state.values)
            except Exception as e:
                self.console.print(f"[red]No state yet: {e}[/red]")
        elif cmd == "/history":
            try:
                state = await self.graph.aget_state(self.config)
                self._show_debug_log(state.values.get("debug_log", []))
            except Exception as e:
                self.console.print(f"[red]No history yet: {e}[/red]")
        elif cmd == "/memory":
            self.console.print("[cyan]🔄 Switching to memory checkpointer...[/cyan]")
            self.graph = build_graph_with_memory()
            self.console.print("[green]✓ Memory checkpointer active[/green]")
        elif cmd in {"/quit", "/exit"}:
            raise KeyboardInterrupt
        else:
            self.console.print(f"[red]Unknown command: {cmd}[/red]")
            self.console.print("[dim]Type /help for available commands[/dim]")

    def _show_state(self, state: dict[str, Any]) -> None:
        """Display state in a clean panel."""
        from rich.table import Table

        table = Table(title="📦 Current State", show_header=True, border_style="dim")
        table.add_column("Field", style="cyan", min_width=20)
        table.add_column("Value", style="yellow")

        for key, value in state.items():
            if key == "messages":
                table.add_row("messages", f"[{len(value)} messages]")
            elif key == "debug_log":
                table.add_row("debug_log", f"[{len(value)} entries]")
            elif hasattr(value, "model_dump"):
                table.add_row(key, str(value.model_dump()))
            else:
                s = str(value)
                if len(s) > 100:
                    s = s[:100] + "..."
                table.add_row(key, s if value is not None else "[dim]None[/dim]")

        self.console.print(table)

    def _show_debug_log(self, log: list[dict[str, Any]]) -> None:
        """Display the full debug log."""
        from rich.table import Table

        table = Table(title=f"🐛 Debug Log ({len(log)} steps)", show_header=True, border_style="green")
        table.add_column("#", style="cyan", width=4)
        table.add_column("Node", style="green", min_width=20)
        table.add_column("Time", style="dim", min_width=20)
        table.add_column("Key Changes", style="yellow")

        for i, entry in enumerate(log, 1):
            update_keys = entry.get("snapshot", {}).get("update_keys", [])
            table.add_row(
                str(i),
                entry.get("node", "?"),
                entry.get("timestamp", "?"),
                ", ".join(update_keys) if update_keys else "[dim]—[/dim]",
            )

        self.console.print(table)

    # ============================================================
    # 🚀 Process one turn
    # ============================================================

    async def _process_turn(self, user_input: str) -> None:
        """Run one conversation turn through the graph."""
        self.console.print()
        self.console.print(f"[bold yellow]User:[/bold yellow] {user_input}")
        self.console.print()

        initial_state = {
            "messages": [HumanMessage(content=user_input)],
            "thread_id": self.thread_id,
            "session_id": self.thread_id[:8],
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

        # First invocation
        result = await self.graph.ainvoke(initial_state, config=self.config)

        # ── Handle interrupt (human-in-the-loop) ─────────────
        while "__interrupt__" in result:
            interrupts = result["__interrupt__"]
            for intr in interrupts:
                payload = intr.value if hasattr(intr, "value") else intr
                question = payload.get("question", "Confirm?")
                summary = payload.get("summary", "")

                self.console.print(Panel(
                    f"[bold hot_pink]{question}[/bold hot_pink]\n\n{summary}",
                    title="🤚 Human Review",
                    border_style="hot_pink",
                ))

                # Get user input
                confirm = self.console.input("[bold yellow]You (y/n):[/bold yellow] ").strip()

                # Resume with the user's answer
                result = await self.graph.ainvoke(
                    Command(resume=confirm),
                    config=self.config,
                )

        # ── Display final response ────────────────────────────
        final_response = result.get("final_response") or "I couldn't generate a response."
        self.console.print()
        self.console.print(Panel(
            Markdown(final_response),
            title="🤖 Assistant",
            border_style="green",
        ))
        self.console.print()


# ============================================================
# 🚀 Entry point
# ============================================================

def _setup_logging() -> None:
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logger.info("Logging initialized at %s level", settings.log_level)


async def main():
    _setup_logging()
    import argparse
    parser = argparse.ArgumentParser(description="Hotel Search AI Chatbot")
    parser.add_argument("--no-debug", action="store_true", help="Disable debug mode")
    parser.add_argument("--memory", action="store_true", help="Force in-memory checkpointer")
    args = parser.parse_args()

    if args.no_debug:
        settings.debug_mode = False
    if args.memory:
        settings.checkpointer = "memory"

    chatbot = HotelSearchChatbot()
    await chatbot.run()


if __name__ == "__main__":
    asyncio.run(main())
