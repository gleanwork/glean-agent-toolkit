import os

import requests
from pydantic import BaseModel

from glean.agent_toolkit import tool_spec


class WeatherResponse(BaseModel):
    temperature: float
    condition: str
    humidity: int
    city: str


@tool_spec(
    name="get_current_weather",
    description="Get current weather information for a specified city",
    output_model=WeatherResponse,
)
def get_weather(city: str, units: str = "celsius") -> WeatherResponse:
    """Fetch current weather for a city."""
    # Replace with actual weather API call
    api_key = os.getenv("WEATHER_API_KEY")
    response = requests.get(
        f"https://api.weather.com/v1/current?key={api_key}&q={city}&units={units}"
    )
    data = response.json()

    return WeatherResponse(
        temperature=data["temp"], condition=data["condition"], humidity=data["humidity"], city=city
    )


# Use across frameworks
openai_weather = get_weather.as_openai_tool()
langchain_weather = get_weather.as_langchain_tool()
crewai_weather = get_weather.as_crewai_tool()
