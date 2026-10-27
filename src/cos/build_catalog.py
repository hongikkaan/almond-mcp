"""Generate exact tool schemas from inert AST stubs, without importing Almond."""
from __future__ import annotations

import ast
import asyncio
import copy
from importlib.metadata import version
import json
from pathlib import Path
import sys
import types
import tomllib
from almond_mcp.instruction_text import read_tool_instruction

sys.dont_write_bytecode = True
from runtime import CATALOG, ENGINE, ROOT, digest, source_paths


def checked_versions() -> dict[str, str]:
    """Keep compatibility tied to the reviewed lock, not a generated tool count."""
    lock = tomllib.loads((ROOT.parents[1] / "uv.lock").read_text(encoding="utf-8"))
    result = {}
    for name in ("almond-mcp", "fastmcp", "mcp"):
        expected = {p["version"] for p in lock["package"] if p["name"] == name}
        actual = version(name)
        if expected != {actual}:
            raise RuntimeError(f"Runtime expects {name} version {sorted(expected)} from uv.lock; installed: {actual}.")
        result[name] = actual
    return result


def checked_stub(node: ast.FunctionDef) -> ast.FunctionDef:
    node = copy.deepcopy(node)
    allowed = (ast.Name, ast.Load, ast.Subscript, ast.Tuple, ast.BinOp, ast.BitOr, ast.Constant)
    inputs = [a.annotation for a in (*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs)]
    for annotation in inputs + [node.returns]:
        if annotation is None:
            continue
        # ToolResult is the reviewed image tool's return envelope, never an input type.
        if annotation is node.returns and isinstance(annotation, ast.Name) and annotation.id == "ToolResult":
            continue
        # The context tool optionally appends an image to its existing text response.
        # Admit this exact return shape, never nested/input ToolResult annotations.
        if (annotation is node.returns and isinstance(annotation, ast.BinOp)
                and isinstance(annotation.op, ast.BitOr)
                and isinstance(annotation.left, ast.Name) and annotation.left.id == "str"
                and isinstance(annotation.right, ast.Name) and annotation.right.id == "ToolResult"):
            continue
        for part in ast.walk(annotation):
            if not isinstance(part, allowed):
                raise ValueError(f"Review annotation in {node.name}: {ast.dump(part)}")
            if isinstance(part, ast.Name) and part.id not in {"str", "int", "StrictInt", "StrictFloat", "StrictBool", "float", "bool", "list", "dict"}:
                raise ValueError(f"Review annotation name {part.id} in {node.name}")
    for default in [*node.args.defaults, *node.args.kw_defaults]:
        if default is not None:
            ast.literal_eval(default)
    decorators = []
    external_doc = None
    for decorator in node.decorator_list:
        if isinstance(decorator, ast.Name) and decorator.id == "query_output":
            continue  # Known output projection; schemas are built from inert bodies.
        if (isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Name)
                and decorator.func.id == "tool_instruction"):
            if (len(decorator.args) != 2 or decorator.keywords
                    or not isinstance(decorator.args[0], ast.Name)
                    or decorator.args[0].id != "__file__"
                    or not isinstance(decorator.args[1], ast.Constant)
                    or decorator.args[1].value != node.name
                    or not hasattr(node, "_guidance_source")):
                raise ValueError(f"Unexpected instruction decorator: {node.name}")
            external_doc = read_tool_instruction(node._guidance_source, node.name)
            continue
        if not (isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute)
                and isinstance(decorator.func.value, ast.Name) and decorator.func.value.id == "mcp"
                and decorator.func.attr == "tool" and not decorator.args):
            raise ValueError(f"Unexpected tool decorator: {node.name}")
        for keyword in decorator.keywords:
            if keyword.arg != "annotations":
                raise ValueError(f"Review decorator option {keyword.arg} in {node.name}")
            ast.literal_eval(keyword.value)
        decorators.append(decorator)
    node.decorator_list = decorators
    doc = external_doc if external_doc is not None else ast.get_docstring(node, clean=False)
    node.body = ([ast.Expr(ast.Constant(doc))] if doc else []) + [
        ast.Raise(ast.Call(ast.Name("RuntimeError", ast.Load()),
                          [ast.Constant("Catalog stub must never execute")], []), None)
    ]
    return node


def collect_tool_functions(server_path: Path) -> list[ast.FunctionDef]:
    sources = [server_path, *sorted(server_path.parent.glob("features/*/tools.py"))]
    functions = []
    for path in sources:
        tree = ast.parse(path.read_text(encoding="utf-8-sig"))
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                node._guidance_source = str(path)
        candidates = list(tree.body)
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and node.name == "register":
                candidates.extend(node.body)
        functions.extend(n for n in candidates if isinstance(n, ast.FunctionDef) and
                         any(isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute)
                             and isinstance(d.func.value, ast.Name) and d.func.value.id == "mcp"
                             and d.func.attr == "tool" for d in n.decorator_list))
    names = [node.name for node in functions]
    if len(names) != len(set(names)):
        raise RuntimeError("Duplicate public tool definitions across feature sources.")
    return functions


async def generate(engine: Path = ENGINE) -> dict:
    packages = checked_versions()
    server_loaded = "almond_mcp.server" in sys.modules
    from fastmcp import FastMCP
    from fastmcp.tools import ToolResult
    from pydantic import StrictInt, StrictFloat, StrictBool
    paths = source_paths(engine)
    sources = {name: digest(path) for name, path in paths.items()}
    functions = collect_tool_functions(paths["server"])
    entry = ast.parse(paths["entry"].read_text(encoding="utf-8-sig"))
    for node in ast.walk(entry):
        if isinstance(node, ast.FunctionDef) and any(
            isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute)
            and isinstance(d.func.value, ast.Name) and d.func.value.id == "mcp"
            and d.func.attr == "tool" for d in node.decorator_list
        ):
            node._guidance_source = str(paths["entry"])
            functions.append(node)
    module = types.ModuleType("_almondcos_schema_stubs")
    module.mcp = FastMCP("AlmondCOS schema build")
    module.ToolResult = ToolResult
    module.StrictInt = StrictInt
    module.StrictFloat = StrictFloat
    module.StrictBool = StrictBool
    sys.modules[module.__name__] = module
    tree = ast.Module(body=[checked_stub(n) for n in functions], type_ignores=[])
    exec(compile(ast.fix_missing_locations(tree), "<AlmondCOS schemas only>", "exec"), module.__dict__)
    tools = [t.to_mcp_tool().model_dump(mode="json", by_alias=True, exclude_none=True)
             for t in await module.mcp.list_tools()]
    if not tools:
        raise RuntimeError("No common tools found in the current source.")
    if not server_loaded and "almond_mcp.server" in sys.modules:
        raise RuntimeError("Catalog generation must not import the Almond server.")
    if sources != {name: digest(path) for name, path in source_paths(engine).items()}:
        raise RuntimeError("Tool sources changed during schema discovery. Start a new client session.")
    return {
        "format": 1,
        "packages": packages,
        "sources": sources,
        "tools": sorted(tools, key=lambda t: t["name"]),
    }


if __name__ == "__main__":
    catalog = asyncio.run(generate())
    CATALOG.parent.mkdir(parents=True, exist_ok=True)
    CATALOG.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Generated {len(catalog['tools'])} tool schemas without importing Almond.")
