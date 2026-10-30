"""Read BASIC and public tool explanations without importing a model runtime."""
from copy import deepcopy
from functools import lru_cache
import ast
import hashlib
import json
from pathlib import Path
from almond_mcp.instruction_text import parse_instruction

PACKAGE = Path(__file__).resolve().parent
BASIC_GUIDE = PACKAGE / "BASIC-INSTRUCTIONS.md"
SCRIPTING_SKILL = PACKAGE / "features/modeling/rhino3d-scripts"
SCRIPTING_TOOLS = {"execute_rhino_script", "execute_project_python"}


def _read_content(path: Path) -> bytes:
    raw = path.read_bytes()
    return raw if path.suffix == ".png" else raw.decode("utf-8-sig").replace("\r\n", "\n").encode("utf-8")


def content_digest(path: Path) -> str:
    return hashlib.sha256(_read_content(path)).hexdigest()


def _tool_sources() -> list[Path]:
    sources = list((PACKAGE / "features").glob("*/tools.py"))
    runtime = PACKAGE / "runtime/mcp_server.py"
    # The standalone wheel excludes the checkout's execution runtime.
    if runtime.is_file():
        sources.append(runtime)
    return sorted(sources)


def source_files() -> list[Path]:
    tools = _tool_sources()
    return sorted([BASIC_GUIDE, *tools, *(p.with_name(p.stem + "-explain.md") for p in tools),
                   *(p for p in SCRIPTING_SKILL.rglob("*") if p.is_file())])


@lru_cache(maxsize=1)
def _snapshot() -> dict:
    inventory = source_files()
    raw = {p: _read_content(p) for p in inventory}

    def reference(path: Path) -> dict:
        return {"path": "src/mcp/" + path.relative_to(PACKAGE).as_posix(),
                "sha256": hashlib.sha256(raw[path]).hexdigest()}

    tools = {}
    for path in _tool_sources():
        note = path.with_name(path.stem + "-explain.md")
        for node in ast.walk(ast.parse(raw[path].decode("utf-8"))):
            if not isinstance(node, ast.FunctionDef) or not any(
                isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute)
                and isinstance(d.func.value, ast.Name) and d.func.value.id == "mcp"
                and d.func.attr == "tool" for d in node.decorator_list
            ):
                continue
            if node.name in tools:
                raise ValueError(f"Duplicate public tool instruction: {node.name}")
            tools[node.name] = {
                "text": parse_instruction(raw[note].decode("utf-8"), node.name, note),
                "source_refs": [reference(note)],
            }
            if node.name in SCRIPTING_TOOLS:
                # Same pinned sources as reading the installed skill, available
                # in every client without an external personal skill directory.
                skill_files = [SCRIPTING_SKILL / "INTEGRATION.md", SCRIPTING_SKILL / "SKILL.md",
                               *sorted((SCRIPTING_SKILL / "references").glob("*.md"))]
                tools[node.name]["scripting_skill"] = {
                    "name": "rhino3d-scripts",
                    "sources": [{**reference(p), "text": raw[p].decode("utf-8")} for p in skill_files],
                }
                tools[node.name]["source_refs"].extend(reference(p) for p in skill_files)
    if inventory != source_files() or any(_read_content(p) != value for p, value in raw.items()):
        raise RuntimeError("Guide source changed while reading; start a new session.")
    identity = {p.relative_to(PACKAGE).as_posix(): hashlib.sha256(value).hexdigest() for p, value in raw.items()}
    version = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    return {"tools": tools, "guide_version": version,
            "basic": raw[BASIC_GUIDE].decode("utf-8").strip(), "basic_refs": [reference(BASIC_GUIDE)]}


def startup_instructions() -> str:
    snapshot = _snapshot()
    return ('Almond inspects and edits Rhino architecture and drawings. On first use, call '
            'get_modeling_guide() to read BASIC-INSTRUCTIONS.md. '
            f'guide_version={snapshot["guide_version"]}')


def project_instructions() -> str:
    return _snapshot()["basic"]


def read_guide(tool: str = "") -> dict:
    snapshot = _snapshot()
    result = {"status": "success", "guide_version": snapshot["guide_version"]}
    if tool:
        if tool not in snapshot["tools"]:
            raise ValueError("Unknown Almond tool. Call get_modeling_guide() for available tools.")
        return {**result, "tool_name": tool, **deepcopy(snapshot["tools"][tool])}
    return {**result, "text": snapshot["basic"], "source_refs": deepcopy(snapshot["basic_refs"]),
            "tools": sorted(snapshot["tools"])}
