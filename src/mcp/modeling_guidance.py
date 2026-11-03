"""Read BASIC and optional bundled scripting references, not tool descriptions."""
from copy import deepcopy
from functools import lru_cache
import ast
import hashlib
import json
from pathlib import Path
from almond_mcp.instruction_text import public_tool_name

PACKAGE = Path(__file__).resolve().parent
BASIC_GUIDE = PACKAGE / "BASIC-INSTRUCTIONS.md"
SCRIPTING_SKILL = PACKAGE / "features/modeling/rhino3d-scripts"


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
    # Tool sources provide names only. Descriptions are delivered by tools/list.
    return sorted([BASIC_GUIDE, *_tool_sources(),
                   *(p for p in SCRIPTING_SKILL.rglob("*") if p.is_file())])


@lru_cache(maxsize=1)
def _snapshot() -> dict:
    inventory = source_files()
    raw = {p: _read_content(p) for p in inventory}

    def reference(path: Path) -> dict:
        return {"path": "src/mcp/" + path.relative_to(PACKAGE).as_posix(),
                "sha256": hashlib.sha256(raw[path]).hexdigest()}

    tools = set()
    for path in _tool_sources():
        for node in ast.walk(ast.parse(raw[path].decode("utf-8"))):
            if not isinstance(node, ast.FunctionDef) or not any(
                isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute)
                and isinstance(d.func.value, ast.Name) and d.func.value.id == "mcp"
                and d.func.attr == "tool" for d in node.decorator_list
            ):
                continue
            name = public_tool_name(node)
            if name in tools:
                raise ValueError(f"Duplicate public tool name: {name}")
            tools.add(name)
    skill_files = [SCRIPTING_SKILL / "INTEGRATION.md", SCRIPTING_SKILL / "SKILL.md",
                   *sorted((SCRIPTING_SKILL / "references").glob("*.md"))]
    scripting_skill = {
        "name": "rhino3d-scripts",
        "sources": [{**reference(p), "text": raw[p].decode("utf-8")} for p in skill_files],
    }
    if inventory != source_files() or any(_read_content(p) != value for p, value in raw.items()):
        raise RuntimeError("Guide source changed while reading; start a new session.")
    identity = {p.relative_to(PACKAGE).as_posix(): hashlib.sha256(value).hexdigest() for p, value in raw.items()}
    version = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    return {"tools": sorted(tools), "guide_version": version,
            "basic": raw[BASIC_GUIDE].decode("utf-8").strip(), "basic_refs": [reference(BASIC_GUIDE)],
            "scripting_skill": scripting_skill, "scripting_refs": [reference(p) for p in skill_files]}


def startup_instructions() -> str:
    snapshot = _snapshot()
    return ('Almond inspects and edits Rhino architecture and drawings. On first use, call '
            'get_modeling_guide() to read BASIC-INSTRUCTIONS.md. '
            f'guide_version={snapshot["guide_version"]}')


def read_guide(include_scripting: bool = False) -> dict:
    if type(include_scripting) is not bool:
        raise ValueError("include_scripting must be a boolean.")
    snapshot = _snapshot()
    result = {"status": "success", "guide_version": snapshot["guide_version"],
              "text": snapshot["basic"], "source_refs": deepcopy(snapshot["basic_refs"]),
              "tools": list(snapshot["tools"])}
    if include_scripting:
        result["scripting_skill"] = deepcopy(snapshot["scripting_skill"])
        result["source_refs"].extend(deepcopy(snapshot["scripting_refs"]))
    return result
