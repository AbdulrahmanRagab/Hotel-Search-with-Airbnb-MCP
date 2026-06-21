from __future__ import annotations

from datetime import date
from typing import Any, Optional, TypedDict, Annotated

from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field, field_validator


class SearchParams(BaseModel):
    location: str = Field(..., description="City, neighborhood, or address")
    check_in: date = Field(..., description="Check-in date (YYYY-MM-DD)")
    check_out: date = Field(..., description="Check-out date (YYYY-MM-DD)")
    guests: int = Field(default=1, ge=1, le=20, description="Number of guests")
    max_price_per_night: Optional[float] = Field(default=None, ge=0, description="Max price per night")
    currency: str = Field(default="USD", min_length=3, max_length=3, description="3-letter currency code")
    preferences: list[str] = Field(default_factory=list, description="User preferences (wifi, pool, etc.)")

    @field_validator("check_in", "check_out", mode="before")
    @classmethod
    def parse_date(cls, v: Any) -> date:
        if isinstance(v, date):
            return v
        if isinstance(v, str):
            return date.fromisoformat(v)
        raise ValueError(f"Cannot parse date from {v}")

    @field_validator("check_out")
    @classmethod
    def check_out_after_check_in(cls, v: date, info) -> date:
        check_in = info.data.get("check_in")
        if check_in is not None and v <= check_in:
            raise ValueError("check_out must be after check_in")
        return v


class DebugLogEntry(TypedDict, total=False):
    node: str
    timestamp: str
    snapshot: dict[str, Any]


class ToolCallRecord(TypedDict, total=False):
    tool_name: str
    params: dict[str, Any]
    result: Any
    error: Optional[str]
    duration_ms: float
    timestamp: str


class HotelSearchState(TypedDict, total=False):
    messages: Annotated[list[Any], add_messages]
    thread_id: str
    session_id: str
    step: int
    retry_count: int
    is_valid: bool
    user_intent: str
    search_params: Optional[SearchParams]
    available_tools: list[str]
    debug_log: list[DebugLogEntry]
    pending_tool_calls: list[dict[str, Any]]
    tool_history: list[ToolCallRecord]
    results: list[Any]
    error: Optional[str]
    final_response: Optional[str]
    human_approved: Optional[bool]
    interrupt_payload: Optional[dict[str, Any]]
    status: Optional[str]
