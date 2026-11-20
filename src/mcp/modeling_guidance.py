"""Read bundled work policies and collect public tool names."""
from copy import deepcopy
from functools import lru_cache
import hashlib
import json
from pathlib import Path
from typing import Literal
from almond_mcp.tool_declarations import declaration_sources, inspect_declarations

PACKAGE = Path(__file__).resolve().parent
BASIC_GUIDE = PACKAGE / "BASIC-INSTRUCTIONS.md"
STARTUP_DOCUMENTS = (BASIC_GUIDE, PACKAGE / "design_judgment.md", PACKAGE / "About Rhino.md")
SCRIPTING_SKILL = PACKAGE / "features/modeling/rhino3d-scripts"
METADATA_POLICY = PACKAGE / "modeling_policy.json"
RHINOCODE_POLICY = PACKAGE / "RHINOCODE-INSTRUCTIONS.md"
POLICIES = {
    "basic": ("건축 설계·모델링·도면 검증 지침과 공통 도구 목록", BASIC_GUIDE),
    "metadata": ("Rhino 객체 메타데이터 키 사전", METADATA_POLICY),
    "rhino_scripting": ("Rhino 스크립트 작성과 API 참고 자료", None),
    "rhinocode": ("RhinoCode 코드·Rhino 커맨드 실행과 결과 확인", RHINOCODE_POLICY),
}
PolicyName = Literal[("", *POLICIES)]


def _read_content(path: Path) -> bytes:
    raw = path.read_bytes()
    return raw if path.suffix == ".png" else raw.decode("utf-8-sig").replace("\r\n", "\n").encode("utf-8")


def _read_source(path: Path) -> tuple[bytes, str | None]:
    if path not in STARTUP_DOCUMENTS:
        return _read_content(path), None

    try:
        raw = path.read_bytes()
    except FileNotFoundError:
        return b"", "file missing"
    except OSError:
        return b"", "file unreadable"

    try:
        text = raw.decode("utf-8-sig").replace("\r\n", "\n")
    except UnicodeDecodeError:
        return raw, "invalid UTF-8"
    if not text.strip():
        return raw, "empty document"
    return text.encode("utf-8"), None


def _source_digest(source: tuple[bytes, str | None]) -> str:
    content, problem = source
    if problem is not None:
        # An unavailable document must have a distinct fingerprint from valid UTF-8.
        content = b"\xff" + problem.encode("utf-8") + b"\0" + content
    return hashlib.sha256(content).hexdigest()


def content_digest(path: Path) -> str:
    return _source_digest(_read_source(path))


def _tool_sources() -> tuple[Path, ...]:
    runtime = PACKAGE / "runtime/mcp_server.py"
    # The standalone wheel excludes the checkout's execution runtime.
    return declaration_sources(PACKAGE, document_entry=runtime if runtime.is_file() else None)


def _source_files(tool_sources: tuple[Path, ...]) -> list[Path]:
    # Tool sources provide names only. Descriptions are delivered by tools/list.
    policy_files = [path for _, path in POLICIES.values() if path is not None]
    return sorted({*policy_files, *STARTUP_DOCUMENTS, *tool_sources,
                   *(p for p in SCRIPTING_SKILL.rglob("*") if p.is_file())})


def source_files() -> list[Path]:
    return _source_files(_tool_sources())


@lru_cache(maxsize=1)
def _snapshot() -> dict:
    tool_sources = _tool_sources()
    inventory = _source_files(tool_sources)
    sources = {path: _read_source(path) for path in inventory}
    raw = {path: content for path, (content, _) in sources.items()}
    digests = {path: _source_digest(source) for path, source in sources.items()}

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
        if path is not None and path.suffix == ".md" and sources[path][1] is None
    }
    if "basic" in payloads:
        payloads["basic"]["tools"] = sorted(declaration.name for declaration in tools)
    payloads["metadata"] = {"policy": json.loads(raw[METADATA_POLICY]), "source_refs": [reference(METADATA_POLICY)]}
    payloads["rhino_scripting"] = {"scripting_skill": scripting_skill,
                                   "source_refs": [reference(p) for p in skill_files]}
    startup_sections = {}
    for path in STARTUP_DOCUMENTS:
        content, problem = sources[path]
        if problem is None:
            startup_sections[path] = f"## {path.name}\n\n{content.decode('utf-8')}"
        else:
            startup_sections[path] = f"Startup guidance unavailable: {path.name} ({problem})."

    if inventory != source_files() or any(_read_source(path) != source for path, source in sources.items()):
        raise RuntimeError("Guide source changed while reading; start a new session.")
    identity = {
        "sources": {path.relative_to(PACKAGE).as_posix(): digest for path, digest in digests.items()},
        "policies": {name: (description, path.relative_to(PACKAGE).as_posix() if path is not None else None)
                     for name, (description, path) in POLICIES.items()},
    }
    version = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    return {"guide_version": version, "payloads": payloads, "startup_sections": startup_sections}


def startup_instructions() -> str:
    snapshot = _snapshot()
    introduction = ("Almond inspects and edits Rhino architecture and drawings. "
                    "Use context_01-get_policy tool for bundled guidance and the metadata key dictionary. "
                    f'guide_version={snapshot["guide_version"]}')
    return "\n\n".join([introduction, *snapshot["startup_sections"].values()])


def read_policy(policy: str = "") -> dict:
    if not isinstance(policy, str) or (policy and policy not in POLICIES):
        raise ValueError(f"policy must be one of {', '.join(POLICIES)} or an empty string.")
    policy = policy or "basic"
    snapshot = _snapshot()
    if policy == "basic" and policy not in snapshot["payloads"]:
        raise RuntimeError(snapshot["startup_sections"][BASIC_GUIDE])
    return {"status": "success", "guide_version": snapshot["guide_version"],
            "selected_policy": policy,
            "available_policies": {name: description for name, (description, _) in POLICIES.items()},
            **deepcopy(snapshot["payloads"][policy])}
