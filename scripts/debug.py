from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
# from rich.tree import Tree

from scripts.config.settings import settings

logger = logging.getLogger(__name__)

console = Console()

_debug_enabled: bool = settings.debug_mode


def set_debug(enabled: bool) -> None:
    global _debug_enabled
    _debug_enabled = enabled


def is_debug_enabled() -> bool:
    return _debug_enabled


def log_entry(
    node_name: str,
    state: dict[str, Any],
    update: dict[str, Any],
) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "node": node_name,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "snapshot": {
            "update_keys": list(update.keys()),
        },
    }
    debug_log = state.get("debug_log", [])
    debug_log = list(debug_log) if debug_log else []
    debug_log.append(entry)
    return {"debug_log": debug_log}


def show_prompt(title: str, content: str) -> None:
    if not _debug_enabled:
        return
    syntax = Syntax(content, "markdown", theme="monokai", word_wrap=True)
    console.print(Panel(syntax, title=f"📝 {title}", border_style="yellow"))
    console.print()


def show_error(error: Exception | str, context: dict[str, Any] | None = None) -> None:
    if not _debug_enabled:
        logger.error("%s | context: %s", error, context)
        return
    console.print(f"[red bold]❌ Error: {error}[/red bold]")
    if context:
        table = Table(show_header=True, border_style="red")
        table.add_column("Key", style="cyan")
        table.add_column("Value", style="yellow")
        for k, v in context.items():
            s = str(v)
            table.add_row(k, s[:200] + "..." if len(s) > 200 else s)
        console.print(table)
    console.print()


def show_state(state: dict[str, Any], title: str = "State") -> None:
    if not _debug_enabled:
        return
    table = Table(title=title, show_header=True, border_style="dim")
    table.add_column("Field", style="cyan", min_width=20)
    table.add_column("Value", style="yellow")
    for key, value in state.items():
        if key == "messages":
            table.add_row("messages", f"[{len(value)} messages]" if value else "[]")
        elif key == "debug_log":
            table.add_row("debug_log", f"[{len(value)} entries]")
        elif hasattr(value, "model_dump"):
            table.add_row(key, str(value.model_dump()))
        else:
            s = str(value)
            if len(s) > 120:
                s = s[:120] + "..."
            table.add_row(key, s if value is not None else "[dim]None[/dim]")
    console.print(table)
    console.print()


def show_tool_call(name: str, params: dict[str, Any], result: Any, duration: float) -> None:
    if not _debug_enabled:
        return
    console.print(Panel(
        f"[bold green]🔧 Tool: {name}[/bold green]\n"
        f"[dim]Parameters:[/dim] {params}\n"
        f"[dim]Duration:[/dim] {duration:.2f}s\n"
        f"[bold]Result:[/bold] {str(result)[:300]}",
        border_style="green",
    ))
    console.print()
