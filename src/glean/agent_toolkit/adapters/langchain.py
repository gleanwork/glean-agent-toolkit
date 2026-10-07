"""LangChain adapter for converting tool specifications."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypeAlias, cast

from pydantic import BaseModel

from glean.agent_toolkit.adapters.base import (
    BaseAdapter,
    ainvoke_tool,
    get_field_type,
    invoke_tool,
    is_error_payload,
    payload_to_text,
)
from glean.agent_toolkit.spec import ToolSpec

if TYPE_CHECKING:
    from glean.agent_toolkit.context import GleanContext

if TYPE_CHECKING:
    from langchain_core.tools import StructuredTool as LangchainTool  # pragma: no cover
else:
    LangchainTool = Any  # type: ignore  # noqa: N816

from pydantic import create_model as pydantic_create_model

ToolClass: Any = object
Field: Any = object
create_model = pydantic_create_model


class _FallbackStructuredTool:
    """Fallback for langchain_core.tools.StructuredTool."""

    name: str
    description: str
    func: Any
    coroutine: Any
    args_schema: Any

    def __init__(self, *args: Any, **kwargs: Any) -> None:  # noqa: D107
        pass


def _fallback_pydantic_field(*args: Any, **kwargs: Any) -> Any:  # noqa: N802
    """Fallback for pydantic.Field."""
    return None


def _fallback_pydantic_create_model(*args: Any, **kwargs: Any) -> Any:
    """Fallback for pydantic.create_model."""
    return None


class _FallbackToolException(Exception):  # noqa: N818 - mirrors LangChain's name
    """Fallback for langchain_core.tools.ToolException."""


try:
    from langchain_core.tools import StructuredTool as _ActualStructuredToolImport  # type: ignore
    from langchain_core.tools import ToolException as _ActualToolExceptionImport  # type: ignore
    from pydantic import Field as _ActualPydanticFieldImport  # type: ignore
    from pydantic import create_model as _actual_pydantic_create_model_import

    ToolClass = _ActualStructuredToolImport
    ToolException: type[Exception] = _ActualToolExceptionImport
    Field = _ActualPydanticFieldImport
    create_model = _actual_pydantic_create_model_import
    HAS_LANGCHAIN = True
except ImportError:  # pragma: no cover
    ToolClass = _FallbackStructuredTool  # type: ignore[assignment]
    ToolException = _FallbackToolException
    Field = _fallback_pydantic_field
    create_model = _fallback_pydantic_create_model
    HAS_LANGCHAIN = False


if TYPE_CHECKING:
    LangChainToolType: TypeAlias = "LangchainTool"
else:
    from typing import Any as LangChainToolType  # type: ignore


class LangChainAdapter(BaseAdapter[LangChainToolType]):
    """Adapter for LangChain tools."""

    def __init__(self, tool_spec: ToolSpec, ctx: GleanContext | None = None) -> None:
        """Initialize the adapter.

        Args:
            tool_spec: The tool specification
            ctx: Optional GleanContext to bind into tool invocations.
        """
        super().__init__(tool_spec, ctx)
        if not HAS_LANGCHAIN:
            raise ImportError(
                "langchain-core package is required for LangChain adapter. "
                "Install it with `pip install glean-agent-toolkit[langchain]`."
            )

    def to_tool(self) -> Any:
        """Convert to LangChain tool format.

        Builds a ``StructuredTool`` so multi-argument tools are invocable
        (the legacy single-input ``Tool`` rejects dict inputs with more
        than one key and calls its func positionally).

        LangChain's tool contract expects string returns. On a ``ToolResult``
        envelope the wrapper delivers the raw ``result`` payload on success
        (or a compact error dict on failure) and JSON-serializes it; other
        return values are JSON-serialized as-is. When an async_function is
        available, passes it as ``coroutine`` so LangChain can ``await`` it
        natively.

        Failures (an error ``ToolResult`` or an exception raised by the tool)
        are raised as ``ToolException`` with ``handle_tool_error=True``: the
        model still receives the same compact error JSON, and LangChain marks
        the resulting ``ToolMessage`` with ``status="error"``.

        Returns:
            LangChain StructuredTool instance
        """
        tool_spec = self.tool_spec
        ctx = self.ctx

        def _to_output(payload: Any) -> str:
            text = payload_to_text(payload)
            if is_error_payload(payload):
                raise ToolException(text)
            return text

        def _string_wrapper(**kwargs: Any) -> str:
            return _to_output(invoke_tool(tool_spec, ctx, kwargs))

        async def _async_string_wrapper(**kwargs: Any) -> str:
            return _to_output(await ainvoke_tool(tool_spec, ctx, kwargs))

        args_schema = self.tool_spec.input_model or self._create_args_schema()
        if args_schema is not None and not args_schema.model_fields:
            args_schema = None
        if args_schema is None:
            # StructuredTool requires an args_schema; use an empty model
            # for tools that take no arguments.
            args_schema = cast("type[BaseModel]", create_model(f"{self.tool_spec.name}Schema"))

        tool_kwargs: dict[str, Any] = {
            "name": self.tool_spec.name,
            "description": self.tool_spec.description,
            "func": _string_wrapper,
            "args_schema": args_schema,
            "handle_tool_error": True,
        }
        if tool_spec.async_function is not None:
            tool_kwargs["coroutine"] = _async_string_wrapper

        return ToolClass(**tool_kwargs)

    def _create_args_schema(self) -> type[BaseModel] | None:
        """Create a Pydantic model for the arguments schema.

        Returns:
            A Pydantic model class or None if no properties
        """
        json_schema = self.tool_spec.input_schema

        props = json_schema.get("properties", {})
        required = json_schema.get("required", [])

        if not props:
            return None

        field_defs: dict[str, tuple[type, Any]] = {}

        for name, schema in props.items():
            field_type = get_field_type(schema, use_date_types=True)
            is_required = name in required

            description = schema.get("description", "")

            if is_required:
                field_defs[name] = (field_type, Field(..., description=description))
            else:
                field_defs[name] = (field_type, Field(None, description=description))

        model = create_model(f"{self.tool_spec.name}Schema", **field_defs)  # type: ignore
        return cast(type[BaseModel], model)
