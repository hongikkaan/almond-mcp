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
METADATA_POLICY = PACKAGE / "modeling_policy.json"
RHINOCODE_POLICY = PACKAGE / "RHINOCODE-INSTRUCTIONS.md"
POLICIES = {
    "basic": "건축 설계·모델링·도면 검증 지침과 공통 도구 목록",
    "metadata": "객체·그룹 메타데이터 키, 레이어·재료 기록 규칙",
    "rhino_scripting": "Rhino 스크립트 작성과 API 참고 자료",
    "rhinocode": "RhinoCode 코드·Rhino 커맨드 실행과 결과 확인",
}


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
    return sorted([BASIC_GUIDE, METADATA_POLICY, RHINOCODE_POLICY, *_tool_sources(),
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
            "scripting_skill": scripting_skill, "scripting_refs": [reference(p) for p in skill_files],
            "metadata": json.loads(raw[METADATA_POLICY]), "metadata_refs": [reference(METADATA_POLICY)],
            "rhinocode": raw[RHINOCODE_POLICY].decode("utf-8").strip(),
            "rhinocode_refs": [reference(RHINOCODE_POLICY)]}


def startup_instructions() -> str:
    snapshot = _snapshot()
    return ('Almond inspects and edits Rhino architecture and drawings. On first use, call '
            'get_policy() to read BASIC-INSTRUCTIONS.md and discover optional policies. '
            f'guide_version={snapshot["guide_version"]}')


def read_policy(policy: str = "") -> dict:
    if not isinstance(policy, str) or (policy and policy not in POLICIES):
        raise ValueError("policy must be basic, metadata, rhino_scripting, rhinocode or an empty string.")
    policy = policy or "basic"
    snapshot = _snapshot()
    result = {"status": "success", "guide_version": snapshot["guide_version"],
              "selected_policy": policy, "available_policies": dict(POLICIES)}
    if policy == "basic":
        result.update(text=snapshot["basic"], source_refs=deepcopy(snapshot["basic_refs"]),
                      tools=list(snapshot["tools"]))
    elif policy == "metadata":
        result.update(policy=deepcopy(snapshot["metadata"]), source_refs=deepcopy(snapshot["metadata_refs"]))
    elif policy == "rhinocode":
        result.update(text=snapshot["rhinocode"], source_refs=deepcopy(snapshot["rhinocode_refs"]))
    else:
        result["scripting_skill"] = deepcopy(snapshot["scripting_skill"])
        result["source_refs"] = deepcopy(snapshot["scripting_refs"])
    return result
