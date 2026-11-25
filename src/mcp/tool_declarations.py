"""Read one set of MCP tool declarations without importing executable handlers."""

from __future__ import annotations

import ast
from copy import copy, deepcopy
from dataclasses import dataclass
from functools import wraps
from inspect import signature
from pathlib import Path
from typing import Literal, get_args

from almond_mcp.output_contracts import public_output_schema
from almond_mcp.public_names import PUBLIC_TOOL_NAMES
from almond_mcp.tool_response import mcp_error_result


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


def _tool_options(internal_name, *, wrapped, annotations=None):
    options = {
        "name": _public_name(internal_name),
        "output_schema": public_output_schema(internal_name, wrapped=wrapped),
    }
    if annotations is not None:
        options["annotations"] = annotations
    return options


def _register_manipulate_view(mcp, **options):
    def register(handler):
        if not hasattr(mcp, "add_tool"):
            return mcp.tool(**options)(handler)
        from fastmcp.tools import FunctionTool

        tool = FunctionTool.from_function(handler, **options)
        # Keep flat wire fields but disclose both exclusive request branches.
        # FastMCP still validates each top-level argument through the handler signature.
        tool.parameters = {
            **tool.parameters,
            "properties": {key: {k: v for k, v in prop.items() if k != "default"}
                           for key, prop in tool.parameters["properties"].items()},
            "additionalProperties": False,
            "oneOf": [
                {
                    "properties": {"operation": {"const": "rotate"}},
                    "required": ["operation", "mode"],
                    "not": {"required": ["factor"]},
                },
                {
                    "properties": {"operation": {"const": "zoom"}, "factor": {"exclusiveMinimum": 0}},
                    "required": ["operation", "factor"],
                    "not": {"anyOf": [{"required": [key]} for key in ("mode", "yaw_deg", "pitch_deg")]},
                },
            ],
        }
        mcp.add_tool(tool)
        return handler

    return register


def public_tool(mcp, *, wrapped, annotations=None, errors=False):
    """Register the handler and the declarations used by the external catalog."""
    def register(handler):
        options = _tool_options(handler.__name__, wrapped=wrapped, annotations=annotations)
        parameters = signature(handler)

        @wraps(handler)
        def guided(*args, **kwargs):
            from almond_mcp.tool_guidance import guide_result
            arguments = parameters.bind(*args, **kwargs)
            arguments.apply_defaults()
            return guide_result(handler.__name__, handler(*args, **kwargs), arguments.arguments)

        add = _register_manipulate_view(mcp, **options) if handler.__name__ == "manipulate_view" else mcp.tool(**options)
        return add(mcp_error_result(guided) if errors else guided)

    return register


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


def _inert_registration(node: ast.FunctionDef) -> ast.Call:
    decorator = _public_tool_decorator(node)
    if len(decorator.args) != 1 or not isinstance(decorator.args[0], ast.Name) or decorator.args[0].id != "mcp":
        raise ValueError(f"Unexpected registration target: {node.name}")
    arguments = {}
    for keyword in decorator.keywords:
        if keyword.arg not in {"wrapped", "annotations", "errors"} or keyword.arg in arguments:
            raise ValueError(f"Unexpected registration option in {node.name}: {keyword.arg}")
        arguments[keyword.arg] = ast.literal_eval(keyword.value)
    if type(arguments.get("wrapped")) is not bool or type(arguments.pop("errors", False)) is not bool:
        raise ValueError(f"Invalid registration flags: {node.name}")
    annotations = arguments.get("annotations")
    if annotations is not None and (not isinstance(annotations, dict)
            or any(not isinstance(key, str) or type(value) is not bool for key, value in annotations.items())):
        raise ValueError(f"Invalid annotations: {node.name}")
    options = _tool_options(node.name, **arguments)
    mcp = ast.Name("mcp", ast.Load())
    special = node.name == "manipulate_view"
    register = ast.Name("_register_manipulate_view", ast.Load()) if special else ast.Attribute(mcp, "tool", ast.Load())
    return ast.Call(register, [mcp] if special else [],
                    [ast.keyword(key, ast.parse(repr(value), mode="eval").body) for key, value in options.items()])


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


