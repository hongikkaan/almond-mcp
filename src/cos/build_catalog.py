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

sys.dont_write_bytecode = True
from runtime import CATALOG, ENGINE, digest, source_paths


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
        for part in ast.walk(annotation):
            if not isinstance(part, allowed):
                raise ValueError(f"Review annotation in {node.name}: {ast.dump(part)}")
            if isinstance(part, ast.Name) and part.id not in {"str", "int", "StrictInt", "StrictFloat", "float", "bool", "list", "dict"}:
                raise ValueError(f"Review annotation name {part.id} in {node.name}")
    for default in [*node.args.defaults, *node.args.kw_defaults]:
        if default is not None:
            ast.literal_eval(default)
    for decorator in node.decorator_list:
        if not (isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute)
                and isinstance(decorator.func.value, ast.Name) and decorator.func.value.id == "mcp"
                and decorator.func.attr == "tool" and not decorator.args):
            raise ValueError(f"Unexpected tool decorator: {node.name}")
        for keyword in decorator.keywords:
            if keyword.arg != "annotations":
                raise ValueError(f"Review decorator option {keyword.arg} in {node.name}")
            ast.literal_eval(keyword.value)
    doc = ast.get_docstring(node, clean=False)
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
    from fastmcp import FastMCP
    from fastmcp.tools import ToolResult
    from pydantic import StrictInt, StrictFloat
    paths = source_paths(engine)
    functions = collect_tool_functions(paths["server"])
    entry = ast.parse(paths["entry"].read_text(encoding="utf-8-sig"))
    project_info = next(n for n in ast.walk(entry)
                        if isinstance(n, ast.FunctionDef) and n.name == "almond_project_info")
    functions.append(project_info)
    module = types.ModuleType("_almondcos_schema_stubs")
    module.mcp = FastMCP("AlmondCOS schema build")
    module.ToolResult = ToolResult
    module.StrictInt = StrictInt
    module.StrictFloat = StrictFloat
    sys.modules[module.__name__] = module
    tree = ast.Module(body=[checked_stub(n) for n in functions], type_ignores=[])
    exec(compile(ast.fix_missing_locations(tree), "<AlmondCOS schemas only>", "exec"), module.__dict__)
    tools = [t.to_mcp_tool().model_dump(mode="json", by_alias=True, exclude_none=True)
             for t in await module.mcp.list_tools()]
    if len(tools) != 77:
        raise RuntimeError(f"Expected the inspected 77 tools; got {len(tools)}. Review the changed package.")
    if "almond_mcp.server" in sys.modules:
        raise RuntimeError("Catalog generation must not import the Almond server.")
    return {
        "format": 1,
        "packages": {p: version(p) for p in ("almond-mcp", "fastmcp", "mcp")},
        "sources": {name: digest(path) for name, path in paths.items()},
        "tools": sorted(tools, key=lambda t: t["name"]),
    }


if __name__ == "__main__":
    catalog = asyncio.run(generate())
    CATALOG.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Generated {len(catalog['tools'])} tool schemas without importing Almond.")
