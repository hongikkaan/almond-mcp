"""Read one set of MCP tool declarations without importing executable handlers."""

from __future__ import annotations

import ast
import json
from dataclasses import dataclass
from functools import lru_cache
from inspect import Parameter, signature
from pathlib import Path

from fastmcp.server.middleware import Middleware
from fastmcp.tools import FunctionTool, ToolResult
from jsonschema import Draft202012Validator

from almond_mcp.output_contracts import public_output_schema, public_tool_contract
from almond_mcp.public_names import PUBLIC_TOOL_NAMES
from almond_mcp.tool_response import error_payload, mcp_error_result, transform_response


PACKAGE = Path(__file__).resolve().parent
FEATURE_MODULES = (
    "almond_mcp.features.assets.tools",
    "almond_mcp.features.capture.tools",
    "almond_mcp.features.components.tools",
    "almond_mcp.features.context.tools",
    "almond_mcp.features.diagrams.tools",
    "almond_mcp.features.drawings.tools",
    "almond_mcp.features.egress.tools",
    "almond_mcp.features.grasshopper.tools",
    "almond_mcp.features.guidance.tools",
    "almond_mcp.features.modeling.tools",
    "almond_mcp.features.planning.tools",
    "almond_mcp.features.scenes.tools",
    "almond_mcp.features.structure.tools",
)


def _public_name(internal_name: str) -> str:
    try:
        return PUBLIC_TOOL_NAMES[internal_name]
    except KeyError as exc:
        raise ValueError(f"No public tool name for {internal_name!r}.") from exc


@dataclass(frozen=True)
class ToolDeclaration:
    name: str
    node: ast.FunctionDef


def declaration_sources(package_root: Path = PACKAGE, *,
                        document_entry: Path | None = None) -> tuple[Path, ...]:
    """Return the source paths for the selected executable registration scopes."""
    features = tuple(package_root.joinpath(*module.split(".")[1:]).with_suffix(".py")
                     for module in FEATURE_MODULES)
    return features if document_entry is None else (*features, document_entry)


def _tool_decorator(node: ast.expr) -> bool:
    return isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "public_tool"


def _public_tool_decorator(node: ast.FunctionDef) -> ast.Call:
    decorators = [decorator for decorator in node.decorator_list if _tool_decorator(decorator)]
    if len(decorators) != 1:
        raise ValueError(f"{node.name} must have exactly one public_tool decorator.")
    return decorators[0]


def inspect_declarations(sources: tuple[Path, ...], *,
                         captured_bytes: dict[Path, bytes] | None = None) -> tuple[ToolDeclaration, ...]:
    """Read tools at module level or directly in their registration function."""
    declarations = []
    names = set()
    for path in sources:
        source = path.read_bytes() if captured_bytes is None else captured_bytes[path]
        body = ast.parse(source, filename=str(path)).body
        candidates = list(body)
        for node in body:
            if (isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and node.name in {"register", "configure_project_context"}):
                candidates.extend(node.body)
        for node in candidates:
            if (not isinstance(node, ast.FunctionDef)
                    or not any(_tool_decorator(decorator) for decorator in node.decorator_list)):
                continue
            name = _public_name(node.name)
            if name in names:
                raise ValueError(f"Duplicate public tool name: {name}")
            names.add(name)
            declarations.append(ToolDeclaration(name, node))
    return tuple(declarations)


@lru_cache(maxsize=None)
def _payload_schema(name):
    return public_output_schema(name, wrapped=False)


def _project(value, schema):
    """Keep declared fields, descending into records but leaving opaque user JSON intact."""
    variants = schema.get("anyOf", schema.get("oneOf", ()))
    if variants:
        for branch in variants:
            if Draft202012Validator(branch).is_valid(value):
                return _project(value, branch)
    if isinstance(value, dict):
        properties = schema.get("properties")
        additional = schema.get("additionalProperties")
        if properties is None:
            if isinstance(additional, dict) and additional:
                return {key: _project(item, additional) for key, item in value.items()}
            return value
        required = schema.get("required", ())
        projected = {}
        for key, item in value.items():
            field = properties.get(key)
            if field is None:
                continue
            if item is None and key not in required and not Draft202012Validator(field).is_valid(None):
                continue
            projected[key] = _project(item, field)
        return projected
    if isinstance(value, list) and schema.get("items"):
        return [_project(item, schema["items"]) for item in value]
    return value


def public_result(name: str, payload: dict) -> dict:
    return _project(payload, _payload_schema(name))


def _bound_input(contract):
    schema = contract["input_schema"]
    if "connection_id" in schema.get("properties", {}):
        del schema["properties"]["connection_id"]
        schema["required"].remove("connection_id")
        if not schema["required"]:
            del schema["required"]
    return schema


class PublicToolBoundary(Middleware):
    """Check wire arguments before the document runtime translates paths or creates files."""

    def __init__(self):
        self.validators = {}

    async def on_call_tool(self, context, call_next):
        name = context.message.name
        if name not in self.validators:
            return await call_next(context)
        validator, wrapped = self.validators[name]
        failure = next(validator.iter_errors(context.message.arguments or {}), None)
        if failure:
            body = error_payload(f"{failure.json_path}: {failure.message}", error_code="invalid_arguments")
            serialized = json.dumps(body, ensure_ascii=False)
            return ToolResult(content=serialized, structured_content={"result": serialized} if wrapped else body,
                              is_error=True)
        result = await call_next(context)
        # Some compact contracts report a failure through message/error_code
        # and MCP isError. Classify the original body before removing status.
        return transform_response(result, lambda payload: public_result(name, payload),
                                  mark_errors="status" not in _payload_schema(name).get("properties", {}))


def _register(mcp, name, handler, annotations, *, executable):
    contract = public_tool_contract(name)
    parameters = _bound_input(contract)
    if executable:
        accepts = signature(handler).parameters
        required = {key for key, param in accepts.items() if param.default is Parameter.empty}
        if accepts.keys() != parameters["properties"].keys() or not required.issubset(parameters.get("required", [])):
            raise ValueError(f"The registered handler signature disagrees with the public declaration for {name}")
    mcp.add_tool(FunctionTool(
        name=name, description=contract["description"], parameters=parameters,
        output_schema=contract["output_schema"], annotations=annotations, fn=handler,
    ))
    if executable:
        boundary = next((item for item in mcp.middleware if isinstance(item, PublicToolBoundary)), None)
        if boundary is None:
            boundary = PublicToolBoundary()
            mcp.add_middleware(boundary)
        boundary.validators[name] = Draft202012Validator(parameters), contract["wrapped"]


def public_tool(mcp, *, annotations=None, errors=False):
    def register(handler):
        name = _public_name(handler.__name__)
        _register(mcp, name, mcp_error_result(handler) if errors else handler, annotations, executable=True)
        return handler
    return register


def register_inert_tools(mcp, declarations: tuple[ToolDeclaration, ...]) -> None:
    """Read registration metadata without executing handler source or annotations."""
    def unavailable():
        raise RuntimeError("A tool declaration cannot execute its handler")

    for declaration in declarations:
        decorator = _public_tool_decorator(declaration.node)
        annotations = next((ast.literal_eval(option.value) for option in decorator.keywords
                            if option.arg == "annotations"), None)
        _register(mcp, declaration.name, unavailable, annotations, executable=False)
