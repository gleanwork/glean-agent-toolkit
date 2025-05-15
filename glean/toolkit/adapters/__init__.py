"""Adapters for different agent frameworks."""

from pydantic import BaseModel

from glean.toolkit.adapters.adk import ADKAdapter
from glean.toolkit.adapters.base import BaseAdapter
from glean.toolkit.adapters.crewai import CrewAIAdapter
from glean.toolkit.adapters.langchain import LangChainAdapter
from glean.toolkit.adapters.openai import (
    OpenAIAdapter,
    OpenAIFunctionDef,
    OpenAIToolDef,
)

__all__ = [
    "BaseAdapter",
    "ADKAdapter",
    "CrewAIAdapter",
    "LangChainAdapter",
    "OpenAIAdapter",
    "OpenAIToolDef",
    "OpenAIFunctionDef",
    "BaseModel",
]