def checked_stub(node: ast.FunctionDef) -> ast.FunctionDef:
    """Keep only reviewed declaration syntax and replace the executable body."""
    doc = ast.get_docstring(node)
    declaration = copy(node)
    declaration.body = []
    node = deepcopy(declaration)
    if node.type_params:
        raise ValueError(f"Review type parameters in {node.name}.")
    registration = _inert_registration(node)
    # Resolve the reviewed argument to literal values before compiling the inert stub.
    if node.name == "get_policy":
        from almond_mcp.modeling_guidance import PolicyName
        for argument in node.args.args:
            annotation = argument.annotation
            if argument.arg == "policy" and isinstance(annotation, ast.Name) and annotation.id == "PolicyName":
                argument.annotation = ast.parse(f"Literal[{get_args(PolicyName)!r}]", mode="eval").body
    allowed = (ast.Name, ast.Load, ast.Subscript, ast.Tuple, ast.BinOp, ast.BitOr, ast.Constant)
    arguments = (*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs,
                 node.args.vararg, node.args.kwarg)
    inputs = [argument.annotation for argument in arguments if argument is not None]
    for annotation in inputs + [node.returns]:
        if annotation is None:
            continue
        # ToolResult is the reviewed image tool's return envelope, never an input type.
        if annotation is node.returns and isinstance(annotation, ast.Name) and annotation.id == "ToolResult":
            continue
        # Fixed observations may append an image or mark an explicit error while
        # preserving their existing wrapped-string output schema.
        # Admit this exact return shape, never nested/input ToolResult annotations.
        if (annotation is node.returns and isinstance(annotation, ast.BinOp)
                and isinstance(annotation.op, ast.BitOr)
                and isinstance(annotation.left, ast.Name) and annotation.left.id == "str"
                and isinstance(annotation.right, ast.Name) and annotation.right.id == "ToolResult"):
            continue
        if (node.name == "apply_drawing_style"
                and isinstance(annotation, ast.Name) and annotation.id == "StandardDLayerPath"
                and any(argument.arg == "layer_path" and argument.annotation is annotation
                        for argument in node.args.args)):
            continue
        if (node.name == "resolve_object_intersection"
                and any(argument.arg == "user_dictionary" and argument.annotation is annotation
                        for argument in node.args.args)
                and ast.dump(annotation) == ast.dump(ast.parse("DictionaryFilter | None", mode="eval").body)):
            continue
        for part in ast.walk(annotation):
            if not isinstance(part, allowed):
                raise ValueError(f"Review annotation in {node.name}: {ast.dump(part)}")
            if isinstance(part, ast.Name) and part.id not in {"str", "int", "StrictInt", "StrictFloat", "StrictBool", "float", "bool", "list", "dict", "StringListPatch", "Literal", "CreateRequest", "GetRequest", "ListRequest", "UpdateRequest", "ObjectScope", "ObjectResultMode", "ObjectFilters", "ObjectOutput"}:
                raise ValueError(f"Review annotation name {part.id} in {node.name}")
    for default in [*node.args.defaults, *node.args.kw_defaults]:
        if default is not None:
            ast.literal_eval(default)
    for decorator in node.decorator_list:
        if _tool_decorator(decorator):
            continue
        if isinstance(decorator, ast.Name) and decorator.id in {"query_output", "holon_output"}:
            continue
        if (isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Name)
                and decorator.func.id == "query_output"
                and node.name == "get_asset_drawing" and not decorator.args and len(decorator.keywords) == 1
                and decorator.keywords[0].arg == "preserve_cross_drive_fields"
                and ast.literal_eval(decorator.keywords[0].value) == {"package_dir"}):
            continue
        raise ValueError(f"Unexpected output decorator: {node.name}")
    node.decorator_list = [registration]
    node.body = ([ast.Expr(ast.Constant(doc))] if doc else []) + [
        ast.Raise(ast.Call(ast.Name("RuntimeError", ast.Load()),
                          [ast.Constant("A tool declaration cannot execute its handler")], []), None)
    ]
    return node


def register_inert_tools(mcp, declarations: tuple[ToolDeclaration, ...]) -> None:
    """Compile reviewed metadata into FastMCP with bodies that cannot run tools."""
    from fastmcp.tools import ToolResult
    from pydantic import StrictBool, StrictFloat, StrictInt
    from almond_mcp.features.context.object_inputs import DictionaryFilter, ObjectFilters, ObjectOutput, ObjectResultMode, ObjectScope

    from almond_mcp.features.drawings.standard import StandardDLayerPath
    from almond_mcp.features.planning.requests import CreateRequest, GetRequest, ListRequest, UpdateRequest
    from almond_mcp.features.planning.updates import StringListPatch

    namespace = {
        "__name__": __name__,
        "mcp": mcp,
        "_register_manipulate_view": _register_manipulate_view,
        "ToolResult": ToolResult,
        "StandardDLayerPath": StandardDLayerPath,
        "StrictInt": StrictInt,
        "StrictFloat": StrictFloat,
        "StrictBool": StrictBool,
        "Literal": Literal,
        "ObjectScope": ObjectScope,
        "ObjectResultMode": ObjectResultMode,
        "ObjectFilters": ObjectFilters,
        "DictionaryFilter": DictionaryFilter,
        "ObjectOutput": ObjectOutput,
        "StringListPatch": StringListPatch,
        "CreateRequest": CreateRequest,
        "GetRequest": GetRequest,
        "ListRequest": ListRequest,
        "UpdateRequest": UpdateRequest,
    }
    tree = ast.Module(body=[checked_stub(declaration.node)
                            for declaration in declarations], type_ignores=[])
    exec(compile(ast.fix_missing_locations(tree), "<Almond tool declarations>", "exec", dont_inherit=True),
         namespace)
