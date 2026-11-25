"""Read bundled work policies and collect public tool names."""
from copy import deepcopy
from functools import lru_cache
import hashlib
import json
from pathlib import Path
from typing import Literal
from almond_mcp.tool_declarations import declaration_sources, inspect_declarations

PACKAGE = Path(__file__).resolve().parent
BASIC_REFERENCE = Path(__file__).resolve()
BASIC_SUMMARY = (
    "공통 도구 참고 목록입니다. 이 연결에서 호출할 수 있는 도구와 사용법은 tools/list에서 확인하세요. "
    "메타데이터·스크립팅 참고 자료는 available_policies에서 선택할 수 있습니다."
)
SCRIPTING_SKILL = PACKAGE / "features/modeling/rhino3d-scripts"
METADATA_POLICY = PACKAGE / "modeling_policy.json"
RHINOCODE_POLICY = PACKAGE / "RHINOCODE-INSTRUCTIONS.md"
POLICIES = {
    "basic": ("공개 도구 목록과 참고 자료 종류", None),
    "metadata": ("Rhino 객체 메타데이터 키 사전", METADATA_POLICY),
    "rhino_scripting": ("Rhino 스크립트 작성과 API 참고 자료", None),
    "rhinocode": ("RhinoCode 코드·Rhino 커맨드 실행과 결과 확인", RHINOCODE_POLICY),
}
PolicyName = Literal[("", *POLICIES)]


def _read_content(path: Path, *, captured_bytes: bytes | None = None) -> bytes:
    raw = path.read_bytes() if captured_bytes is None else captured_bytes
    return raw if path.suffix == ".png" else raw.decode("utf-8-sig").replace("\r\n", "\n").encode("utf-8")


def content_digest(path: Path, *, captured_bytes: bytes | None = None) -> str:
    return hashlib.sha256(_read_content(path, captured_bytes=captured_bytes)).hexdigest()


def _tool_sources() -> tuple[Path, ...]:
    runtime = PACKAGE / "runtime/mcp_server.py"
    # The standalone wheel excludes the checkout's execution runtime.
    return declaration_sources(PACKAGE, document_entry=runtime if runtime.is_file() else None)


def _source_files(tool_sources: tuple[Path, ...]) -> list[Path]:
    # Tool sources provide names only. Descriptions are delivered by tools/list.
    policy_files = [path for _, path in POLICIES.values() if path is not None]
    return sorted({BASIC_REFERENCE, *policy_files, *tool_sources,
                   *(p for p in SCRIPTING_SKILL.rglob("*") if p.is_file())})


def source_files() -> list[Path]:
    return _source_files(_tool_sources())


@lru_cache(maxsize=1)
def _snapshot() -> dict:
    tool_sources = _tool_sources()
    inventory = _source_files(tool_sources)
    raw = {path: _read_content(path) for path in inventory}
    digests = {path: hashlib.sha256(content).hexdigest() for path, content in raw.items()}

    def reference(path: Path) -> dict:
        return {"path": "src/mcp/" + path.relative_to(PACKAGE).as_posix(), "sha256": digests[path]}

    tools = inspect_declarations(tool_sources, captured_bytes=raw)
    skill_files = [SCRIPTING_SKILL / "INTEGRATION.md", SCRIPTING_SKILL / "SKILL.md",
                   *sorted((SCRIPTING_SKILL / "references").glob("*.md"))]
    scripting_skill = {
        "name": "rhino3d-scripts",
        "sources": [{**reference(p), "text": raw[p].decode("utf-8")} for p in skill_files],
    }
    payloads = {
        name: {"text": raw[path].decode("utf-8").strip(), "source_refs": [reference(path)]}
        for name, (_, path) in POLICIES.items()
        if path is not None and path.suffix == ".md"
    }
    payloads["basic"] = {"text": BASIC_SUMMARY, "source_refs": [reference(BASIC_REFERENCE)],
                         "tools": sorted(declaration.name for declaration in tools)}
    payloads["metadata"] = {"policy": json.loads(raw[METADATA_POLICY]), "source_refs": [reference(METADATA_POLICY)]}
    payloads["rhino_scripting"] = {"scripting_skill": scripting_skill,
                                   "source_refs": [reference(p) for p in skill_files]}
    if inventory != source_files() or any(_read_content(path) != content for path, content in raw.items()):
        raise RuntimeError("Guide source changed while reading; start a new session.")
    identity = {
        "sources": {path.relative_to(PACKAGE).as_posix(): digest for path, digest in digests.items()},
        "policies": {name: (description, path.relative_to(PACKAGE).as_posix() if path is not None else None)
                     for name, (description, path) in POLICIES.items()},
    }
    version = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    return {"guide_version": version, "payloads": payloads}


def startup_instructions() -> str:
    snapshot = _snapshot()
    return ("Almond inspects and edits Rhino architecture and drawings. "
            "Use tools/list to see the tools available on this connection. "
            'Use context_01-get_policy tool for technical references (policy="metadata" for object keys). '
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
