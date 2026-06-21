"""
Weather Tool — current conditions + forecast for any location.
"""
from __future__ import annotations

import asyncio
import os
from typing import Any

import httpx
from langchain_core.tools import tool
from pydantic import Field

from scripts.config.settings import settings


@tool
async def get_weather(
    location: str = Field(description="City name or coordinates"),
    units: str = Field(default="metric", description="'metric' (Celsius) or 'imperial' (Fahrenheit)"),
) -> dict[str, Any]:
    """
    Get current weather and 3-day forecast for a location.

    Returns temperature, condition, humidity, wind, and forecast.
    """
    api_key = settings.openweather_api_key or os.getenv("OPENWEATHER_API_KEY", "mock")

    # Mock data fallback
    if not api_key or api_key == "mock":
        await asyncio.sleep(0.2)
        return {
            "location": location,
            "temperature": 22 if units == "metric" else 72,
            "feels_like": 20 if units == "metric" else 68,
            "units": units,
            "condition": "Partly cloudy",
            "humidity": 65,
            "wind_speed": 12 if units == "metric" else 7.5,
            "forecast": [
                {"day": "Tomorrow", "high": 25, "low": 18, "condition": "Sunny"},
                {"day": "Day after", "high": 23, "low": 17, "condition": "Cloudy"},
            ],
            "source": "mock",
        }

    # Real API
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://api.openweathermap.org/data/2.5/weather",
                params={"q": location, "units": units, "appid": api_key},
            )
            response.raise_for_status()
            data = response.json()
            return {
                "location": data["name"],
                "temperature": data["main"]["temp"],
                "feels_like": data["main"]["feels_like"],
                "units": units,
                "condition": data["weather"][0]["description"],
                "humidity": data["main"]["humidity"],
                "wind_speed": data["wind"]["speed"],
                "source": "openweathermap",
            }
    except Exception as e:
        return {"location": location, "error": str(e)}
