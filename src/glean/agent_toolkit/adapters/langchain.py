"""LangChain adapter for converting tool specifications."""

from __future__ import annotations

import functools
import json
from typing import TYPE_CHECKING, Any, TypeAlias, cast

from pydantic import BaseModel

from glean.agent_toolkit.adapters.base import BaseAdapter, get_field_type
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


try:
    from langchain_core.tools import StructuredTool as _ActualStructuredToolImport  # type: ignore
    from pydantic import Field as _ActualPydanticFieldImport  # type: ignore
    from pydantic import create_model as _actual_pydantic_create_model_import

    ToolClass = _ActualStructuredToolImport
    Field = _ActualPydanticFieldImport
    create_model = _actual_pydantic_create_model_import
    HAS_LANGCHAIN = True
except ImportError:  # pragma: no cover
    ToolClass = _FallbackStructuredTool  # type: ignore[assignment]
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

        LangChain's tool contract expects string returns.  The wrapper
        JSON-serializes whatever the underlying function produces.
        When an async_function is available, passes it as ``coroutine``
        so LangChain can ``await`` it natively.

        Returns:
            LangChain StructuredTool instance
        """
        original_func = self.tool_spec.function
        async_func = self.tool_spec.async_function
        if self.ctx is not None:
            original_func = functools.partial(original_func, self.ctx)
            if async_func is not None:
                async_func = functools.partial(async_func, self.ctx)

        def _string_wrapper(**kwargs: Any) -> str:
            result = original_func(**kwargs)
            if isinstance(result, str):
                return result
            return json.dumps(result, default=str)

        async def _async_string_wrapper(**kwargs: Any) -> str:
            result = await async_func(**kwargs)  # type: ignore[misc]
            if isinstance(result, str):
                return result
            return json.dumps(result, default=str)

        args_schema = self._create_args_schema()
        if args_schema is None:
            # StructuredTool requires an args_schema; use an empty model
            # for tools that take no arguments.
            args_schema = cast("type[BaseModel]", create_model(f"{self.tool_spec.name}Schema"))

        tool_kwargs: dict[str, Any] = {
            "name": self.tool_spec.name,
            "description": self.tool_spec.description,
            "func": _string_wrapper,
            "args_schema": args_schema,
        }
        if async_func is not None:
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
