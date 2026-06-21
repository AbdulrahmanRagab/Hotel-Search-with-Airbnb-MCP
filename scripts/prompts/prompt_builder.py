"""
Dynamic Prompt Builder — Jinja2-based templating.

Why Jinja2?
- Decouple prompts from Python code (separate .j2 files).
- Inject ANY runtime data: tool lists, dates, user prefs, retry counts.
- Conditional rendering with {% if %}.
- Filters, loops, macros — full template engine.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import json

from jinja2 import Environment, FileSystemLoader, select_autoescape

TEMPLATES_DIR = Path(__file__).parent / "templates"

# Single shared environment (cached at import time)
env = Environment(
    loader=FileSystemLoader(TEMPLATES_DIR),
    autoescape=select_autoescape(disabled_extensions=("j2",)),
    trim_blocks=True,
    lstrip_blocks=True,
)


def build_prompt(template_name: str, **kwargs: Any) -> str:
    """
    Render a Jinja2 template with dynamic variables.

    Usage:
        build_prompt("system.j2", today=date.today(), tool_names=["search","weather"])
        build_prompt("intent_parser.j2", user_message="...", json_schema={...})

    Args:
        template_name: Filename inside scripts/prompts/templates/
        **kwargs: Variables to substitute into the template

    Returns:
        Rendered prompt string
    """
    # Inject `today` by default — most templates need it
    kwargs.setdefault("today", date.today().isoformat())

    template = env.get_template(template_name)
    return template.render(**kwargs)


def list_templates() -> list[str]:
    """List all available template names."""
    return [p.name for p in TEMPLATES_DIR.glob("*.j2")]


def to_pretty_json(value: Any) -> str:
    """
    Render Python objects as pretty JSON for prompt templates.
    Useful for showing dicts, lists, Pydantic models, and tool results clearly.
    """
    if hasattr(value, "model_dump"):
        value = value.model_dump()
    return json.dumps(
        value,
        indent=2,
        ensure_ascii=False,
        default=str,
    )


env.filters["to_pretty_json"] = to_pretty_json
