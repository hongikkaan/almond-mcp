"""Read bundled work policies and collect public tool names."""
from copy import deepcopy
from functools import lru_cache
import ast
import hashlib
import json
from pathlib import Path
from typing import Literal
from almond_mcp.instruction_text import public_tool_name

PACKAGE = Path(__file__).resolve().parent
BASIC_GUIDE = PACKAGE / "BASIC-INSTRUCTIONS.md"
SCRIPTING_SKILL = PACKAGE / "features/modeling/rhino3d-scripts"
METADATA_POLICY = PACKAGE / "modeling_policy.json"
RHINOCODE_POLICY = PACKAGE / "RHINOCODE-INSTRUCTIONS.md"
ACTIVITY_POLICY_DIR = PACKAGE / "features/guidance/policies"
POLICIES = {
    "basic": ("건축 설계·모델링·도면 검증 지침과 공통 도구 목록", BASIC_GUIDE),
    "metadata": ("객체·그룹 메타데이터 키, 레이어·재료 기록 규칙", METADATA_POLICY),
    "rhino_scripting": ("Rhino 스크립트 작성과 API 참고 자료", None),
    "rhinocode": ("RhinoCode 코드·Rhino 커맨드 실행과 결과 확인", RHINOCODE_POLICY),
    "spatial_modeling": ("설계 의도에 맞춘 공간·구축 모델링과 수정 후 확인", ACTIVITY_POLICY_DIR / "spatial_modeling.md"),
    "observation": ("모델과 도면을 관찰하고 판단에 필요한 근거를 확인하는 기준", ACTIVITY_POLICY_DIR / "observation.md"),
    "drawing": ("도면의 목적·표현 기준과 작성·수정 결과의 검수", ACTIVITY_POLICY_DIR / "drawing.md"),
    "design_exploration": ("설계 질문을 구체화하고 대안을 구성·비교하는 기준", ACTIVITY_POLICY_DIR / "design_exploration.md"),
    "feedback_reporting": ("사용자 피드백을 작업에 반영하고 결과와 판단 근거를 전달하는 기준", ACTIVITY_POLICY_DIR / "feedback_reporting.md"),
}
PolicyName = Literal[("", *POLICIES)]


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
    policy_files = [path for _, path in POLICIES.values() if path is not None]
    return sorted([*policy_files, *_tool_sources(),
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
    payloads = {
        name: {"text": raw[path].decode("utf-8").strip(), "source_refs": [reference(path)]}
        for name, (_, path) in POLICIES.items() if path is not None and path.suffix == ".md"
    }
    payloads["basic"]["tools"] = sorted(tools)
    payloads["metadata"] = {"policy": json.loads(raw[METADATA_POLICY]), "source_refs": [reference(METADATA_POLICY)]}
    payloads["rhino_scripting"] = {"scripting_skill": scripting_skill,
                                   "source_refs": [reference(p) for p in skill_files]}
    if inventory != source_files() or any(_read_content(p) != value for p, value in raw.items()):
        raise RuntimeError("Guide source changed while reading; start a new session.")
    identity = {
        "sources": {p.relative_to(PACKAGE).as_posix(): hashlib.sha256(value).hexdigest() for p, value in raw.items()},
        "policies": {name: (description, path.relative_to(PACKAGE).as_posix() if path is not None else None)
                     for name, (description, path) in POLICIES.items()},
    }
    version = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    return {"guide_version": version, "payloads": payloads}


def startup_instructions() -> str:
    snapshot = _snapshot()
    return ('Almond inspects and edits Rhino architecture and drawings. On first use, call '
            'context_01-get_policy tool to read BASIC-INSTRUCTIONS.md and discover policies for the current activity. '
            f'guide_version={snapshot["guide_version"]}')


def read_policy(policy: str = "") -> dict:
    if not isinstance(policy, str) or (policy and policy not in POLICIES):
        raise ValueError(f"policy must be one of {', '.join(POLICIES)} or an empty string.")
    policy = policy or "basic"
    snapshot = _snapshot()
    return {"status": "success", "guide_version": snapshot["guide_version"],
            "selected_policy": policy,
            "available_policies": {name: description for name, (description, _) in POLICIES.items()},
            **deepcopy(snapshot["payloads"][policy])}
