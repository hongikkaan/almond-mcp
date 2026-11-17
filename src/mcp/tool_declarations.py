"""Read one set of MCP tool declarations without importing executable handlers."""

from __future__ import annotations

import ast
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, get_args

from almond_mcp.instruction_text import read_tool_instruction
from almond_mcp.public_names import internal_tool_name


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


@dataclass(frozen=True)
class ToolDeclaration:
    name: str
    source: Path
    node: ast.FunctionDef


def declaration_sources(package_root: Path = PACKAGE, *,
                        document_entry: Path | None = None) -> tuple[Path, ...]:
    """Return the source paths for the selected executable registration scopes."""
    features = tuple(package_root.joinpath(*module.split(".")[1:]).with_suffix(".py")
                     for module in FEATURE_MODULES)
    return features if document_entry is None else (*features, document_entry)


def _tool_decorator(node: ast.expr) -> bool:
    return (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name) and node.func.value.id == "mcp"
            and node.func.attr == "tool")


def _public_tool_name(node: ast.FunctionDef) -> str:
    """Read an explicit literal MCP name without executing the tool module."""
    decorators = [decorator for decorator in node.decorator_list if _tool_decorator(decorator)]
    if len(decorators) != 1:
        raise ValueError(f"{node.name} must have exactly one MCP tool decorator.")
    for keyword in decorators[0].keywords:
        if keyword.arg == "name":
            name = ast.literal_eval(keyword.value)
            if not isinstance(name, str) or not name:
                raise ValueError("A public tool name must be a nonempty literal string.")
            return name
    return node.name


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
            name = _public_tool_name(node)
            if name in names:
                raise ValueError(f"Duplicate public tool name: {name}")
            names.add(name)
            declarations.append(ToolDeclaration(name, path, node))
    return tuple(declarations)


def checked_stub(node: ast.FunctionDef, *, source: Path | None = None) -> ast.FunctionDef:
    """Keep only reviewed declaration syntax and replace the executable body."""
    node = deepcopy(node)
    if node.type_params:
        raise ValueError(f"Review type parameters in {node.name}.")
    name = _public_tool_name(node)
    internal_name = internal_tool_name(name)
    # Resolve the reviewed argument to literal values before compiling the inert stub.
    if node.name == "get_policy" and name == "context_01-get_policy":
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
        for part in ast.walk(annotation):
            if not isinstance(part, allowed):
                raise ValueError(f"Review annotation in {node.name}: {ast.dump(part)}")
            if isinstance(part, ast.Name) and part.id not in {"str", "int", "StrictInt", "StrictFloat", "StrictBool", "float", "bool", "list", "dict", "StringListPatch", "Literal", "CreateRequest", "GetRequest", "ListRequest", "UpdateRequest"}:
                raise ValueError(f"Review annotation name {part.id} in {node.name}")
    for default in [*node.args.defaults, *node.args.kw_defaults]:
        if default is not None:
            ast.literal_eval(default)
    decorators = []
    external_doc = None
    for decorator in node.decorator_list:
        if isinstance(decorator, ast.Name) and decorator.id in {"query_output", "holon_output", "mcp_error_result"}:
            continue  # Known output projection; schemas are built from inert bodies.
        if (isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Name)
                and decorator.func.id == "query_output"):
            if (node.name != "get_asset_drawing" or decorator.args or len(decorator.keywords) != 1
                    or decorator.keywords[0].arg != "preserve_cross_drive_fields"
                    or ast.literal_eval(decorator.keywords[0].value) != {"package_dir"}):
                raise ValueError(f"Unexpected output projection: {node.name}")
            continue  # Reviewed output-only option; never execute its decorator.
        if (isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Name)
                and decorator.func.id == "tool_instruction"):
            if (len(decorator.args) != 2 or decorator.keywords
                    or not isinstance(decorator.args[0], ast.Name)
                    or decorator.args[0].id != "__file__"
                    or not isinstance(decorator.args[1], ast.Constant)
                    or decorator.args[1].value != internal_name
                    or source is None):
                raise ValueError(f"Unexpected instruction decorator: {node.name}")
            external_doc = read_tool_instruction(str(source), internal_name)
            continue
        if not (isinstance(decorator, ast.Call) and _tool_decorator(decorator) and not decorator.args):
            raise ValueError(f"Unexpected tool decorator: {node.name}")
        for keyword in decorator.keywords:
            if keyword.arg == "name":
                continue
            if keyword.arg == "title":
                title = ast.literal_eval(keyword.value)
                if not isinstance(title, str) or not title:
                    raise ValueError(f"Review tool title in {node.name}")
                continue
            if keyword.arg == "output_schema":
                if isinstance(keyword.value, ast.Dict):
                    expected = {"type": "object", "properties": {"result": {"type": "string"}},
                                "required": ["result"], "x-fastmcp-wrap-result": True}
                    if (node.name not in {"get_rhino_context", "get_objects", "get_object_intersections"}
                            or ast.literal_eval(keyword.value) != expected):
                        raise ValueError(f"Review output schema in {node.name}")
                    continue
                call = keyword.value
                if (not isinstance(call, ast.Call) or not isinstance(call.func, ast.Name)
                        or call.func.id != "public_output_schema" or len(call.args) != 1
                        or ast.literal_eval(call.args[0]) != internal_name
                        or len(call.keywords) != 1 or call.keywords[0].arg != "wrapped"
                        or type(ast.literal_eval(call.keywords[0].value)) is not bool):
                    raise ValueError(f"Review output schema in {node.name}")
                from almond_mcp.output_contracts import public_output_schema
                resolved = public_output_schema(internal_name, ast.literal_eval(call.keywords[0].value))
                keyword.value = ast.parse(repr(resolved), mode="eval").body
                continue
            if keyword.arg != "annotations":
                raise ValueError(f"Review decorator option {keyword.arg} in {node.name}")
            ast.literal_eval(keyword.value)
        decorators.append(decorator)
    node.decorator_list = decorators
    doc = external_doc if external_doc is not None else ast.get_docstring(node, clean=False)
    node.body = ([ast.Expr(ast.Constant(doc))] if doc else []) + [
        ast.Raise(ast.Call(ast.Name("RuntimeError", ast.Load()),
                          [ast.Constant("A tool declaration cannot execute its handler")], []), None)
    ]
    return node


def register_inert_tools(mcp, declarations: tuple[ToolDeclaration, ...]) -> None:
    """Compile reviewed metadata into FastMCP with bodies that cannot run tools."""
    from fastmcp.tools import ToolResult
    from pydantic import StrictBool, StrictFloat, StrictInt
    from almond_mcp.features.planning.requests import CreateRequest, GetRequest, ListRequest, UpdateRequest
    from almond_mcp.features.planning.updates import StringListPatch

    namespace = {
        "__name__": __name__,
        "mcp": mcp,
        "ToolResult": ToolResult,
        "StrictInt": StrictInt,
        "StrictFloat": StrictFloat,
        "StrictBool": StrictBool,
        "Literal": Literal,
        "StringListPatch": StringListPatch,
        "CreateRequest": CreateRequest,
        "GetRequest": GetRequest,
        "ListRequest": ListRequest,
        "UpdateRequest": UpdateRequest,
    }
    tree = ast.Module(body=[checked_stub(declaration.node, source=declaration.source)
                            for declaration in declarations], type_ignores=[])
    exec(compile(ast.fix_missing_locations(tree), "<Almond tool declarations>", "exec", dont_inherit=True),
         namespace)
