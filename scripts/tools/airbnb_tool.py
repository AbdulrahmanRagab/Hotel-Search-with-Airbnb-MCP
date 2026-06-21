"""
Airbnb Tool — wraps an MCP server that exposes Airbnb search as tools.

Architecture:
    Airbnb MCP Server (stdio/HTTP) → MCPClient → LangChain BaseTool → Agent
"""
from __future__ import annotations

import asyncio
import os
import json
import logging
from typing import Any

from langchain_core.tools import tool
from pydantic import Field

logger = logging.getLogger(__name__)


# ============================================================
# 🔌 MCP Client (with dynamic stdio command and mock fallback)
# ============================================================

class AirbnbMCPClient:
    """
    Connects to an Airbnb MCP server.

    If configured via environment variables (AIRBNB_MCP_COMMAND and optionally AIRBNB_MCP_ARGS),
    this client connects to a real stdio-based MCP server. Otherwise, it defaults to
    realistic mock listings data.
    """

    def __init__(self, server_url: str = "stdio://airbnb-mcp"):
        self.server_url = server_url
        self.connected = False
        
        # Load stdio configurations from env
        self.command = os.getenv("AIRBNB_MCP_COMMAND")
        args_str = os.getenv("AIRBNB_MCP_ARGS", "")
        self.args = [a.strip() for a in args_str.split(",") if a.strip()] if args_str else []

    async def connect(self) -> None:
        if self.command:
            logger.info("AirbnbMCPClient: Configured to connect via command: %s (args: %s)", self.command, self.args)
        else:
            logger.info("AirbnbMCPClient: AIRBNB_MCP_COMMAND not set. Using mock fallback.")
        self.connected = True

    async def disconnect(self) -> None:
        self.connected = False

    async def search(
        self,
        location: str,
        check_in: str | None = None,
        check_out: str | None = None,
        guests: int = 1,
        max_price: float | None = None,
    ) -> dict[str, Any]:
        if self.command:
            try:
                from mcp import ClientSession, StdioServerParameters
                from mcp.client.stdio import stdio_client

                server_params = StdioServerParameters(
                    command=self.command,
                    args=self.args,
                    env=os.environ.copy()
                )
                logger.info("Connecting to real MCP server using stdio...")
                async with stdio_client(server_params) as (read_stream, write_stream):
                    async with ClientSession(read_stream, write_stream) as session:
                        await session.initialize()
                        logger.info("Calling airbnb_search on real MCP server...")
                        result = await session.call_tool(
                            "airbnb_search",
                            {
                                "location": location,
                                "check_in": check_in,
                                "check_out": check_out,
                                "guests": guests,
                                "max_price_per_night": max_price,
                            }
                        )
                        if hasattr(result, "content") and result.content:
                            text_content = result.content[0].text
                            try:
                                return json.loads(text_content)
                            except Exception:
                                return {"result": text_content, "source": "real_airbnb_mcp"}
                        return {"result": str(result), "source": "real_airbnb_mcp"}
            except ImportError:
                logger.warning("mcp package not installed. Install with: pip install mcp")
            except Exception as e:
                logger.warning("Failed to connect or query real Airbnb MCP server: %s. Falling back to mock data.", e)

        # Fallback to Mock listings
        await asyncio.sleep(0.5)  # Simulate API latency

        listings = [
            {
                "id": "AB12345",
                "name": f"Cozy Apartment in {location}",
                "price_per_night": 120,
                "currency": "USD",
                "rating": 4.8,
                "reviews": 234,
                "amenities": ["WiFi", "Kitchen", "AC", "Washer"],
                "distance_to_center_km": 1.2,
                "url": f"https://airbnb.com/rooms/AB12345",
            },
            {
                "id": "AB67890",
                "name": f"Luxury Villa in {location}",
                "price_per_night": 350,
                "currency": "USD",
                "rating": 4.9,
                "reviews": 567,
                "amenities": ["Pool", "WiFi", "Kitchen", "AC", "Parking"],
                "distance_to_center_km": 3.5,
                "url": f"https://airbnb.com/rooms/AB67890",
            },
            {
                "id": "AB11111",
                "name": f"Budget Room near {location} Center",
                "price_per_night": 45,
                "currency": "USD",
                "rating": 4.3,
                "reviews": 89,
                "amenities": ["WiFi", "AC"],
                "distance_to_center_km": 0.8,
                "url": f"https://airbnb.com/rooms/AB11111",
            },
        ]

        if max_price is not None:
            listings = [l for l in listings if l["price_per_night"] <= max_price]

        return {
            "location": location,
            "check_in": check_in,
            "check_out": check_out,
            "guests": guests,
            "total_results": len(listings),
            "listings": listings,
            "source": "airbnb_mcp_mock",
        }


# Singleton client
_mcp_client = AirbnbMCPClient()


# ============================================================
# 🛠️ LangChain tool wrapper
# ============================================================

@tool
async def airbnb_search(
    location: str = Field(description="City, neighborhood, or address to search"),
    check_in: str | None = Field(default=None, description="Check-in date YYYY-MM-DD"),
    check_out: str | None = Field(default=None, description="Check-out date YYYY-MM-DD"),
    guests: int = Field(default=1, description="Number of guests"),
    max_price_per_night: float | None = Field(default=None, description="Max price per night"),
) -> dict[str, Any]:
    """
    Search for accommodations via the Airbnb MCP server.

    Returns a dict with `listings` (name, price, rating, amenities, URL).
    Use this whenever the user wants to find a place to stay.
    """
    if not _mcp_client.connected:
        await _mcp_client.connect()

    return await _mcp_client.search(
        location=location,
        check_in=check_in,
        check_out=check_out,
        guests=guests,
        max_price=max_price_per_night,
    )
