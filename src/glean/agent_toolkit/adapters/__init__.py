"""Adapters for converting tool specifications to framework-specific formats."""

__all__ = [
    "BaseAdapter",
    "ADKAdapter",
    "CrewAIAdapter",
    "LangChainAdapter",
    "OpenAIAdapter",
    "OpenAIToolDef",
    "OpenAIFunctionDef",
]

_LAZY_IMPORTS: dict[str, tuple[str, str]] = {
    "BaseAdapter": (".base", "BaseAdapter"),
    "ADKAdapter": (".adk", "ADKAdapter"),
    "CrewAIAdapter": (".crewai", "CrewAIAdapter"),
    "LangChainAdapter": (".langchain", "LangChainAdapter"),
    "OpenAIAdapter": (".openai", "OpenAIAdapter"),
    "OpenAIToolDef": (".openai", "OpenAIToolDef"),
    "OpenAIFunctionDef": (".openai", "OpenAIFunctionDef"),
}


def __getattr__(name: str) -> object:
    entry = _LAZY_IMPORTS.get(name)
    if entry is not None:
        module_path, attr = entry
        import importlib

        mod = importlib.import_module(module_path, __name__)
        value = getattr(mod, attr)
        globals()[name] = value  # cache for subsequent access
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
